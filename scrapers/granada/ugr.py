"""Conector: agenda de CANAL UGR (Universidad de Granada).

Fuente: https://canal.ugr.es/agenda-canal-ugr/proximas-actividades/
Organismo público. Solo tomamos datos básicos (título, fecha, hora, lugar, tipo,
condiciones de entrada) y enlazamos a la ficha original. Sin textos ni imágenes.
"""
from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup

from ..common import (
    TZ, PoliteSession, clean, find_dates, find_time, local_iso, resolve_years,
)

SOURCE = "ugr"
LIST_URL = "https://canal.ugr.es/agenda-canal-ugr/proximas-actividades/"
MAX_PAGES = 20

# Tipos de actividad de la UGR → categorías de Agendalia (por orden de prioridad).
CATEGORY_MAP = [
    ("conciertos-y-actividades-musicales", "concierto"),
    ("teatro-y-artes-escenicas", "teatro"),
    ("cine-y-artes-audiovisuales", "cine"),
    ("exposiciones", "exposicion"),
    ("actividades-literarias-y-presentaciones-de-libros", "conferencia"),
    ("conferencias-seminarios-divulgacion-cientifica", "conferencia"),
    ("visitas-culturales-patrimonio", "otros"),
    ("actividades-deportivas-aire-libre", "otros"),
]
# Seminarios de investigación muy especializados: no son agenda cultural para el público general.
ACADEMIC_TITLE = re.compile(r"^\s*(seminario|defensa|lectura de tesis|webinar)\b", re.IGNORECASE)

# Sedes fuera de Granada capital (Ceuta, Melilla, área metropolitana) o en línea.
EXCLUDED_VENUES = ("ceuta", "melilla", "santa-fe", "actividad-en-linea")

# Unificar salas de un mismo edificio en un solo lugar.
VENUE_ALIASES = [
    ("palacio-de-la-madraza", "la-madraza", "La Madraza (UGR)"),
    ("espacio-v-centenario", "espacio-v-centenario", "Espacio V Centenario (UGR)"),
    ("rectorado-universidad-de-granada-hospital-real", "hospital-real", "Hospital Real (UGR)"),
]
MULTI_VENUE = ("ugr-varias-sedes", "Varias sedes (UGR)")


def map_category(tipos: list[str]) -> str | None:
    for tipo, cat in CATEGORY_MAP:
        if tipo in tipos:
            return cat
    return None


def map_venue(slug: str | None, name: str | None) -> tuple[str, str] | None:
    """Devuelve (venue_id, nombre) o None si la sede queda fuera de la ciudad."""
    if not slug:
        return MULTI_VENUE
    if any(x in slug for x in EXCLUDED_VENUES):
        return None
    for prefix, vid, vname in VENUE_ALIASES:
        if slug.startswith(prefix):
            return vid, vname
    return slug, name or slug


def parse_dates(fecha_el) -> dict | None:
    """Convierte el bloque de fecha del listado en start/end/all_day."""
    text = clean(fecha_el.get_text(" "))
    desde = fecha_el.select_one(".desde")
    hasta = fecha_el.select_one(".hasta")
    hora = fecha_el.select_one(".hora")
    if desde is not None:
        text = clean(desde.get_text(" ")) + (" al " + clean(hasta.get_text(" ")) if hasta else "")
    dates = find_dates(text)
    if not dates:
        return None
    dates = resolve_years(dates)
    t = find_time(clean(hora.get_text(" "))) if hora is not None else find_time(text)
    (d1, m1, y1), (d2, m2, y2) = dates[0], dates[-1]
    if len(dates) > 1 and (d1, m1, y1) != (d2, m2, y2):
        # Varios días (exposiciones, ciclos): evento de día completo con fin.
        return {
            "start": local_iso(y1, m1, d1),
            "end": datetime(y2, m2, d2, 23, 59, tzinfo=TZ).isoformat(),
            "all_day": True,
        }
    if t is None:
        return {"start": local_iso(y1, m1, d1), "end": None, "all_day": True}
    return {"start": local_iso(y1, m1, d1, t), "end": None, "all_day": False}


def parse_list_page(html: str) -> tuple[list[dict], str | None]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for it in soup.select("div.e-loop-item.type-actividad"):
        a = it.select_one("h3 a[href]")
        fecha = it.select_one("span.fecha")
        if a is None or fecha is None:
            continue
        post_id = next((c[5:] for c in it.get("class", []) if re.fullmatch(r"post-\d+", c)), None)
        tipos = []
        for t in it.select("ul.tipo-actividad a[href]"):
            tipos += parse_qs(urlsplit(t["href"]).query).get("tipo", [])
        lugar = it.select_one("li.nombre-lugar")
        lugar_slug = next((c for c in lugar.get("class", []) if c != "nombre-lugar"), None) if lugar else None
        lugar_name = clean(lugar.select_one(".nivel-0").get_text()) if lugar and lugar.select_one(".nivel-0") else None
        items.append({
            "post_id": post_id,
            "title": clean(a.get_text()),
            "url": a["href"],
            "fecha": fecha,
            "tipos": tipos,
            "lugar_slug": lugar_slug,
            "lugar_name": lugar_name,
        })
    nxt = soup.select_one("[data-next-page][data-max-page]")
    next_url = None
    if nxt is not None and int(nxt.get("data-page", 0)) < int(nxt.get("data-max-page", 0)):
        next_url = nxt["data-next-page"]
    return items, next_url


def parse_price(detail_html: str) -> dict:
    """Lee el campo de entrada de la ficha (icono de personas) → objeto price."""
    soup = BeautifulSoup(detail_html, "html.parser")
    icon = soup.select_one(".elementor-post-info svg.e-fas-users")
    li = icon.find_parent("li") if icon else None
    text = clean(li.get_text(" ")) if li else ""
    return price_from_text(text)


def price_from_text(text: str) -> dict:
    low = text.lower()
    nums = [float(n.replace(",", ".")) for n in re.findall(r"(\d+(?:[.,]\d+)?)\s*€", text)]
    if nums:
        lo, hi = min(nums), max(nums)
        fmt = lambda n: f"{n:g}"
        return {"free": False, "min": lo, "max": hi,
                "text": f"{fmt(lo)} €" if lo == hi else f"{fmt(lo)}–{fmt(hi)} €"}
    if "libre" in low or "gratu" in low:
        return {"free": True}
    # Sin información clara de precio: se muestra "consultar".
    return {"free": None, "text": text[:60] or None}


def fetch(prev_events: list[dict], session: PoliteSession | None = None, log=print) -> tuple[list[dict], list[dict]]:
    """Descarga la agenda. Devuelve (eventos, lugares)."""
    session = session or PoliteSession()
    prev = {e["id"]: e for e in prev_events}
    raw, url, pages = [], LIST_URL, 0
    while url and pages < MAX_PAGES:
        items, url = parse_list_page(session.get(url).text)
        raw += items
        pages += 1
    log(f"[ugr] {pages} páginas, {len(raw)} actividades en el listado")

    today = datetime.now(TZ).strftime("%Y-%m-%d")
    events, venues, seen = [], {}, set()
    skipped = {"tipo": 0, "sede": 0, "fecha": 0, "academico": 0}
    for it in raw:
        cat = map_category(it["tipos"])
        if cat is None:
            skipped["tipo"] += 1
            continue
        if cat == "conferencia" and ACADEMIC_TITLE.match(it["title"]):
            skipped["academico"] += 1
            continue
        venue = map_venue(it["lugar_slug"], it["lugar_name"])
        if venue is None:
            skipped["sede"] += 1
            continue
        dates = parse_dates(it["fecha"])
        if dates is None:
            skipped["fecha"] += 1
            log(f"[ugr] fecha no reconocida: {clean(it['fecha'].get_text(' '))!r} ({it['url']})")
            continue
        eid = f"ugr-{it['post_id'] or abs(hash(it['url']))}"
        if eid in seen:
            continue
        seen.add(eid)

        # El precio solo está en la ficha: se descarga una vez y se reutiliza los días siguientes.
        old = prev.get(eid)
        if old and old.get("url") == it["url"] and "price" in old:
            price = old["price"]
        else:
            try:
                price = parse_price(session.get(it["url"]).text)
            except Exception as exc:  # noqa: BLE001
                log(f"[ugr] no se pudo leer la ficha {it['url']}: {exc}")
                price = {"free": None}

        vid, vname = venue
        venues[vid] = {"id": vid, "city": "granada", "name": vname}
        events.append({
            "id": eid,
            "city": "granada",
            "title": it["title"],
            **dates,
            "venue_id": vid,
            "category": cat,
            "price": price,
            "url": it["url"],
            "source": SOURCE,
            "updated": old["updated"] if old and _same(old, it, dates) else today,
        })
    log(f"[ugr] {len(events)} eventos útiles; descartados: {skipped}")
    return events, list(venues.values())


def _same(old: dict, it: dict, dates: dict) -> bool:
    return old.get("title") == it["title"] and old.get("start") == dates["start"] and old.get("end") == dates["end"]
