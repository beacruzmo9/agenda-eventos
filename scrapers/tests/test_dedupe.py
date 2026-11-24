"""Pruebas de la deduplicación entre fuentes."""
import unittest

from scrapers.dedupe import dedupe, norm_title


def ev(source, title, start="2027-03-14T21:30:00+01:00", venue="palacio-de-congresos", price=None, all_day=False):
    return {"id": f"{source}-{title}", "source": source, "title": title, "start": start, "all_day": all_day,
            "venue_id": venue, "url": f"https://{source}.test/{len(title)}", "price": price or {"free": None}}


class TestDedupe(unittest.TestCase):
    def test_normaliza(self):
        self.assertEqual(norm_title("Concierto: «Grupo X» – Gira 2027 en Granada"), "grupo x")

    def test_mismo_evento_distinto_titulo(self):
        a = ev("ugr", "Concierto de Grupo X")
        b = ev("ticketmaster", "GRUPO X - Gira 2027", price={"free": False, "min": 25, "max": 25, "text": "25 €"})
        out, n = dedupe([a, b])
        self.assertEqual(n, 1)
        self.assertEqual(out[0]["source"], "ugr")              # gana la fuente prioritaria
        self.assertEqual(out[0]["price"]["text"], "25 €")      # pero se aprovecha el precio
        self.assertEqual(out[0]["also"], [{"source": "ticketmaster", "url": b["url"]}])

    def test_otro_dia_no_es_duplicado(self):
        out, n = dedupe([ev("ugr", "Grupo X"), ev("ticketmaster", "Grupo X", start="2027-03-15T21:30:00+01:00")])
        self.assertEqual(n, 0)

    def test_titulos_distintos_mismo_sitio(self):
        out, n = dedupe([ev("ugr", "Orquesta Ciudad de Granada: Mahler"), ev("ticketmaster", "Rozalén")])
        self.assertEqual(n, 0)

    def test_parecido_pero_otro_lugar_y_hora(self):
        a = ev("ugr", "Noche de flamenco", venue="la-madraza", start="2027-03-14T19:00:00+01:00")
        b = ev("ticketmaster", "Noche flamenca", venue="sala-x")
        self.assertEqual(dedupe([a, b])[1], 0)

    def test_misma_fuente_no_se_fusiona(self):
        # Dos pases del mismo espectáculo en una fuente son eventos distintos.
        self.assertEqual(dedupe([ev("ugr", "Obra Z"), ev("ugr", "Obra Z")])[1], 0)


if __name__ == "__main__":
    unittest.main()
