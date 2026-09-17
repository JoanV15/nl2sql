"""Un CSV corrupto no entra en Bronze (D-08)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tfm_nlsql.ingesta.esquemas import ESQUEMAS
from tfm_nlsql.plataforma.bronze import demostrar_cuarentena, promover, sesion_spark

pytestmark = pytest.mark.spark

SANO = "olist_customers_dataset.csv"
MALO = "olist_sellers_dataset.csv"
FECHA = "2026-09-14"


@pytest.fixture(scope="module")
def spark():
    pytest.importorskip("pyspark")
    s = sesion_spark()
    yield s
    s.stop()


def _escribir(dir_: Path, nombre: str, texto: str) -> None:
    (dir_ / nombre).write_text(texto, encoding="utf-8")


def test_csv_sano_va_a_bronze(spark, tmp_path: Path) -> None:
    landing = tmp_path / "landing"
    landing.mkdir()
    cols = ",".join(ESQUEMAS[SANO])
    _escribir(landing, SANO, cols + "\nc1,u1,01000,sao paulo,SP\n")
    ok, ko = promover(
        landing, tmp_path / "bronze", tmp_path / "cuarentena", FECHA, spark
    )
    assert SANO in ok
    assert SANO not in ko
    dest = (
        tmp_path
        / "bronze"
        / "olist_customers_dataset"
        / f"fecha_ingesta={FECHA}"
        / SANO
    )
    assert dest.is_file()


def test_csv_corrupto_va_a_cuarentena_no_bronze(spark, tmp_path: Path) -> None:
    assert demostrar_cuarentena(tmp_path / "demo", spark, FECHA)
    bronze_malo = (
        tmp_path
        / "demo"
        / "bronze"
        / "olist_sellers_dataset"
        / f"fecha_ingesta={FECHA}"
        / MALO
    )
    cuarentena_malo = (
        tmp_path
        / "demo"
        / "cuarentena"
        / "olist_sellers_dataset"
        / f"fecha_ingesta={FECHA}"
        / MALO
    )
    assert not bronze_malo.is_file()
    assert cuarentena_malo.is_file()
    assert (
        tmp_path
        / "demo"
        / "bronze"
        / "olist_customers_dataset"
        / f"fecha_ingesta={FECHA}"
        / SANO
    ).is_file()
