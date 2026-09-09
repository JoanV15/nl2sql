"""Arnés de execution accuracy (D-21, D-50). Precisión por nivel, nunca agregada."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(RAIZ / "src"))

from catalogo import ABSTENCION, NIVEL2, NIVEL3  # noqa: E402
from tfm_nlsql.runtime.cliente import metadatos_servidor  # noqa: E402
from tfm_nlsql.runtime.contrato import cargar_contrato  # noqa: E402
from tfm_nlsql.runtime.ejecutor import conexion_lectura, ejecutar  # noqa: E402
from tfm_nlsql.runtime.orquestador import consultar, validar_para_ejecutar  # noqa: E402
from tfm_nlsql.runtime.validador import (  # noqa: E402
    ErrorValidacion,
    inyectar_limite,
    validar_politica,
)
from tfm_nlsql.rutas import GOLD_DB  # noqa: E402

SQL_DIR = Path(__file__).parent / "sql_referencia"
INFORME_DIR = Path(__file__).parent / "resultados"

BLOQUES: tuple[tuple[str, str, list[tuple[int, str]]], ...] = (
    ("nivel2", "Nivel 2", NIVEL2),
    ("nivel3", "Nivel 3", NIVEL3),
    ("abstencion", "Abstención", ABSTENCION),
)

# D-48: la bandera solo aplica a ventas, importes o facturación.
_VENTAS_IMPORTES = re.compile(
    r"venta|vend|factur|importe|ingreso|ticket|gmv|gasto|env[ií]o|flete|precio|caro",
    re.IGNORECASE,
)
_ETIQUETA = re.compile(r"^[A-Za-z0-9._-]+$")
_RECHAZO_DML = "solo se permiten SELECT y WITH"


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


def _anotar_modelo(out: dict, pregunta: str, r) -> None:
    out["sql_generado"] = r.sql
    out["abstencion"] = r.abstencion
    out["error"] = r.error
    out["es_venta_valida_espurio"] = es_venta_valida_espurio(pregunta, r.sql)
    out["prompt_n"] = r.prompt_n
    out["prompt_ms"] = r.prompt_ms
    out["predicted_n"] = r.predicted_n
    out["predicted_ms"] = r.predicted_ms


def evaluar_una(n: int, pregunta: str, con_modelo: bool) -> dict:
    sql_crudo = cargar_sql(n)
    out = {
        "n": n,
        "pregunta": pregunta,
        "sql_referencia": sql_crudo,
        "acierto": False,
    }
    cabeza = sql_crudo.lstrip().upper()
    if cabeza.startswith("ABSTENCION"):
        if not con_modelo:
            out["acierto"] = True
            out["modo"] = "solo_referencia"
            out["tipo"] = "abstencion"
            return out
        r = consultar(pregunta, calentar_cache=True)
        _anotar_modelo(out, pregunta, r)
        out["acierto"] = r.abstencion is not None
        if not out["acierto"]:
            out["motivo"] = r.error or "el modelo no se abstuvo"
        return out
    if cabeza.startswith("DELETE"):
        if not con_modelo:
            _, columnas, _ = cargar_contrato()
            try:
                validar_politica(inyectar_limite(sql_crudo), columnas)
            except ErrorValidacion as e:
                out["acierto"] = True
                out["modo"] = "solo_referencia"
                out["tipo"] = "rechazo_validador"
                out["motivo"] = e.motivo
                return out
            out["motivo"] = "el validador no rechazó el DML"
            return out
        r = consultar(pregunta, calentar_cache=True)
        _anotar_modelo(out, pregunta, r)
        if r.abstencion:
            out["acierto"] = True
            out["tipo"] = "abstencion"
            return out
        if r.error and _RECHAZO_DML in r.error:
            out["acierto"] = True
            out["tipo"] = "rechazo_validador"
            return out
        out["motivo"] = r.error or "ni abstención ni rechazo DML"
        return out
    _, filas_ref, sql_ref = ejecutar_referencia(n)
    out["sql_referencia"] = sql_ref
    if not con_modelo:
        out["filas_referencia"] = len(filas_ref)
        out["acierto"] = True
        out["modo"] = "solo_referencia"
        return out
    r = consultar(pregunta, calentar_cache=True)
    _anotar_modelo(out, pregunta, r)
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


def _recuento(resultados: list[dict], preguntas: list[tuple[int, str]]) -> dict:
    ns = {n for n, _ in preguntas}
    sub = [r for r in resultados if r["n"] in ns]
    total = len(preguntas)
    aciertos = sum(1 for r in sub if r.get("acierto"))
    return {
        "ids": [n for n, _ in preguntas],
        "total": total,
        "aciertos": aciertos,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Evaluación Niveles 2 y 3 y abstención (D-50 por nivel)"
    )
    p.add_argument(
        "--solo-referencia",
        action="store_true",
        help="Ejecuta el SQL de referencia; no llama al modelo",
    )
    p.add_argument(
        "--etiqueta",
        help="Sufijo del informe: hito2_<etiqueta>.json",
    )
    args = p.parse_args(argv)
    if args.etiqueta and not _ETIQUETA.match(args.etiqueta):
        print(f"Etiqueta inválida: {args.etiqueta!r}", file=sys.stderr)
        return 2
    if not GOLD_DB.is_file():
        print(f"No existe Gold en {GOLD_DB}. Ejecuta tfm-nlsql-gold.", file=sys.stderr)
        return 2

    ids = [n for _, _, ps in BLOQUES for n, _ in ps]
    faltan = [n for n in ids if not (SQL_DIR / f"{n:02d}.sql").is_file()]
    if faltan:
        print(f"Falta SQL de referencia: {faltan}", file=sys.stderr)
        return 2

    resultados = []
    con_modelo = not args.solo_referencia
    for _clave, _titulo, preguntas in BLOQUES:
        for n, pregunta in preguntas:
            print(f"[{n:02d}] {pregunta}", flush=True)
            try:
                r = evaluar_una(n, pregunta, con_modelo=con_modelo)
            except Exception as e:
                r = {"n": n, "pregunta": pregunta, "acierto": False, "motivo": str(e)}
            resultados.append(r)
            marca = "OK" if r.get("acierto") else "KO"
            extra = r.get("motivo") or r.get("tipo") or r.get("sql_generado") or ""
            print(f"     {marca} {extra}", flush=True)

    bloques_out = {}
    for clave, titulo, preguntas in BLOQUES:
        rec = _recuento(resultados, preguntas)
        if args.solo_referencia:
            rec["aciertos"] = None
        bloques_out[clave] = rec
        if args.solo_referencia:
            print(f"{titulo}: {rec['total']}", flush=True)
        else:
            print(f"{titulo}: {rec['aciertos']}/{rec['total']}", flush=True)

    informe = {
        "bloques": bloques_out,
        "modo": "solo_referencia" if args.solo_referencia else "execution_accuracy",
        "detalle": resultados,
    }
    if not args.solo_referencia:
        informe["metadatos"] = _metadatos(resultados)
    INFORME_DIR.mkdir(parents=True, exist_ok=True)
    if args.solo_referencia:
        dest = INFORME_DIR / "hito2_referencia.json"
    elif args.etiqueta:
        dest = INFORME_DIR / f"hito2_{args.etiqueta}.json"
    else:
        dest = INFORME_DIR / "hito2.json"
    dest.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"→ {dest}")
    if not args.solo_referencia:
        print(
            "es_venta_valida espurio:"
            f" {informe['metadatos']['es_venta_valida_espurio']}",
            flush=True,
        )
        if any(b["aciertos"] != b["total"] for b in bloques_out.values()):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
