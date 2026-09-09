"""Materializa Gold desde los CSV de Landing con dbt-duckdb (Hito 1, D-23)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

from tfm_nlsql.rutas import GOLD_DB, LANDING, RAIZ

CSV_OBLIGATORIOS = (
    "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_customers_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
)


def _comprobar_landing() -> None:
    faltan = [n for n in CSV_OBLIGATORIOS if not (LANDING / n).is_file()]
    if faltan:
        raise SystemExit(
            "Faltan CSV en "
            f"{LANDING}: {', '.join(faltan)}. "
            "Colócalos o ejecuta `uv run --extra landing tfm-nlsql-aterrizar`."
        )


def main() -> int:
    _comprobar_landing()
    GOLD_DB.parent.mkdir(parents=True, exist_ok=True)
    dbt_dir = RAIZ / "dbt"
    dbt = shutil.which("dbt")
    if dbt is None:
        raise SystemExit("dbt no está en PATH; ejecuta dentro de `uv run`.")
    env = os.environ.copy()
    env["TFM_LANDING_PATH"] = str(LANDING.resolve())
    env["TFM_GOLD_PATH"] = str(GOLD_DB.resolve())
    comunes = ["--project-dir", str(dbt_dir), "--profiles-dir", str(dbt_dir)]
    for paso in ("seed", "run", "test"):
        r = subprocess.run([dbt, paso, *comunes], env=env, check=False)
        if r.returncode != 0:
            return r.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
