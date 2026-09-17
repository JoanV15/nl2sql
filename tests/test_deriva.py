"""Deriva D-25: Gold vs catalogo_columnas() del prefijo. No interpola el contrato."""

from __future__ import annotations

from pathlib import Path

import pytest

from tfm_nlsql.plataforma.muestra import construir_muestra
from tfm_nlsql.runtime.contrato import catalogo_columnas, extraer_prefijo
from tfm_nlsql.runtime.deriva import (
    TABLAS_GOLD,
    DerivaContrato,
    columnas_gold,
    comprobar_deriva,
    quitar_columna_prefijo,
)
from tfm_nlsql.rutas import CONTRATO


@pytest.fixture(scope="module")
def gold_ci(tmp_path_factory: pytest.TempPathFactory) -> Path:
    gold = tmp_path_factory.mktemp("gold") / "ci.duckdb"
    rc = construir_muestra(gold)
    assert rc == 0, "dbt build de muestra falló"
    return gold


def test_muestra_instancia_las_cuatro_obt(gold_ci: Path) -> None:
    import duckdb

    con = duckdb.connect(str(gold_ci), read_only=True)
    tablas = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
    for t in TABLAS_GOLD:
        assert t in tablas
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        assert n >= 1


def test_deriva_contrato_real(gold_ci: Path) -> None:
    prefijo = extraer_prefijo(CONTRATO.read_text(encoding="utf-8"))
    comprobar_deriva(catalogo_columnas(prefijo), columnas_gold(gold_ci))


def test_deriva_falla_si_quitas_columna_del_contrato(gold_ci: Path) -> None:
    prefijo = extraer_prefijo(CONTRATO.read_text(encoding="utf-8"))
    gold = columnas_gold(gold_ci)
    comprobar_deriva(catalogo_columnas(prefijo), gold)
    roto = quitar_columna_prefijo(prefijo, "obt_pedidos", "ciudad_cliente")
    with pytest.raises(DerivaContrato, match="ciudad_cliente"):
        comprobar_deriva(catalogo_columnas(roto), gold)
