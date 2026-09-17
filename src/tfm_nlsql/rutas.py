"""Rutas del repositorio. Configurables por entorno (D-07)."""

from __future__ import annotations

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def es_abfs(valor: str) -> bool:
    return valor.startswith(("abfs://", "abfss://"))


def _path_local(var: str, default: Path) -> Path:
    crudo = os.environ.get(var)
    if not crudo or es_abfs(crudo):
        return default
    return Path(crudo)


def resolver_gold(crudo: str | None = None) -> Path:
    """Gold es un fichero DuckDB local (D-07, D-59). abfs → PARA."""
    valor = os.environ.get("TFM_GOLD_PATH") if crudo is None else crudo
    if valor and es_abfs(valor):
        raise SystemExit(
            "Gold es DuckDB local (D-07). TFM_GOLD_PATH no admite abfs. PARA."
        )
    if not valor:
        return RAIZ / "datos" / "gold" / "gold.duckdb"
    return Path(valor)


CONTRATO = RAIZ / "CONTRATO_SEMANTICO.md"
LANDING = _path_local("TFM_LANDING_PATH", RAIZ / "datos" / "landing")
BRONZE = _path_local("TFM_BRONZE_PATH", RAIZ / "datos" / "bronze")
SILVER = _path_local("TFM_SILVER_PATH", RAIZ / "datos" / "silver")
CUARENTENA = _path_local(
    "TFM_CUARENTENA_PATH", RAIZ / "datos" / "landing" / "cuarentena"
)
GOLD_DB = resolver_gold()
TRAZA_DB = Path(os.environ.get("TFM_TRAZA_PATH", RAIZ / "trazas" / "consultas.sqlite"))
LLAMA_URL = os.environ.get("TFM_LLAMA_URL", "http://127.0.0.1:8080")
