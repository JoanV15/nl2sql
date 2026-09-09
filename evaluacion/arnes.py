"""Arnés de execution accuracy del Nivel 1 (D-21). Compara conjuntos, no texto."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from catalogo import NIVEL1  # noqa: E402
from tfm_nlsql.runtime.contrato import cargar_contrato  # noqa: E402
from tfm_nlsql.runtime.ejecutor import conexion_lectura, ejecutar  # noqa: E402
from tfm_nlsql.runtime.orquestador import consultar, validar_para_ejecutar  # noqa: E402
from tfm_nlsql.rutas import GOLD_DB  # noqa: E402

SQL_DIR = Path(__file__).parent / "sql_referencia"
INFORME_DIR = Path(__file__).parent / "resultados"


def canon(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, Decimal):
        return round(float(v), 4)
    if isinstance(v, int | float):
        return round(float(v), 4)
    if isinstance(v, datetime):
        return v.isoformat(sep=" ", timespec="seconds")
    if isinstance(v, date):
        return v.isoformat()
    return str(v)


def como_conjunto(filas: list[tuple]) -> set[tuple]:
    return {tuple(canon(c) for c in row) for row in filas}


def cargar_sql(n: int) -> str:
    return (SQL_DIR / f"{n:02d}.sql").read_text(encoding="utf-8").strip()


def ejecutar_referencia(n: int) -> tuple[list[str], list[tuple], str]:
    _, columnas, _ = cargar_contrato()
    sql = cargar_sql(n)
    with conexion_lectura(GOLD_DB) as con:
        reescrito = validar_para_ejecutar(sql, columnas, con)
        cols, filas = ejecutar(con, reescrito)
    return cols, filas, reescrito


def evaluar_una(n: int, pregunta: str, con_modelo: bool) -> dict:
    _, filas_ref, sql_ref = ejecutar_referencia(n)
    out = {
        "n": n,
        "pregunta": pregunta,
        "sql_referencia": sql_ref,
        "acierto": False,
    }
    if not con_modelo:
        out["filas_referencia"] = len(filas_ref)
        out["acierto"] = True
        out["modo"] = "solo_referencia"
        return out
    r = consultar(pregunta, calentar_cache=True)
    out["sql_generado"] = r.sql
    out["abstencion"] = r.abstencion
    out["error"] = r.error
    if r.sql is None:
        out["motivo"] = r.abstencion or r.error or "sin SQL"
        return out
    if como_conjunto(r.filas) == como_conjunto(filas_ref):
        out["acierto"] = True
        return out
    out["motivo"] = "conjuntos distintos"
    out["n_generado"] = len(r.filas)
    out["n_referencia"] = len(filas_ref)
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Evaluación Nivel 1")
    p.add_argument(
        "--solo-referencia",
        action="store_true",
        help="Ejecuta el SQL de referencia; no llama al modelo",
    )
    args = p.parse_args(argv)
    if not GOLD_DB.is_file():
        print(f"No existe Gold en {GOLD_DB}. Ejecuta tfm-nlsql-gold.", file=sys.stderr)
        return 2

    resultados = []
    aciertos = 0
    for n, pregunta in NIVEL1:
        print(f"[{n:02d}] {pregunta}", flush=True)
        try:
            r = evaluar_una(n, pregunta, con_modelo=not args.solo_referencia)
        except Exception as e:
            r = {"n": n, "pregunta": pregunta, "acierto": False, "motivo": str(e)}
        resultados.append(r)
        marca = "OK" if r.get("acierto") else "KO"
        extra = r.get("motivo") or r.get("sql_generado") or ""
        print(f"     {marca} {extra}", flush=True)
        if r.get("acierto"):
            aciertos += 1

    total = len(NIVEL1)
    informe = {
        "nivel": 1,
        "total": total,
        "aciertos": aciertos if not args.solo_referencia else None,
        "precision": (aciertos / total) if not args.solo_referencia else None,
        "modo": "solo_referencia" if args.solo_referencia else "execution_accuracy",
        "detalle": resultados,
    }
    INFORME_DIR.mkdir(parents=True, exist_ok=True)
    dest = INFORME_DIR / (
        "nivel1_referencia.json" if args.solo_referencia else "nivel1.json"
    )
    dest.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{aciertos}/{total}  → {dest}")
    return 0 if args.solo_referencia or aciertos == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
