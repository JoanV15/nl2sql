"""Gold se reconstruye desde Silver, sin CSV de Landing."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tfm_nlsql.ingesta.construir_gold import _comprobar_silver
from tfm_nlsql.rutas import RAIZ, SILVER


def test_sin_silver_falla_sin_pedir_landing(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="Silver"):
        _comprobar_silver(tmp_path / "silver")


def test_gold_sin_csv_en_landing(tmp_path: Path) -> None:
    if not (SILVER / "olist_orders_dataset").is_dir():
        pytest.skip("Silver no materializado")
    if not (SILVER / "olist_order_reviews_dataset" / "_from_mongo").is_file():
        pytest.skip("reseñas Mongo no ingeridas")
    landing = tmp_path / "landing"
    landing.mkdir()
    gold = tmp_path / "gold.duckdb"
    env = os.environ.copy()
    env["TFM_LANDING_PATH"] = str(landing)
    env["TFM_SILVER_PATH"] = str(SILVER.resolve())
    env["TFM_GOLD_PATH"] = str(gold)
    r = subprocess.run(
        [sys.executable, "-m", "tfm_nlsql.ingesta.construir_gold"],
        cwd=RAIZ,
        env=env,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    assert gold.is_file()
    assert not list(landing.glob("*.csv"))
