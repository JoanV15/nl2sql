"""Detector de es_venta_valida espurio (D-48)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluacion"))

from arnes import es_venta_valida_espurio, pregunta_trata_de_ventas  # noqa: E402


def test_censo_con_bandera_es_espurio() -> None:
    sql = "SELECT COUNT(*) FROM obt_pedidos WHERE es_venta_valida"
    assert es_venta_valida_espurio("¿Cuántos clientes tenemos en cada estado?", sql)
    assert es_venta_valida_espurio("¿Cuántos pedidos hemos hecho en total?", sql)


def test_ventas_con_bandera_no_es_espurio() -> None:
    sql = "SELECT SUM(importe_articulos) FROM obt_pedidos WHERE es_venta_valida"
    assert pregunta_trata_de_ventas("¿Cuánto facturamos en 2018?")
    assert not es_venta_valida_espurio("¿Cuánto facturamos en 2018?", sql)
    assert not es_venta_valida_espurio(
        "¿Cuánto se paga de media en gastos de envío por pedido?", sql
    )


def test_sin_bandera_no_es_espurio() -> None:
    assert not es_venta_valida_espurio(
        "¿Cuántos pedidos hemos hecho en total?",
        "SELECT COUNT(*) FROM obt_pedidos",
    )
    assert not es_venta_valida_espurio("¿Cuántos clientes tenemos?", None)
