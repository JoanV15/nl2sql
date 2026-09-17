"""El recorrido de la consulta queda cronometrado etapa a etapa (D-22)."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from tfm_nlsql.runtime import orquestador
from tfm_nlsql.runtime.cliente import RespuestaLLM
from tfm_nlsql.runtime.orquestador import (
    ETAPA_AST,
    ETAPA_CALENTAMIENTO,
    ETAPA_EJECUCION,
    ETAPA_EXPLAIN,
    ETAPA_GENERACION,
    ETAPA_REINTENTO,
    consultar,
    reservar_modelo,
)


@pytest.fixture
def gold(tmp_path: Path) -> Path:
    """Gold mínimo: el validador solo admite las OBT de la lista blanca."""
    ruta = tmp_path / "gold.duckdb"
    con = duckdb.connect(str(ruta))
    con.execute("CREATE TABLE obt_pedidos (id_pedido VARCHAR, es_venta_valida BOOLEAN)")
    con.execute("INSERT INTO obt_pedidos VALUES ('a', true), ('b', false)")
    con.close()
    return ruta


@pytest.fixture
def sin_llm(monkeypatch):
    """Sustituye el modelo: los tests no levantan llama-server (R-08)."""
    trazas: list[orquestador.RegistroTraza] = []
    monkeypatch.setattr(orquestador, "persistir", lambda reg: trazas.append(reg) or 1)
    monkeypatch.setattr(orquestador, "calentar", lambda prompt: None)
    monkeypatch.setattr(orquestador, "_calentado", False)

    def responder(textos: list[str]) -> None:
        cola = list(textos)
        monkeypatch.setattr(
            orquestador,
            "completar",
            lambda prompt: RespuestaLLM(
                texto=cola.pop(0), prompt_n=3067, predicted_n=17
            ),
        )

    return responder, trazas


def test_etapas_de_una_consulta_aceptada(gold: Path, sin_llm) -> None:
    responder, trazas = sin_llm
    responder(["SELECT COUNT(*) AS n FROM obt_pedidos"])

    r = consultar("¿Cuántos pedidos hemos hecho en total?", gold=gold)

    assert r.veredicto == "aceptado"
    assert r.filas == [(2,)]
    assert [e["etapa"] for e in r.etapas] == [
        ETAPA_CALENTAMIENTO,
        ETAPA_GENERACION,
        ETAPA_AST,
        ETAPA_EXPLAIN,
        ETAPA_EJECUCION,
    ]
    assert all(e["ok"] and e["ms"] >= 0 for e in r.etapas)
    assert r.total_ms is not None and r.total_ms > 0
    assert "17 fichas generadas" in r.etapas[1]["detalle"]
    # La traza persiste el desglose, no solo el total (D-22).
    assert [e["etapa"] for e in trazas[0].latencia["etapas"]] == [
        e["etapa"] for e in r.etapas
    ]


def test_etapa_fallida_y_reintento(gold: Path, sin_llm) -> None:
    """El AST rechaza, se reintenta una vez (D-20) y la segunda pasa."""
    responder, _ = sin_llm
    responder(
        [
            "SELECT * FROM clientes",
            "SELECT COUNT(*) AS n FROM obt_pedidos",
        ]
    )

    r = consultar("¿Cuántos pedidos hemos hecho en total?", gold=gold)

    assert r.veredicto == "aceptado"
    etapas = [(e["etapa"], e["ok"]) for e in r.etapas]
    assert (ETAPA_AST, False) in etapas
    assert (ETAPA_REINTENTO, True) in etapas
    assert etapas[-1] == (ETAPA_EJECUCION, True)
    assert len(r.reintentos) == 1
    assert "tabla no permitida" in r.reintentos[0]["error"]


def test_sin_reintento_no_corrige(gold: Path, sin_llm) -> None:
    responder, _ = sin_llm
    responder(["SELECT * FROM clientes", "SELECT COUNT(*) AS n FROM obt_pedidos"])

    r = consultar(
        "¿Cuántos pedidos hemos hecho en total?", gold=gold, max_intentos=1
    )

    assert r.veredicto == "rechazado"
    assert r.reintentos == []
    assert not any(e["etapa"] == ETAPA_REINTENTO for e in r.etapas)


def test_abstencion_no_toca_gold(gold: Path, sin_llm) -> None:
    responder, _ = sin_llm
    responder(["ABSTENCION: no existe el coste de producto"])

    r = consultar("¿Cuál es nuestro margen de beneficio?", gold=gold)

    assert r.veredicto == "abstencion"
    assert r.abstencion is not None
    assert [e["etapa"] for e in r.etapas] == [ETAPA_CALENTAMIENTO, ETAPA_GENERACION]


def test_reservar_modelo_no_encola_una_segunda_consulta() -> None:
    """Dos consultas a la vez llenan n_ctx; la segunda se rechaza al momento."""
    with reservar_modelo() as primera:
        assert primera is True
        with reservar_modelo() as segunda:
            assert segunda is False
    with reservar_modelo() as tercera:
        assert tercera is True
