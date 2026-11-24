"""Conector: Ticketmaster Discovery API (API oficial, gratuita con clave).

Documentación: https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/
La clave se lee de la variable de entorno TICKETMASTER_API_KEY (en GitHub: secreto del
repositorio). Sin clave, el conector se salta sin dar error.

Solo datos básicos (título, fecha, hora, lugar, tipo, precio) y enlace a la ficha de
Ticketmaster. Sin descripciones ni imágenes. Se excluyen deportes, aparcamientos y
paquetes VIP/extras, y los eventos cancelados.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, time as dtime

from ..common import TZ, PoliteSession, SkipSource, clean, local_iso, slugify

SOURCE = "ticketmaster"
API_URL = "https://app.ticketmaster.com/discovery/v2/events.json"
PAGE_SIZE = 200
MAX_PAGES = 5  # la API no deja pasar de 1000 resultados (size × page)

# Granada capital: la API filtra por ciudad y además comprobamos la del lugar.
CITY_NAMES = {"granada"}

# Ticketmaster agrupa por "segment" y "genre". Primero se mira el género, luego el segmento.
GENRE_MAP = {
    "flamenco": "flamenco",
    "theatre": "teatro",
    "comedy": "teatro",
    "opera": "concierto",
    "classical": "concierto",
    "dance": "danza",
    "children's theatre": "infantil",
    "family": "infantil",
    "fine art": "exposicion",
    "festival": "festival",
}
SEGMENT_MAP = {
    "music": "concierto",
    "arts & theatre": "teatro",
    "film": "cine",
    "miscellaneous": "otros",
}
EXCLUDED_SEGMENTS = {"sports"}
EXTRAS_TITLE = re.compile(r"\b(parking|aparcamiento|upgrade|vip package|paquete vip|merchandising)\b", re.IGNORECASE)

# Nombres de Ticketmaster → lugar ya conocido (venues.json). Se amplía al ver datos reales.
VENUE_ALIASES = {
    "palacio-de-congresos-de-granada": "palacio-de-congresos",
    "palacio-de-exposiciones-y-congresos-de-granada": "palacio-de-congresos",
    "auditorio-manuel-de-falla-granada": "auditorio-manuel-de-falla",
    "teatro-isabel-la-catolica-granada": "teatro-isabel-la-catolica",
}


def venue_id(name: str) -> str:
    vid = slugify(name)
    vid = VENUE_ALIASES.get(vid, vid)
    return re.sub(r"-(de-)?granada$", "", vid) or vid


def map_category(ev: dict) -> str | None:
    """Devuelve la categoría o None si hay que descartar el evento (deporte)."""
    cl = next((c for c in ev.get("classifications", []) if c.get("primary")), None) \
        or (ev.get("classifications") or [{}])[0]
    segment = (cl.get("segment") or {}).get("name", "").lower()
    if segment in EXCLUDED_SEGMENTS:
        return None
    for key in ("genre", "subGenre"):
        name = (cl.get(key) or {}).get("name", "").lower()
        if name in GENRE_MAP:
            return GENRE_MAP[name]
    if cl.get("family"):
        return "infantil"
    return SEGMENT_MAP.get(segment, "otros")


def parse_price(ev: dict) -> dict:
    ranges = [p for p in ev.get("priceRanges", []) if p.get("currency", "EUR") == "EUR" and p.get("min") is not None]
    if not ranges:
        return {"free": None}
    lo = min(float(p["min"]) for p in ranges)
    hi = max(float(p.get("max", p["min"])) for p in ranges)
    if hi == 0:
        return {"free": True}
    fmt = lambda n: f"{n:g}"
    return {"free": False, "min": lo, "max": hi,
            "text": f"{fmt(lo)} €" if lo == hi else f"{fmt(lo)}–{fmt(hi)} €"}


def parse_dates(ev: dict) -> dict | None:
    start = (ev.get("dates") or {}).get("start") or {}
    day = start.get("localDate")
    if not day or start.get("dateTBD") or start.get("dateTBA"):
        return None
    y, m, d = (int(x) for x in day.split("-"))
    t = start.get("localTime")
    if not t or start.get("timeTBA") or start.get("noSpecificTime"):
        return {"start": local_iso(y, m, d), "end": None, "all_day": True}
    hh, mm = (int(x) for x in t.split(":")[:2])
    return {"start": local_iso(y, m, d, dtime(hh, mm)), "end": None, "all_day": False}


def parse_event(ev: dict) -> tuple[dict, dict] | tuple[None, str]:
    """Convierte un evento de la API → (evento, lugar) o (None, motivo del descarte)."""
    title = clean(ev.get("name"))
    if not title or EXTRAS_TITLE.search(title):
        return None, "extra"
    status = ((ev.get("dates") or {}).get("status") or {}).get("code", "")
    if status in ("cancelled", "offsale"):
        return None, "cancelado"
    venues = (ev.get("_embedded") or {}).get("venues") or []
    v = venues[0] if venues else {}
    city = clean((v.get("city") or {}).get("name")).lower()
    if not v.get("name") or city not in CITY_NAMES:
        return None, "ciudad"
    cat = map_category(ev)
    if cat is None:
        return None, "deporte"
    dates = parse_dates(ev)
    if dates is None:
        return None, "fecha"
    vid = venue_id(v["name"])
    venue = {"id": vid, "city": "granada", "name": clean(v["name"])}
    if (addr := clean((v.get("address") or {}).get("line1"))):
        venue["address"] = addr
    event = {
        "id": f"tm-{ev['id']}",
        "city": "granada",
        "title": title,
        **dates,
        "venue_id": vid,
        "category": cat,
        "price": parse_price(ev),
        "url": ev.get("url") or f"https://www.ticketmaster.es/event/{ev['id']}",
        "source": SOURCE,
    }
    return event, venue


def fetch(prev_events: list[dict], session: PoliteSession | None = None, log=print,
          api_key: str | None = None) -> tuple[list[dict], list[dict]]:
    api_key = api_key or os.environ.get("TICKETMASTER_API_KEY", "").strip()
    if not api_key:
        raise SkipSource("falta TICKETMASTER_API_KEY")
    session = session or PoliteSession(delay=0.5)
    prev = {e["id"]: e for e in prev_events}
    today = datetime.now(TZ).strftime("%Y-%m-%d")

    raw, page, total_pages = [], 0, 1
    while page < min(total_pages, MAX_PAGES):
        data = session.get(API_URL, robots=False, params={
            "apikey": api_key, "countryCode": "ES", "city": "Granada",
            "size": PAGE_SIZE, "page": page, "sort": "date,asc", "locale": "*",
        }).json()
        raw += (data.get("_embedded") or {}).get("events", [])
        total_pages = (data.get("page") or {}).get("totalPages", 0)
        page += 1
    log(f"[ticketmaster] {page} páginas, {len(raw)} eventos en la API")

    events, venues, seen, skipped = [], {}, set(), {}
    for ev in raw:
        event, venue = parse_event(ev)
        if event is None:
            skipped[venue] = skipped.get(venue, 0) + 1
            continue
        if event["id"] in seen:
            continue
        seen.add(event["id"])
        old = prev.get(event["id"])
        same = old and all(old.get(k) == event[k] for k in ("title", "start", "venue_id", "price"))
        event["updated"] = old["updated"] if same else today
        events.append(event)
        venues[venue["id"]] = venue
    log(f"[ticketmaster] {len(events)} eventos útiles; descartados: {skipped}")
    return events, list(venues.values())
