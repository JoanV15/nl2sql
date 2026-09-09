"""Rutas del repositorio. Configurables por entorno (D-07)."""

from __future__ import annotations

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

CONTRATO = RAIZ / "CONTRATO_SEMANTICO.md"
LANDING = Path(os.environ.get("TFM_LANDING_PATH", RAIZ / "datos" / "landing"))
GOLD_DB = Path(os.environ.get("TFM_GOLD_PATH", RAIZ / "datos" / "gold" / "gold.duckdb"))
TRAZA_DB = Path(os.environ.get("TFM_TRAZA_PATH", RAIZ / "trazas" / "consultas.sqlite"))
LLAMA_URL = os.environ.get("TFM_LLAMA_URL", "http://127.0.0.1:8080")
