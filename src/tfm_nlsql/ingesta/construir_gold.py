"""Materializa Gold desde Silver (Delta) con dbt-duckdb (Hito 3, D-10)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from tfm_nlsql.ingesta.esquemas import CSV_OBLIGATORIOS
from tfm_nlsql.plataforma.adls import exigir_adls, exigir_duckdb_abfs, uri_capa
from tfm_nlsql.rutas import GOLD_DB, RAIZ, SILVER, es_abfs

TABLAS_SILVER = tuple(Path(n).stem for n in CSV_OBLIGATORIOS)


def ruta_silver_para_dbt() -> str:
    """URI abfs o ruta local. Nunca sustituye abfs por el Silver de disco."""
    crudo = uri_capa("TFM_SILVER_PATH", SILVER)
    if es_abfs(crudo):
        return crudo
    return str(Path(crudo).resolve())


def _comprobar_resenas_mongo(silver: Path = SILVER) -> None:
    marca = silver / "olist_order_reviews_dataset" / "_from_mongo"
    if not marca.is_file():
        raise SystemExit(
            "Silver de reseñas no viene de Mongo (D-32). "
            "Ejecuta `uv run --extra spark --extra mongo tfm-nlsql-resenas`. PARA."
        )


def _comprobar_silver(silver: Path = SILVER) -> None:
    faltan = [t for t in TABLAS_SILVER if not (silver / t).is_dir()]
    if faltan:
        raise SystemExit(
            "Falta Silver en "
            f"{silver}: {', '.join(faltan)}. "
            "Ejecuta `uv run --extra spark tfm-nlsql-silver`."
        )
    _comprobar_resenas_mongo(silver)


def _flags_local() -> dict[str, str]:
    return {
        "TFM_TIENE_EVENTOS": (
            "1" if (SILVER / "eventos_logisticos" / "_delta_log").is_dir() else "0"
        ),
        "TFM_TIENE_CLICKSTREAM": (
            "1" if (SILVER / "eventos_clickstream" / "_delta_log").is_dir() else "0"
        ),
        "TFM_TIENE_FUNNEL": (
            "1"
            if (SILVER / "olist_closed_deals_dataset" / "_delta_log").is_dir()
            and (
                SILVER / "olist_marketing_qualified_leads_dataset" / "_delta_log"
            ).is_dir()
            else "0"
        ),
        "TFM_TIENE_FX": (
            "1" if (SILVER / "tipo_cambio" / "_delta_log").is_dir() else "0"
        ),
    }


def _flags_abfs() -> dict[str, str]:
    # No se inspecciona el Silver local. Un probe de tablas opcionales en
    # ADLS sería otra rebanada; 0 evita mezclar flags de disco con URI.
    return {
        "TFM_TIENE_EVENTOS": "0",
        "TFM_TIENE_CLICKSTREAM": "0",
        "TFM_TIENE_FUNNEL": "0",
        "TFM_TIENE_FX": "0",
    }


def main() -> int:
    exigir_adls()
    silver = ruta_silver_para_dbt()
    if es_abfs(silver):
        exigir_duckdb_abfs(silver)
        flags = _flags_abfs()
    else:
        _comprobar_silver(Path(silver))
        flags = _flags_local()
    GOLD_DB.parent.mkdir(parents=True, exist_ok=True)
    dbt_dir = RAIZ / "dbt"
    dbt = shutil.which("dbt")
    if dbt is None:
        raise SystemExit("dbt no está en PATH; ejecuta dentro de `uv run`.")
    env = os.environ.copy()
    env["TFM_SILVER_PATH"] = silver
    env["TFM_GOLD_PATH"] = str(GOLD_DB.resolve())
    env.update(flags)
    comunes = ["--project-dir", str(dbt_dir), "--profiles-dir", str(dbt_dir)]
    for paso in ("seed", "run", "test"):
        r = subprocess.run([dbt, paso, *comunes], env=env, check=False)
        if r.returncode != 0:
            return r.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
