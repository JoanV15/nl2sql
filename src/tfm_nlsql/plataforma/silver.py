"""Bronze → Silver en Delta Lake (D-10).

Idempotencia por overwrite de la tabla particionada por `fecha_ingesta`,
no por MERGE: las claves no están en DECISIONES.md y el criterio de hecho
es el recuento estable entre dos corridas.

Overwrite de tabla, no MERGE. El snapshot es la última fecha_ingesta de
Bronze (un CSV aterrizado N días no es N copias). Un job incremental
exigiría una D-xx con las PKs de origen y MERGE.

Nombres de origen (D-36). D-31: retención de ficheros eliminados 7 días,
log 30 días (valores por defecto de Delta). VACUUM es asset de Dagster
(Hito 5); no se ejecuta aquí.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from tfm_nlsql.ingesta.esquemas import (
    CSV_FUNNEL,
    CSV_OBLIGATORIOS,
    ESQUEMAS,
)
from tfm_nlsql.plataforma.adls import join_capa
from tfm_nlsql.plataforma.bronze import puerto_8080_abierto, sesion_spark
from tfm_nlsql.rutas import BRONZE, CUARENTENA, SILVER, es_abfs

PARTICION = "fecha_ingesta"


def _schema(columnas: tuple[str, ...]):
    from pyspark.sql.types import StringType, StructField, StructType

    return StructType([StructField(c, StringType(), True) for c in columnas])


def _snapshot(df):
    from pyspark.sql import functions as F

    if PARTICION not in df.columns:
        return df
    ultima = df.agg(F.max(PARTICION)).first()[0]
    if ultima is None:
        return df
    return df.filter(F.col(PARTICION) == ultima)


def _leer_bronze(spark, bronze: Path | str, csv_name: str):
    tabla = Path(csv_name).stem
    origen = join_capa(bronze, tabla)
    return (
        spark.read.option("header", "true")
        .option("multiLine", "true")
        .option("quote", '"')
        .option("escape", '"')
        .option("encoding", "UTF-8")
        .option("basePath", origen)
        .schema(_schema(ESQUEMAS[csv_name]))
        .csv(origen)
    )


def promover_silver(
    bronze: Path | str,
    silver: Path | str,
    spark,
    csvs: tuple[str, ...] | None = None,
) -> dict[str, int]:
    """Escribe Delta en Silver. No toca Bronze ni cuarentena."""
    recuentos: dict[str, int] = {}
    if not es_abfs(str(silver)):
        Path(silver).mkdir(parents=True, exist_ok=True)
    lote = csvs if csvs is not None else CSV_OBLIGATORIOS
    for csv_name in lote:
        if csv_name == "olist_order_reviews_dataset.csv":
            continue
        tabla = Path(csv_name).stem
        origen = join_capa(bronze, tabla)
        if not es_abfs(origen) and not Path(origen).is_dir():
            continue
        df = _snapshot(_leer_bronze(spark, bronze, csv_name))
        dest = join_capa(silver, tabla)
        if not es_abfs(dest) and Path(dest).exists():
            shutil.rmtree(dest)
        (
            df.write.format("delta")
            .mode("overwrite")
            .option("overwriteSchema", "true")
            .partitionBy(PARTICION)
            .save(dest)
        )
        n = spark.read.format("delta").load(dest).count()
        recuentos[tabla] = n
        print(f"  SILVER {tabla}: {n}")
        df.unpersist()
    return recuentos


def _hay_bronze(bronze: Path | str) -> bool:
    if es_abfs(str(bronze)):
        return True
    return any((Path(bronze) / Path(n).stem).is_dir() for n in CSV_OBLIGATORIOS)


def main() -> int:
    from tfm_nlsql.plataforma.adls import exigir_adls, uri_capa

    exigir_adls()
    if puerto_8080_abierto():
        print(
            "R-08: hay un proceso en 127.0.0.1:8080 (7B). "
            "Páralo antes de levantar Spark.",
            file=sys.stderr,
        )
        return 1
    if not _hay_bronze(BRONZE):
        print(
            f"No hay Bronze en {BRONZE}. "
            "Ejecuta `uv run --extra spark tfm-nlsql-bronze`.",
            file=sys.stderr,
        )
        return 1
    bronze_antes = _mtime_arbol(BRONZE)
    cuarentena_antes = _mtime_arbol(CUARENTENA)
    spark = sesion_spark()
    try:
        print(f"Bronze → Silver (overwrite, {PARTICION})")
        csvs = tuple(
            n
            for n in (*CSV_OBLIGATORIOS, *CSV_FUNNEL)
            if n != "olist_order_reviews_dataset.csv"
            and (BRONZE / Path(n).stem).is_dir()
        )
        dest_silver = uri_capa("TFM_SILVER_PATH", SILVER)
        a = promover_silver(BRONZE, dest_silver, spark, csvs=csvs)
        b = promover_silver(BRONZE, dest_silver, spark, csvs=csvs)
    finally:
        spark.stop()
    if a != b:
        print(f"FALLO: recuentos distintos entre corridas: {a} vs {b}", file=sys.stderr)
        return 1
    if _mtime_arbol(BRONZE) != bronze_antes:
        print("FALLO: Bronze se ha reescrito.", file=sys.stderr)
        return 1
    if _mtime_arbol(CUARENTENA) != cuarentena_antes:
        print("FALLO: cuarentena se ha reescrito.", file=sys.stderr)
        return 1
    return 0


def _mtime_arbol(raiz: Path) -> tuple[tuple[str, int], ...]:
    if not raiz.exists():
        return ()
    return tuple(
        sorted(
            (str(p.relative_to(raiz)), p.stat().st_mtime_ns)
            for p in raiz.rglob("*")
            if p.is_file()
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
