"""Arnés de execution accuracy del Nivel 1 (D-21). Compara conjuntos, no texto."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from catalogo import NIVEL1  # noqa: E402
from tfm_nlsql.runtime.cliente import metadatos_servidor  # noqa: E402
from tfm_nlsql.runtime.contrato import cargar_contrato  # noqa: E402
from tfm_nlsql.runtime.ejecutor import conexion_lectura, ejecutar  # noqa: E402
from tfm_nlsql.runtime.orquestador import consultar, validar_para_ejecutar  # noqa: E402
from tfm_nlsql.rutas import GOLD_DB  # noqa: E402

SQL_DIR = Path(__file__).parent / "sql_referencia"
INFORME_DIR = Path(__file__).parent / "resultados"

# D-48: la bandera solo aplica a ventas, importes o facturación.
_VENTAS_IMPORTES = re.compile(
    r"venta|vend|factur|importe|ingreso|ticket|gmv|gasto|env[ií]o|flete|precio|caro",
    re.IGNORECASE,
)
_ETIQUETA = re.compile(r"^[A-Za-z0-9._-]+$")


def pregunta_trata_de_ventas(pregunta: str) -> bool:
    return bool(_VENTAS_IMPORTES.search(pregunta))


def es_venta_valida_espurio(pregunta: str, sql: str | None) -> bool:
    if not sql or "es_venta_valida" not in sql.lower():
        return False
    return not pregunta_trata_de_ventas(pregunta)


def _media(xs: list[float | None]) -> float | None:
    vals = [x for x in xs if x is not None]
    return sum(vals) / len(vals) if vals else None


def _tok_s(n: int | float | None, ms: float | None) -> float | None:
    if n is None or ms is None or ms <= 0:
        return None
    return n / (ms / 1000.0)


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
    out["es_venta_valida_espurio"] = es_venta_valida_espurio(pregunta, r.sql)
    out["prompt_n"] = r.prompt_n
    out["prompt_ms"] = r.prompt_ms
    out["predicted_n"] = r.predicted_n
    out["predicted_ms"] = r.predicted_ms
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


def _metadatos(resultados: list[dict]) -> dict:
    _, _, version = cargar_contrato()
    serv = metadatos_servidor()
    prefill = [_tok_s(r.get("prompt_n"), r.get("prompt_ms")) for r in resultados]
    gen = [_tok_s(r.get("predicted_n"), r.get("predicted_ms")) for r in resultados]
    lat = []
    for r in resultados:
        p, g = r.get("prompt_ms"), r.get("predicted_ms")
        lat.append(p + g if p is not None and g is not None else None)
    return {
        "modelo": serv["modelo"],
        "cuantizacion": serv["cuantizacion"],
        "n_ctx": serv["n_ctx"],
        "hilos": serv["hilos"],
        "version_contrato": version,
        "fecha": datetime.now(UTC).isoformat(),
        "prefill_tok_s_medio": _media(prefill),
        "generacion_tok_s_medio": _media(gen),
        "latencia_ms_media": _media(lat),
        "es_venta_valida_espurio": sum(
            1 for r in resultados if r.get("es_venta_valida_espurio")
        ),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Evaluación Nivel 1")
    p.add_argument(
        "--solo-referencia",
        action="store_true",
        help="Ejecuta el SQL de referencia; no llama al modelo",
    )
    p.add_argument(
        "--etiqueta",
        help="Sufijo del informe: nivel1_<etiqueta>.json",
    )
    args = p.parse_args(argv)
    if args.etiqueta and not _ETIQUETA.match(args.etiqueta):
        print(f"Etiqueta inválida: {args.etiqueta!r}", file=sys.stderr)
        return 2
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
    if not args.solo_referencia:
        informe["metadatos"] = _metadatos(resultados)
    INFORME_DIR.mkdir(parents=True, exist_ok=True)
    if args.solo_referencia:
        dest = INFORME_DIR / "nivel1_referencia.json"
    elif args.etiqueta:
        dest = INFORME_DIR / f"nivel1_{args.etiqueta}.json"
    else:
        dest = INFORME_DIR / "nivel1.json"
    dest.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{aciertos}/{total}  → {dest}")
    if not args.solo_referencia:
        print(
            "es_venta_valida espurio:"
            f" {informe['metadatos']['es_venta_valida_espurio']}",
            flush=True,
        )
    return 0 if args.solo_referencia or aciertos == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
