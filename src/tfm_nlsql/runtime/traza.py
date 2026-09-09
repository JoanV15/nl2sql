"""Traza persistida de cada consulta (D-22)."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from tfm_nlsql.rutas import TRAZA_DB

_DDL = """
CREATE TABLE IF NOT EXISTS consultas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  pregunta TEXT NOT NULL,
  version_contrato TEXT,
  prompt TEXT,
  sql_crudo TEXT,
  veredicto_validador TEXT,
  reintentos TEXT,
  sql_final TEXT,
  latencia_json TEXT,
  tokens_json TEXT,
  filas_devueltas INTEGER,
  error TEXT
);
"""


@dataclass
class RegistroTraza:
    pregunta: str
    version_contrato: str
    prompt: str
    sql_crudo: str | None
    veredicto_validador: str
    reintentos: list[dict]
    sql_final: str | None
    latencia: dict
    tokens: dict
    filas_devueltas: int | None
    error: str | None = None


def _conectar(ruta: Path | None = None) -> sqlite3.Connection:
    dest = ruta or TRAZA_DB
    dest.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(dest)
    con.execute(_DDL)
    return con


def persistir(reg: RegistroTraza, ruta: Path | None = None) -> int:
    con = _conectar(ruta)
    try:
        cur = con.execute(
            """
            INSERT INTO consultas (
              ts, pregunta, version_contrato, prompt, sql_crudo,
              veredicto_validador, reintentos, sql_final, latencia_json,
              tokens_json, filas_devueltas, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(UTC).isoformat(),
                reg.pregunta,
                reg.version_contrato,
                reg.prompt,
                reg.sql_crudo,
                reg.veredicto_validador,
                json.dumps(reg.reintentos, ensure_ascii=False),
                reg.sql_final,
                json.dumps(reg.latencia),
                json.dumps(reg.tokens),
                reg.filas_devueltas,
                reg.error,
            ),
        )
        con.commit()
        return int(cur.lastrowid)
    finally:
        con.close()
