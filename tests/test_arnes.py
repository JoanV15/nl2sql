"""Detector de es_venta_valida espurio (D-48) y catálogo Hito 2."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluacion"))

from arnes import (  # noqa: E402
    elegir_bloques,
    es_venta_valida_espurio,
    evaluar_una,
    pregunta_trata_de_ventas,
)
from catalogo import (  # noqa: E402
    ABSTENCION,
    EMBUDO,
    FUENTES,
    LOGISTICA,
    NIVEL1,
    NIVEL2,
    NIVEL3,
)


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


def test_hito2_catalogo_sin_43_ni_49_a_55() -> None:
    ids = [n for n, _ in NIVEL2 + NIVEL3 + ABSTENCION]
    assert 43 not in ids
    assert all(n not in ids for n in range(49, 56))
    assert ids == [
        *range(19, 35),
        *range(35, 43),
        *range(44, 47),
        *range(56, 64),
    ]


def test_elegir_bloques_hibrida() -> None:
    claves = [c for c, _, _ in elegir_bloques("logistica,embudo,fuentes")]
    assert claves == ["logistica", "embudo", "fuentes"]
    ids = [n for _, _, ps in elegir_bloques("logistica,embudo,fuentes") for n, _ in ps]
    assert ids == [47, 48, 50, 51, 53, 54, 55]


def test_nivel1_en_catalogo() -> None:
    assert [n for n, _ in NIVEL1] == list(range(1, 19))


def test_hito4_logistica_47_y_48_en_catalogo() -> None:
    assert [n for n, _ in LOGISTICA] == [47, 48]


def test_hito4_embudo_50_y_51_en_catalogo() -> None:
    assert [n for n, _ in EMBUDO] == [50, 51]


def test_hito4_fuentes_53_a_55_en_catalogo() -> None:
    assert [n for n, _ in FUENTES] == [53, 54, 55]


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
