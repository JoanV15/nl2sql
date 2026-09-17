"""Invariantes del clickstream simulado; ids reales se comprueban en el job."""

from tfm_nlsql.ingesta.clickstream import evento_de


def test_evento_invariantes_y_r05() -> None:
    e = evento_de("producto-real-1", "2018-01-15")
    assert e["product_id"] == "producto-real-1"
    assert e["fecha"] == "2018-01-15"
    assert e["es_simulado"] is True
    assert e["num_visitas"] >= e["num_anadidos_carrito"]
    assert e["num_anadidos_carrito"] == (
        e["num_compras"] + e["num_carritos_abandonados"]
    )
    assert e["num_compras"] >= 0
    assert e["num_carritos_abandonados"] >= 0
