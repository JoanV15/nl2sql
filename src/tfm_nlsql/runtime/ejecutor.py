"""Ejecutor DuckDB en solo lectura (D-19 capas 3 y 4)."""

from __future__ import annotations

import threading
from collections.abc import Sequence
from contextlib import contextmanager
from pathlib import Path

import duckdb

from tfm_nlsql.runtime.validador import ErrorValidacion

MEMORIA = "1GB"
HILOS = 2
TIMEOUT_S = 30


@contextmanager
def conexion_lectura(ruta: Path):
    con = duckdb.connect(
        str(ruta),
        read_only=True,
        config={
            "enable_external_access": False,
            "memory_limit": MEMORIA,
            "threads": HILOS,
        },
    )
    try:
        yield con
    finally:
        con.close()


def validar_binding(con: duckdb.DuckDBPyConnection, sql: str) -> None:
    try:
        con.execute(f"EXPLAIN {sql}")
    except duckdb.Error as e:
        raise ErrorValidacion(f"binding: {e}") from e


def ejecutar(con: duckdb.DuckDBPyConnection, sql: str) -> tuple[list[str], list[tuple]]:
    resultado: dict = {}
    error: list[BaseException] = []

    def _correr() -> None:
        try:
            cur = con.execute(sql)
            cols = [d[0] for d in cur.description] if cur.description else []
            filas = cur.fetchall()
            resultado["cols"] = cols
            resultado["filas"] = filas
        except BaseException as e:  # noqa: BLE001 — se re-lanza fuera
            error.append(e)

    hilo = threading.Thread(target=_correr, daemon=True)
    hilo.start()
    hilo.join(TIMEOUT_S)
    if hilo.is_alive():
        con.interrupt()
        hilo.join(5)
        raise TimeoutError(f"consulta superó {TIMEOUT_S}s")
    if error:
        raise error[0]
    return resultado["cols"], resultado["filas"]


def formatear(columnas: Sequence[str], filas: Sequence[tuple]) -> str:
    if not columnas:
        return "(sin filas)"
    anchos = [len(c) for c in columnas]
    texto = []
    for fila in filas:
        celdas = [("NULL" if v is None else str(v)) for v in fila]
        texto.append(celdas)
        for i, c in enumerate(celdas):
            anchos[i] = max(anchos[i], len(c))
    sep = " | "
    cab = sep.join(c.ljust(anchos[i]) for i, c in enumerate(columnas))
    raya = "-+-".join("-" * a for a in anchos)
    cuerpo = "\n".join(
        sep.join(c.ljust(anchos[i]) for i, c in enumerate(fila)) for fila in texto
    )
    if not texto:
        return f"{cab}\n{raya}\n(sin filas)"
    return f"{cab}\n{raya}\n{cuerpo}"
