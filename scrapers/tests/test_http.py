"""Pruebas sin red de los reintentos de PoliteSession."""
import unittest
from unittest import mock

import requests

from scrapers.common import PoliteSession


def resp(status: int, headers=None) -> requests.Response:
    r = requests.Response()
    r.status_code = status
    r.headers.update(headers or {})
    r.url = "https://ejemplo.test/"
    return r


class TestReintentos(unittest.TestCase):
    def setUp(self):
        self.ps = PoliteSession(delay=0)
        self.ps._allowed = lambda url: True
        self.sleeps = []
        self.ps._sleep = self.sleeps.append

    def test_503_y_luego_bien(self):
        with mock.patch.object(self.ps.s, "get", side_effect=[resp(503), resp(200)]) as g:
            self.assertEqual(self.ps.get("https://ejemplo.test/").status_code, 200)
        self.assertEqual(g.call_count, 2)
        self.assertEqual(self.sleeps, [5])

    def test_corte_de_conexion_y_luego_bien(self):
        with mock.patch.object(self.ps.s, "get", side_effect=[requests.ConnectionError("x"), resp(200)]):
            self.assertEqual(self.ps.get("https://ejemplo.test/").status_code, 200)

    def test_falla_siempre(self):
        with mock.patch.object(self.ps.s, "get", side_effect=[resp(503)] * 3) as g:
            with self.assertRaises(requests.HTTPError):
                self.ps.get("https://ejemplo.test/")
        self.assertEqual(g.call_count, 3)
        self.assertEqual(self.sleeps, [5, 20])

    def test_404_no_reintenta(self):
        with mock.patch.object(self.ps.s, "get", side_effect=[resp(404)]) as g:
            with self.assertRaises(requests.HTTPError):
                self.ps.get("https://ejemplo.test/")
        self.assertEqual(g.call_count, 1)

    def test_respeta_retry_after(self):
        with mock.patch.object(self.ps.s, "get", side_effect=[resp(429, {"Retry-After": "30"}), resp(200)]):
            self.ps.get("https://ejemplo.test/")
        self.assertEqual(self.sleeps, [30])


if __name__ == "__main__":
    unittest.main()
