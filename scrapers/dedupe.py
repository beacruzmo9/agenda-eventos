"""Deduplicación de eventos entre fuentes.

Dos eventos se consideran el mismo si:
  - empiezan el mismo día, y
  - sus títulos se parecen (tras quitar acentos, signos y palabras de relleno), y
  - coinciden en lugar o en hora (o los títulos son prácticamente idénticos).

Se queda el de la fuente con más prioridad (la que aparece antes en la lista, ver
CONNECTORS en run.py). Del otro se aprovecha el precio si el primero no lo tenía, y su
enlace se guarda en "also" (para mostrar más adelante "también en: …").
"""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

# Palabras que no ayudan a distinguir eventos.
STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "de", "del", "y", "e", "en", "a", "al", "con", "por",
    "the", "and", "of", "in", "live", "granada", "concierto", "concert", "tour",
    "gira", "presenta", "espectaculo", "exposicion",
}


def norm_title(title: str) -> str:
    t = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return " ".join(w for w in t.split() if w not in STOPWORDS and not re.fullmatch(r"20\d\d", w))


def similar_titles(a: str, b: str) -> float:
    """0..1. Contener el otro título (si no es muy corto) cuenta como muy parecido."""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    short, long_ = sorted((a, b), key=len)
    if len(short) >= 8 and re.search(rf"\b{re.escape(short)}\b", long_):
        return 0.9
    ratio = SequenceMatcher(None, a, b).ratio()
    wa, wb = set(a.split()), set(b.split())
    jaccard = len(wa & wb) / len(wa | wb)
    return max(ratio, jaccard)


def _start_time(e: dict) -> str | None:
    return None if e.get("all_day") else e["start"][11:16]


def is_same(a: dict, b: dict) -> bool:
    if a["start"][:10] != b["start"][:10]:
        return False
    sim = similar_titles(norm_title(a["title"]), norm_title(b["title"]))
    if sim >= 0.95:
        return True
    if sim < 0.75:
        return False
    same_place = a.get("venue_id") and a.get("venue_id") == b.get("venue_id")
    ta, tb = _start_time(a), _start_time(b)
    return bool(same_place or (ta and ta == tb))


def merge(keep: dict, other: dict) -> dict:
    keep = dict(keep)
    if keep.get("price", {}).get("free") is None and other.get("price", {}).get("free") is not None:
        keep["price"] = other["price"]
    also = list(keep.get("also", []))
    for x in [{"source": other["source"], "url": other["url"]}, *other.get("also", [])]:
        if x["url"] != keep["url"] and x not in also:
            also.append(x)
    if also:
        keep["also"] = also
    return keep


def dedupe(events: list[dict]) -> tuple[list[dict], int]:
    """`events` en orden de prioridad de fuente. Devuelve (eventos sin duplicados, nº fusionados)."""
    kept: list[dict] = []
    by_day: dict[str, list[int]] = {}
    merged = 0
    for e in events:
        day = e["start"][:10]
        for i in by_day.get(day, []):
            if kept[i]["source"] != e["source"] and is_same(kept[i], e):
                kept[i] = merge(kept[i], e)
                merged += 1
                break
        else:
            by_day.setdefault(day, []).append(len(kept))
            kept.append(e)
    return kept, merged
