"""Silver es idempotente: dos corridas, mismo recuento (D-10)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tfm_nlsql.ingesta.esquemas import ESQUEMAS
from tfm_nlsql.plataforma.bronze import sesion_spark
from tfm_nlsql.plataforma.silver import promover_silver

pytestmark = pytest.mark.spark

TABLA = "olist_sellers_dataset"
CSV = f"{TABLA}.csv"
FECHA = "2026-09-14"


@pytest.fixture(scope="module")
def spark():
    pytest.importorskip("delta")
    s = sesion_spark()
    yield s
    s.stop()


def test_dos_corridas_mismo_recuento(spark, tmp_path: Path) -> None:
    bronze = tmp_path / "bronze"
    csv = bronze / TABLA / f"fecha_ingesta={FECHA}" / CSV
    csv.parent.mkdir(parents=True)
    cols = ",".join(ESQUEMAS[CSV])
    csv.write_text(cols + "\ns1,01000,sao paulo,SP\n", encoding="utf-8")
    cuarentena = tmp_path / "cuarentena"
    marca = cuarentena / "no-tocar.txt"
    marca.parent.mkdir(parents=True)
    marca.write_text("x", encoding="utf-8")
    mtime_bronze = csv.stat().st_mtime_ns
    mtime_cuarentena = marca.stat().st_mtime_ns
    silver = tmp_path / "silver"
    n1 = promover_silver(bronze, silver, spark)[TABLA]
    n2 = promover_silver(bronze, silver, spark)[TABLA]
    assert n1 == n2 == 1
    assert csv.stat().st_mtime_ns == mtime_bronze
    assert marca.stat().st_mtime_ns == mtime_cuarentena
    dest = silver / TABLA
    assert (dest / "_delta_log").is_dir()
