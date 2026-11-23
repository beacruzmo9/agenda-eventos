"""Pruebas sin red del conector UGR.  Ejecutar:  python -m unittest discover scrapers/tests"""
import unittest

from bs4 import BeautifulSoup

from scrapers.common import find_dates, resolve_years
from scrapers.granada.ugr import map_venue, parse_dates, price_from_text


def fecha(html: str):
    return BeautifulSoup(html, "html.parser").select_one("span.fecha")


class TestFechas(unittest.TestCase):
    def test_dia_con_hora(self):
        r = parse_dates(fecha('<span class="fecha"><span class="desde">24 noviembre 2026</span> | <span class="hora">18:00 h</span></span>'))
        self.assertEqual(r, {"start": "2026-11-24T18:00:00+01:00", "end": None, "all_day": False})

    def test_rango_sin_anio_inicial(self):
        r = parse_dates(fecha('<span class="fecha fecha-texto">Del 7 de octubre al 29 de noviembre de 2026</span>'))
        self.assertEqual(r["start"], "2026-10-07T00:00:00+02:00")
        self.assertEqual(r["end"], "2026-11-29T23:59:00+01:00")
        self.assertTrue(r["all_day"])

    def test_rango_cruza_anio(self):
        r = parse_dates(fecha('<span class="fecha fecha-texto">Del 24 de noviembre al 30 de marzo de 2027</span>'))
        self.assertTrue(r["start"].startswith("2026-11-24"))
        self.assertTrue(r["end"].startswith("2027-03-30"))

    def test_rango_texto_extra(self):
        d = resolve_years(find_dates("Del 19 de octubre de 2026 hasta el 12 de febrero de 2027 (distintas sedes)"))
        self.assertEqual(d, [(19, 10, 2026), (12, 2, 2027)])


class TestPrecio(unittest.TestCase):
    def test_libre(self):
        self.assertEqual(price_from_text("Entrada libre hasta completar aforo"), {"free": True})

    def test_euros(self):
        p = price_from_text("Entradas: 5 € (estudiantes) y 10 €")
        self.assertEqual((p["free"], p["min"], p["max"], p["text"]), (False, 5, 10, "5–10 €"))

    def test_desconocido(self):
        self.assertIsNone(price_from_text("")["free"])


class TestLugar(unittest.TestCase):
    def test_fuera_de_granada(self):
        self.assertIsNone(map_venue("museo-de-ceuta-revellin-de-san-ignacio", "Museo de Ceuta"))

    def test_alias(self):
        self.assertEqual(map_venue("palacio-de-la-madraza-centro-de-cultura-contemporanea", "x")[0], "la-madraza")


if __name__ == "__main__":
    unittest.main()
