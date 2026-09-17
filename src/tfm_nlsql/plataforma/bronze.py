"""Landing → Bronze con Spark local (D-08).

Un CSV que no cumple el esquema de origen no se escribe en Bronze: el
fichero entero va a cuarentena. Spark lee en PERMISSIVE y rellena
`_corrupt_record`; el detector es a grano registro, el aislamiento a
grano fichero.

El aislamiento es a grano fichero (criterio de hecho del Hito 3). D-08
admite aislar solo la fila: filtrar `_corrupt_record` nulo hacia Bronze y
el resto a cuarentena, sin cambiar el detector.

Silver en Delta y VACUUM no viven aquí. D-31: retención de ficheros
eliminados 7 días, log 30 días; VACUUM como asset de Dagster tras un
pipeline correcto (Hito 5). No se orquesta en este módulo.
"""

from __future__ import annotations

import csv
import io
import os
import shutil
import socket
import sys
from datetime import date
from pathlib import Path

from tfm_nlsql.ingesta.esquemas import CSV_FUNNEL, CSV_OBLIGATORIOS, ESQUEMAS
from tfm_nlsql.rutas import BRONZE, CUARENTENA, LANDING, RAIZ

COLUMNA_CORRUPTO = "_corrupt_record"
PARTICION = "fecha_ingesta"


def puerto_8080_abierto() -> bool:
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", 8080)) == 0


def sesion_spark(*, extra_packages: list[str] | None = None):
    from delta import configure_spark_with_delta_pip
    from pyspark.sql import SparkSession

    from tfm_nlsql.plataforma.adls import configurar_spark_adls

    # 2g: cabe en los 6 Gi libres de R-08 con el 7B apagado. local[1]
    # evita picos de executor en WSL. Delta va siempre: un getOrCreate
    # previo sin el JAR deja Silver sin `delta` (pytest de cuarentena).
    os.environ.setdefault("SPARK_LOCAL_IP", "127.0.0.1")
    activa = SparkSession.getActiveSession()
    if activa is not None:
        activa.stop()
    builder = (
        SparkSession.builder.master("local[1]")
        .appName("tfm-nlsql")
        .config("spark.driver.memory", os.environ.get("SPARK_DRIVER_MEMORY", "2g"))
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.default.parallelism", "1")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
    )
    builder, paquetes = configurar_spark_adls(builder, extra_packages)
    return configure_spark_with_delta_pip(
        builder, extra_packages=paquetes or None
    ).getOrCreate()


def fecha_ingesta() -> str:
    return os.environ.get("TFM_FECHA_INGESTA", date.today().isoformat())


def cabecera_de(ruta: Path) -> list[str]:
    with ruta.open(encoding="utf-8-sig", newline="") as fh:
        fila = next(csv.reader(fh), None)
    if not fila:
        return []
    return [c.strip() for c in fila]


def _destino(raiz: Path, csv_name: str, fecha: str) -> Path:
    tabla = Path(csv_name).stem
    dest = raiz / tabla / f"{PARTICION}={fecha}" / csv_name
    dest.parent.mkdir(parents=True, exist_ok=True)
    return dest


def _copiar(origen: Path, dest: Path) -> Path:
    shutil.copy2(origen, dest)
    return dest


def _tiene_corrupto(spark, ruta: Path, columnas: tuple[str, ...]) -> bool:
    from pyspark.sql.types import StringType, StructField, StructType

    campos = [StructField(c, StringType(), True) for c in columnas]
    campos.append(StructField(COLUMNA_CORRUPTO, StringType(), True))
    df = (
        spark.read.option("header", "true")
        .option("mode", "PERMISSIVE")
        .option("columnNameOfCorruptRecord", COLUMNA_CORRUPTO)
        .option("encoding", "UTF-8")
        .option("multiLine", "true")
        .option("quote", '"')
        .option("escape", '"')
        .schema(StructType(campos))
        .csv(str(ruta))
    )
    # cache: sin él Spark puede no materializar `_corrupt_record` (SPARK-21610)
    df = df.cache()
    try:
        return df.filter(df[COLUMNA_CORRUPTO].isNotNull()).limit(1).count() > 0
    finally:
        df.unpersist()


def promover(
    landing: Path,
    bronze: Path,
    cuarentena: Path,
    fecha: str,
    spark,
    nombres: tuple[str, ...] | None = None,
) -> tuple[list[str], list[str]]:
    """Copia CSV sanos a Bronze; los que fallan el esquema, a cuarentena."""
    ok: list[str] = []
    ko: list[str] = []
    bronze.mkdir(parents=True, exist_ok=True)
    cuarentena.mkdir(parents=True, exist_ok=True)
    lote = nombres if nombres is not None else CSV_OBLIGATORIOS
    for nombre in lote:
        src = landing / nombre
        if not src.is_file():
            continue
        columnas = ESQUEMAS[nombre]
        motivo = None
        if cabecera_de(src) != list(columnas):
            motivo = "cabecera"
        elif _tiene_corrupto(spark, src, columnas):
            motivo = COLUMNA_CORRUPTO
        if motivo:
            _copiar(src, _destino(cuarentena, nombre, fecha))
            _destino(bronze, nombre, fecha).unlink(missing_ok=True)
            ko.append(nombre)
            print(f"  CUARENTENA ({motivo}): {nombre}")
        else:
            _copiar(src, _destino(bronze, nombre, fecha))
            _destino(cuarentena, nombre, fecha).unlink(missing_ok=True)
            ok.append(nombre)
            print(f"  BRONZE: {nombre}")
    return ok, ko


def _fila(columnas: tuple[str, ...], valores: list[str]) -> str:
    buf: list[str] = []
    s = io.StringIO()
    w = csv.writer(s, lineterminator="")
    w.writerow(columnas)
    buf.append(s.getvalue())
    s = io.StringIO()
    w = csv.writer(s, lineterminator="")
    w.writerow(valores)
    buf.append(s.getvalue())
    return "\n".join(buf) + "\n"


def demostrar_cuarentena(base: Path, spark, fecha: str) -> bool:
    """Rompe un CSV a propósito. False si el corrupto aparece en Bronze."""
    landing = base / "landing"
    bronze = base / "bronze"
    cuarentena = base / "cuarentena"
    landing.mkdir(parents=True, exist_ok=True)
    sano = "olist_customers_dataset.csv"
    malo = "olist_sellers_dataset.csv"
    (landing / sano).write_text(
        _fila(
            ESQUEMAS[sano],
            ["c1", "u1", "01000", "sao paulo", "SP"],
        ),
        encoding="utf-8",
    )
    (landing / malo).write_text(
        ",".join(ESQUEMAS[malo])
        + "\n"
        + "seller-roto,sin-campos-suficientes\n"
        + 'seller-x,00000,"ciudad con comilla sin cerrar\n',
        encoding="utf-8",
    )
    print(f"Demo cuarentena: {base}")
    ok, ko = promover(landing, bronze, cuarentena, fecha, spark)
    if _destino(bronze, malo, fecha).is_file():
        print("FALLO: el CSV corrupto está en Bronze.")
        return False
    if malo not in ko or sano not in ok:
        print(
            f"FALLO: esperado {sano} en Bronze y {malo} en cuarentena; ok={ok} ko={ko}"
        )
        return False
    if not _destino(cuarentena, malo, fecha).is_file():
        print("FALLO: el CSV corrupto no está en cuarentena.")
        return False
    print(f"  sano → {_destino(bronze, sano, fecha)}")
    print(f"  corrupto → {_destino(cuarentena, malo, fecha)}")
    return True


def main() -> int:
    from tfm_nlsql.plataforma.adls import exigir_adls

    exigir_adls()
    if puerto_8080_abierto():
        print(
            "R-08: hay un proceso en 127.0.0.1:8080 (7B). "
            "Páralo antes de levantar Spark.",
            file=sys.stderr,
        )
        return 1
    faltan = [n for n in CSV_OBLIGATORIOS if not (LANDING / n).is_file()]
    if faltan:
        print(
            f"Faltan CSV en {LANDING}: {', '.join(faltan)}. "
            "Ejecuta `uv run --extra landing tfm-nlsql-aterrizar`.",
            file=sys.stderr,
        )
        return 1
    fecha = fecha_ingesta()
    spark = sesion_spark()
    try:
        print(f"Landing → Bronze ({PARTICION}={fecha})")
        presentes = tuple(
            n for n in (*CSV_OBLIGATORIOS, *CSV_FUNNEL) if (LANDING / n).is_file()
        )
        promover(LANDING, BRONZE, CUARENTENA, fecha, spark, nombres=presentes)
        demo = RAIZ / "datos" / "demo_cuarentena"
        if demo.exists():
            shutil.rmtree(demo)
        if not demostrar_cuarentena(demo, spark, fecha):
            return 1
    finally:
        spark.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
