"""Utilidades comunes para todos los conectores de Ciudad en vivo.

- Sesión HTTP educada: User-Agent identificado, respeta robots.txt y hace pausas.
- Funciones para fechas en español y para el esquema de evento.
"""
from __future__ import annotations

import re
import time
import unicodedata
import urllib.robotparser
from datetime import datetime, time as dtime
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import requests

USER_AGENT = "CiudadEnVivoBot/0.1 (+https://beacruzmo9.github.io/agenda-eventos/)"
TZ = ZoneInfo("Europe/Madrid")


class PoliteSession:
    """requests.Session que respeta robots.txt y espera entre peticiones."""

    def __init__(self, delay: float = 1.5, timeout: float = 30):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "es-ES,es;q=0.9"})
        self.delay = delay
        self.timeout = timeout
        self._robots: dict[str, urllib.robotparser.RobotFileParser] = {}
        self._last = 0.0

    def _allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        base = f"{parts.scheme}://{parts.netloc}"
        rp = self._robots.get(base)
        if rp is None:
            rp = urllib.robotparser.RobotFileParser()
            try:
                r = self.s.get(base + "/robots.txt", timeout=self.timeout)
                rp.parse(r.text.splitlines() if r.status_code == 200 else [])
            except requests.RequestException:
                rp.parse([])
            self._robots[base] = rp
        return rp.can_fetch(USER_AGENT, url)

    # Errores momentáneos que merece la pena reintentar (servidor saturado, caído un instante…).
    RETRY_STATUS = {429, 500, 502, 503, 504}
    RETRY_WAITS = (5, 20)  # segundos antes del 2.º y 3.er intento
    MAX_RETRY_AFTER = 60

    def get(self, url: str, params: dict | None = None, robots: bool = True) -> requests.Response:
        """GET educado. `params` va aparte de la URL para que las claves de API no salgan en
        los mensajes. `robots=False` solo para APIs oficiales (no son páginas web)."""
        if robots and not self._allowed(url):
            raise PermissionError(f"robots.txt no permite: {url}")
        for attempt in range(len(self.RETRY_WAITS) + 1):
            wait = self.delay - (time.monotonic() - self._last)
            if wait > 0:
                self._sleep(wait)
            try:
                r = self.s.get(url, params=params, timeout=self.timeout)
            except (requests.ConnectionError, requests.Timeout) as exc:
                r, error = None, exc
            self._last = time.monotonic()
            if r is not None and r.status_code not in self.RETRY_STATUS:
                _raise_for_status(r, url)  # 404, 403…: no tiene sentido reintentar
                return r
            if attempt == len(self.RETRY_WAITS):
                break
            pause = self.RETRY_WAITS[attempt]
            if r is not None and (ra := r.headers.get("Retry-After", "")).isdigit():
                pause = max(pause, min(int(ra), self.MAX_RETRY_AFTER))
            reason = f"HTTP {r.status_code}" if r is not None else type(error).__name__
            print(f"[http] {reason} en {url}; reintento en {pause} s")
            self._sleep(pause)
        if r is None:
            raise error
        _raise_for_status(r, url)
        return r

    @staticmethod
    def _sleep(seconds: float) -> None:
        time.sleep(seconds)


def _raise_for_status(r: requests.Response, url: str) -> None:
    """Como raise_for_status, pero el mensaje lleva la URL sin parámetros (sin claves)."""
    if r.status_code >= 400:
        raise requests.HTTPError(f"HTTP {r.status_code} en {url}", response=r)


class SkipSource(Exception):
    """El conector no puede ejecutarse (p. ej. falta su clave de API). No es un fallo:
    se conservan sus datos anteriores sin marcar error."""


# ---------- Fechas en español ----------

MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
    "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}
_DATE_RE = re.compile(
    r"(\d{1,2})\s+(?:de\s+)?(" + "|".join(MONTHS) + r")(?:\s+(?:de\s+|del\s+)?(\d{4}))?",
    re.IGNORECASE,
)
_TIME_RE = re.compile(r"(\d{1,2})[:.](\d{2})\s*h", re.IGNORECASE)


def find_dates(text: str) -> list[tuple[int, int, int | None]]:
    """Devuelve [(día, mes, año|None), ...] en el orden en que aparecen."""
    return [(int(d), MONTHS[m.lower()], int(y) if y else None) for d, m, y in _DATE_RE.findall(text)]


def find_time(text: str) -> dtime | None:
    m = _TIME_RE.search(text)
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    return dtime(h, mi) if h < 24 and mi < 60 else None


def resolve_years(dates: list[tuple[int, int, int | None]]) -> list[tuple[int, int, int]]:
    """Rellena años que faltan (p. ej. 'Del 7 de octubre al 29 de noviembre de 2026')."""
    out: list[tuple[int, int, int]] = []
    next_year = None
    for d, m, y in reversed(dates):
        if y is None:
            if next_year is None:
                y = datetime.now(TZ).year
            else:
                ny, nm = next_year
                y = ny - 1 if m > nm else ny
        out.append((d, m, y))
        next_year = (y, m)
    return list(reversed(out))


def local_iso(y: int, m: int, d: int, t: dtime = dtime(0, 0)) -> str:
    return datetime(y, m, d, t.hour, t.minute, tzinfo=TZ).isoformat()


# ---------- Otros ----------

def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()
