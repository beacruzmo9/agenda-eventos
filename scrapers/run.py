"""Ejecuta todos los conectores y genera data/<ciudad>/events.json y venues.json.

Uso:  python -m scrapers.run

- Cada fuente guarda su último resultado bueno en data/<ciudad>/sources/<fuente>.json.
  Si un conector falla (o devuelve sospechosamente pocos eventos), se conserva ese
  último resultado y los demás siguen.
- Los eventos ya terminados pasan al archivo data/<ciudad>/archive/AAAA-MM.json.
"""
from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime
from pathlib import Path

from .common import TZ
from .granada import ugr

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# Conectores activos por ciudad: (nombre de la fuente, función fetch).
CONNECTORS = {
    "granada": [
        ("ugr", ugr.fetch),
    ],
}


def load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def dump_list(path: Path, items: list[dict]) -> None:
    """Un objeto por línea: fácil de leer y de comparar en el historial de Git."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ",\n".join("  " + json.dumps(x, ensure_ascii=False) for x in items)
    path.write_text("[\n" + lines + ("\n" if items else "") + "]\n", encoding="utf-8")


def event_end(e: dict) -> str:
    return e.get("end") or e["start"]


def run_city(city: str, connectors) -> bool:
    city_dir = DATA / city
    today = datetime.now(TZ).date().isoformat()
    ok = True
    source_events: dict[str, list[dict]] = {}
    venues = {v["id"]: v for v in load(city_dir / "venues.json", [])}

    for name, fetch in connectors:
        src_file = city_dir / "sources" / f"{name}.json"
        prev = load(src_file, [])
        try:
            events, new_venues = fetch(prev)
            if len(prev) >= 10 and len(events) < len(prev) * 0.3:
                raise RuntimeError(f"solo {len(events)} eventos (antes {len(prev)}): ¿ha cambiado la web?")
            dump_list(src_file, events)
            for v in new_venues:
                venues[v["id"]] = {**venues.get(v["id"], {}), **v}
            source_events[name] = events
        except Exception:  # noqa: BLE001
            ok = False
            print(f"[{name}] ERROR, se conservan los datos anteriores ({len(prev)} eventos):", file=sys.stderr)
            traceback.print_exc()
            source_events[name] = prev

    # Fuentes que ya no están activas (o retiradas) no se incluyen.
    all_events = [e for evs in source_events.values() for e in evs]

    # Archivar eventos terminados que estaban publicados.
    previous = load(city_dir / "events.json", [])
    by_month: dict[str, list[dict]] = {}
    for e in previous:
        if event_end(e)[:10] < today and e.get("source") != "ejemplo":
            by_month.setdefault(event_end(e)[:7], []).append(e)
    for month, evs in by_month.items():
        path = city_dir / "archive" / f"{month}.json"
        archived = {x["id"]: x for x in load(path, [])}
        archived.update({x["id"]: x for x in evs})
        dump_list(path, sorted(archived.values(), key=lambda x: x["start"]))

    upcoming = sorted((e for e in all_events if event_end(e)[:10] >= today), key=lambda e: (e["start"], e["title"]))
    dump_list(city_dir / "events.json", upcoming)
    dump_list(city_dir / "venues.json", sorted(venues.values(), key=lambda v: v["name"].lower()))
    print(f"[{city}] {len(upcoming)} eventos próximos publicados, {len(venues)} lugares")
    return ok


def main() -> int:
    ok = all([run_city(city, conns) for city, conns in CONNECTORS.items()])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
