"""Funnel real (53/54) y tipo de cambio único 2018-10-17 (55, D-15, D-38).

El tipo no entra en el prefijo (D-33): vive en Silver y en importe_articulos_eur.
"""

from __future__ import annotations

import json
import shutil
import sys
import urllib.request
from pathlib import Path

import duckdb

from tfm_nlsql.ingesta.aterrizar import aterrizar_funnel
from tfm_nlsql.ingesta.construir_gold import main as construir_gold
from tfm_nlsql.ingesta.esquemas import CSV_FUNNEL
from tfm_nlsql.plataforma.bronze import (
    fecha_ingesta,
    promover,
    puerto_8080_abierto,
    sesion_spark,
)
from tfm_nlsql.plataforma.silver import promover_silver
from tfm_nlsql.rutas import BRONZE, CUARENTENA, GOLD_DB, LANDING, SILVER

FECHA_REFERENCIA = "2018-10-17"
URL_FX = f"https://api.frankfurter.app/{FECHA_REFERENCIA}?from=BRL&to=EUR"
TABLA_FX = "tipo_cambio"


def parse_frankfurter(payload: dict) -> dict:
    fecha = payload.get("date")
    if fecha != FECHA_REFERENCIA:
        raise ValueError(f"la API no dio {FECHA_REFERENCIA}: {fecha!r}. PARA.")
    if payload.get("base") != "BRL":
        raise ValueError(f"base inesperada: {payload.get('base')!r}. PARA.")
    eur = (payload.get("rates") or {}).get("EUR")
    if not isinstance(eur, int | float) or eur <= 0:
        raise ValueError(f"EUR ausente o inválido: {eur!r}. PARA.")
    return {
        "fecha": fecha,
        "base": "BRL",
        "eur_por_brl": float(eur),
    }


def fetch_fx() -> dict:
    req = urllib.request.Request(
        URL_FX,
        headers={"User-Agent": "tfm-nlsql/0.1 (TFM; +https://github.com/JoanV15/nl2sql)"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = json.load(resp)
    return parse_frankfurter(payload)


def promover_fx(spark, fila: dict) -> int:
    landing = LANDING / f"{TABLA_FX}.json"
    landing.write_text(json.dumps(fila, ensure_ascii=False) + "\n", encoding="utf-8")
    fecha = fecha_ingesta()
    dest_br = BRONZE / TABLA_FX / f"fecha_ingesta={fecha}"
    if dest_br.exists():
        shutil.rmtree(dest_br)
    dest_br.mkdir(parents=True)
    shutil.copy2(landing, dest_br / landing.name)
    df = spark.read.json(str(BRONZE / TABLA_FX))
    dest_ag = SILVER / TABLA_FX
    (
        df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .save(str(dest_ag))
    )
    n = spark.read.format("delta").load(str(dest_ag)).count()
    print(f"  SILVER {TABLA_FX}: {n}")
    return n


def recuentos_gold() -> tuple[int, tuple | None, int]:
    if not GOLD_DB.is_file():
        return 0, None, 0
    con = duckdb.connect(str(GOLD_DB), read_only=True)
    capt = con.execute(
        "SELECT COUNT(*) FROM obt_vendedores WHERE fecha_captacion IS NOT NULL"
    ).fetchone()[0]
    muestra = con.execute(
        """
        SELECT id_pedido, importe_articulos, importe_articulos_eur
        FROM obt_pedidos
        WHERE es_venta_valida AND importe_articulos_eur IS NOT NULL
        LIMIT 1
        """
    ).fetchone()
    eur_nulos = con.execute(
        """
        SELECT COUNT(*) FROM obt_pedidos
        WHERE es_venta_valida AND importe_articulos_eur IS NULL
        """
    ).fetchone()[0]
    return capt, muestra, eur_nulos


def main() -> int:
    if puerto_8080_abierto():
        print(
            "R-08: hay un proceso en 127.0.0.1:8080 (7B). Páralo antes de Spark.",
            file=sys.stderr,
        )
        return 1
    try:
        fila_fx = fetch_fx()
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    except OSError as e:
        print(f"API FX no disponible: {e}. PARA.", file=sys.stderr)
        return 1
    print(
        f"FX {fila_fx['fecha']}: 1 BRL = {fila_fx['eur_por_brl']} EUR (Frankfurter).",
        flush=True,
    )
    aterrizar_funnel()
    spark = sesion_spark()
    try:
        ok, ko = promover(
            LANDING, BRONZE, CUARENTENA, fecha_ingesta(), spark, nombres=CSV_FUNNEL
        )
        if ko or set(ok) != set(CSV_FUNNEL):
            print(f"FALLO funnel Bronze: ok={ok} ko={ko}", file=sys.stderr)
            return 1
        rec = promover_silver(BRONZE, SILVER, spark, csvs=CSV_FUNNEL)
        if any(rec.get(Path(n).stem, 0) == 0 for n in CSV_FUNNEL):
            print(f"FALLO funnel Silver vacío: {rec}", file=sys.stderr)
            return 1
        promover_fx(spark, fila_fx)
    finally:
        spark.stop()
    con = duckdb.connect(":memory:")
    con.execute("INSTALL delta; LOAD delta;")
    cruce = con.execute(
        f"""
        SELECT COUNT(DISTINCT d.seller_id)
        FROM delta_scan('{SILVER / "olist_closed_deals_dataset"}') AS d
        JOIN delta_scan('{SILVER / "olist_sellers_dataset"}') AS s
          ON d.seller_id = s.seller_id
        """
    ).fetchone()[0]
    if cruce == 0:
        print("PARA: el funnel no cruza con seller_id de Olist.", file=sys.stderr)
        return 1
    print(f"Cruce funnel × sellers: {cruce}.", flush=True)
    rc = construir_gold()
    if rc != 0:
        return rc
    capt, muestra, eur_nulos = recuentos_gold()
    print(f"Gold: {capt} vendedores con captación.")
    print(f"Gold: pedido de muestra EUR {muestra}.")
    if capt == 0:
        print("FALLO: fecha_captacion sigue todo-NULL.")
        return 1
    if muestra is None or eur_nulos:
        print(f"FALLO: importe_articulos_eur NULL en ventas válidas ({eur_nulos}).")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
