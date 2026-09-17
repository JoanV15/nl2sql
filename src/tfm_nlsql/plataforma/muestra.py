"""dbt build de muestra en DuckDB efímero (D-25). Sin Spark ni Olist completo."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from tfm_nlsql.rutas import RAIZ


def construir_muestra(gold: Path) -> int:
    gold.parent.mkdir(parents=True, exist_ok=True)
    dbt_dir = RAIZ / "dbt"
    dbt = shutil.which("dbt")
    if dbt is None:
        raise SystemExit("dbt no está en PATH; ejecuta dentro de `uv run`.")
    env = os.environ.copy()
    env["TFM_GOLD_PATH"] = str(gold.resolve())
    comunes = [
        "--project-dir",
        str(dbt_dir),
        "--profiles-dir",
        str(dbt_dir),
        "--target",
        "ci",
    ]
    for paso in ("seed", "run", "test"):
        r = subprocess.run([dbt, paso, *comunes], env=env, check=False)
        if r.returncode != 0:
            return r.returncode
    return 0


def main() -> int:
    destino = Path(
        os.environ.get("TFM_GOLD_PATH", str(RAIZ / "datos" / "gold" / "ci.duckdb"))
    )
    return construir_muestra(destino)


if __name__ == "__main__":
    raise SystemExit(main())
