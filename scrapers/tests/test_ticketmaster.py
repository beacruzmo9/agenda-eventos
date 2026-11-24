"""Pruebas sin red del conector Ticketmaster (respuestas de la API simuladas)."""
import unittest
from unittest import mock

from scrapers.common import SkipSource
from scrapers.granada import ticketmaster as tm


def api_event(**over):
    ev = {
        "id": "Z698xZ2qZa1",
        "name": "Grupo X - Gira 2027",
        "url": "https://www.ticketmaster.es/event/grupo-x/123",
        "dates": {"start": {"localDate": "2027-03-14", "localTime": "21:30:00"}, "status": {"code": "onsale"}},
        "classifications": [{"primary": True, "segment": {"name": "Music"}, "genre": {"name": "Rock"}}],
        "priceRanges": [{"type": "standard", "currency": "EUR", "min": 25.0, "max": 35.0}],
        "_embedded": {"venues": [{"name": "Palacio de Congresos de Granada", "city": {"name": "Granada"},
                                   "address": {"line1": "Paseo del Violón, s/n"}}]},
    }
    ev.update(over)
    return ev


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data


class FakeSession:
    def __init__(self, pages):
        self.pages, self.calls = pages, []

    def get(self, url, params=None, robots=True):
        self.calls.append((url, params, robots))
        return FakeResponse(self.pages[params["page"]])


class TestParse(unittest.TestCase):
    def test_evento_basico(self):
        e, v = tm.parse_event(api_event())
        self.assertEqual(e["id"], "tm-Z698xZ2qZa1")
        self.assertEqual(e["start"], "2027-03-14T21:30:00+01:00")
        self.assertFalse(e["all_day"])
        self.assertEqual(e["category"], "concierto")
        self.assertEqual(e["price"], {"free": False, "min": 25.0, "max": 35.0, "text": "25–35 €"})
        self.assertEqual(e["venue_id"], "palacio-de-congresos")
        self.assertEqual(v["address"], "Paseo del Violón, s/n")

    def test_sin_hora_es_dia_completo(self):
        e, _ = tm.parse_event(api_event(dates={"start": {"localDate": "2027-07-01", "noSpecificTime": True}}))
        self.assertTrue(e["all_day"])
        self.assertEqual(e["start"], "2027-07-01T00:00:00+02:00")

    def test_sin_precio(self):
        ev = api_event()
        del ev["priceRanges"]
        self.assertEqual(tm.parse_event(ev)[0]["price"], {"free": None})

    def test_categorias(self):
        cl = lambda seg, gen=None: [{"primary": True, "segment": {"name": seg}, "genre": {"name": gen or "Undefined"}}]
        self.assertEqual(tm.map_category({"classifications": cl("Arts & Theatre", "Comedy")}), "teatro")
        self.assertEqual(tm.map_category({"classifications": cl("Music", "Flamenco")}), "flamenco")
        self.assertEqual(tm.map_category({"classifications": cl("Arts & Theatre", "Dance")}), "danza")
        self.assertEqual(tm.map_category({"classifications": cl("Film")}), "cine")
        self.assertIsNone(tm.map_category({"classifications": cl("Sports", "Soccer")}))

    def test_descartes(self):
        self.assertEqual(tm.parse_event(api_event(name="Parking - Grupo X"))[1], "extra")
        self.assertEqual(tm.parse_event(api_event(dates={"start": {"localDate": "2027-03-14"}, "status": {"code": "cancelled"}}))[1], "cancelado")
        otra = api_event(_embedded={"venues": [{"name": "Sala Y", "city": {"name": "Málaga"}}]})
        self.assertEqual(tm.parse_event(otra)[1], "ciudad")
        dep = api_event(classifications=[{"primary": True, "segment": {"name": "Sports"}}])
        self.assertEqual(tm.parse_event(dep)[1], "deporte")


class TestFetch(unittest.TestCase):
    def test_sin_clave_se_salta(self):
        with mock.patch.dict("os.environ", {"TICKETMASTER_API_KEY": ""}), self.assertRaises(SkipSource):
            tm.fetch([], session=FakeSession([]), log=lambda *_: None)

    def test_paginas_y_updated(self):
        pages = [
            {"_embedded": {"events": [api_event()]}, "page": {"totalPages": 2}},
            {"_embedded": {"events": [api_event(id="B2", name="Otro")]}, "page": {"totalPages": 2}},
        ]
        s = FakeSession(pages)
        prev = [{**tm.parse_event(api_event())[0], "updated": "2026-01-01"}]
        events, venues = tm.fetch(prev, session=s, api_key="k", log=lambda *_: None)
        self.assertEqual([e["id"] for e in events], ["tm-Z698xZ2qZa1", "tm-B2"])
        self.assertEqual(events[0]["updated"], "2026-01-01")  # sin cambios: conserva la fecha
        self.assertEqual(len(venues), 1)
        self.assertEqual(len(s.calls), 2)
        self.assertFalse(s.calls[0][2])  # API oficial: no se consulta robots.txt


if __name__ == "__main__":
    unittest.main()
