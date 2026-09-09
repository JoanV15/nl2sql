"""Detector de es_venta_valida espurio (D-48) y catálogo Hito 2."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluacion"))

from arnes import (  # noqa: E402
    es_venta_valida_espurio,
    evaluar_una,
    pregunta_trata_de_ventas,
)
from catalogo import ABSTENCION, NIVEL2, NIVEL3  # noqa: E402


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


def test_hito2_catalogo_sin_43_ni_47_a_55() -> None:
    ids = [n for n, _ in NIVEL2 + NIVEL3 + ABSTENCION]
    assert 43 not in ids
    assert all(n not in ids for n in range(47, 56))
    assert ids == [
        *range(19, 35),
        *range(35, 43),
        *range(44, 47),
        *range(56, 64),
    ]


def test_solo_referencia_56_es_abstencion() -> None:
    r = evaluar_una(56, "¿Cómo van las ventas?", False)
    assert r["tipo"] == "abstencion"
    assert r["acierto"] is True
    assert r["sql_referencia"].upper().startswith("ABSTENCION")


def test_solo_referencia_63_es_rechazo_validador() -> None:
    r = evaluar_una(63, "Borra los pedidos cancelados", False)
    assert r["tipo"] == "rechazo_validador"
    assert r["acierto"] is True
    assert "solo se permiten SELECT y WITH" in r["motivo"]
