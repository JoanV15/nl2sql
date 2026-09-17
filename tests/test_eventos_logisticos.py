"""Valores de incidencia del contrato; el generador no inventa otros."""

from tfm_nlsql.ingesta.eventos_logisticos import INCIDENCIAS, TRANSPORTISTAS, evento_de


def test_evento_referencia_id_y_valores_del_contrato() -> None:
    e = evento_de("pedido-real-1")
    assert e["order_id"] == "pedido-real-1"
    assert e["es_simulado"] is True
    assert e["id_transportista"] in TRANSPORTISTAS
    assert e["id_transportista"].startswith("sim_")
    assert e["tipo_incidencia"] in (*INCIDENCIAS, None)
