"""Spark Structured Streaming available-now: Kafka → Landing/Bronze (D-09)."""

from __future__ import annotations

import shutil
from pathlib import Path

from tfm_nlsql.ingesta.kafka_local import BOOTSTRAP, TOPIC, TOPIC_CLICKSTREAM
from tfm_nlsql.plataforma.bronze import fecha_ingesta, sesion_spark
from tfm_nlsql.rutas import BRONZE, LANDING, SILVER

TABLA = "eventos_logisticos"
TABLA_CLICKSTREAM = "eventos_clickstream"
PAQUETE_KAFKA = "org.apache.spark:spark-sql-kafka-0-10_2.13:4.2.0"


def _esquema_logistica():
    from pyspark.sql.types import BooleanType, StringType, StructField, StructType

    return StructType(
        [
            StructField("order_id", StringType()),
            StructField("id_transportista", StringType()),
            StructField("tipo_incidencia", StringType()),
            StructField("es_simulado", BooleanType()),
        ]
    )


def _esquema_clickstream():
    from pyspark.sql.types import (
        BooleanType,
        IntegerType,
        StringType,
        StructField,
        StructType,
    )

    return StructType(
        [
            StructField("fecha", StringType()),
            StructField("product_id", StringType()),
            StructField("num_visitas", IntegerType()),
            StructField("num_anadidos_carrito", IntegerType()),
            StructField("num_carritos_abandonados", IntegerType()),
            StructField("num_compras", IntegerType()),
            StructField("es_simulado", BooleanType()),
        ]
    )


def drenar_a_landing(spark, landing: Path, topic: str, tabla: str, esquema) -> Path:
    from pyspark.sql.functions import col, from_json

    dest = landing / tabla
    if dest.exists():
        shutil.rmtree(dest)
    ckpt = landing.parent / "checkpoints" / tabla
    if ckpt.exists():
        shutil.rmtree(ckpt)
    df = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", BOOTSTRAP)
        .option("subscribe", topic)
        .option("startingOffsets", "earliest")
        .option("failOnDataLoss", "false")
        .load()
        .select(from_json(col("value").cast("string"), esquema).alias("e"))
        .select("e.*")
    )
    consulta = (
        df.writeStream.trigger(availableNow=True)
        .format("json")
        .option("path", str(dest))
        .option("checkpointLocation", str(ckpt))
        .start()
    )
    consulta.awaitTermination()
    return dest


def promover_bronze_y_silver(
    spark,
    landing: Path,
    bronze: Path,
    silver: Path,
    tabla: str,
    claves_dedup: list[str],
) -> int:
    fecha = fecha_ingesta()
    origen = landing / tabla
    dest_br = bronze / tabla / f"fecha_ingesta={fecha}"
    if dest_br.exists():
        shutil.rmtree(dest_br)
    dest_br.mkdir(parents=True)
    copiados = list(origen.glob("*.json"))
    if not copiados:
        raise SystemExit(f"Spark no escribió JSON en {origen}")
    for part in copiados:
        shutil.copy2(part, dest_br / part.name)
    df = spark.read.json(str(bronze / tabla)).dropDuplicates(claves_dedup)
    dest_ag = silver / tabla
    (
        df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .save(str(dest_ag))
    )
    n = spark.read.format("delta").load(str(dest_ag)).count()
    print(f"  SILVER {tabla}: {n}")
    return n


def _drenar(topic: str, tabla: str, esquema, claves_dedup: list[str]) -> int:
    spark = sesion_spark(extra_packages=[PAQUETE_KAFKA])
    try:
        drenar_a_landing(spark, LANDING, topic, tabla, esquema)
        return promover_bronze_y_silver(
            spark, LANDING, BRONZE, SILVER, tabla, claves_dedup
        )
    finally:
        spark.stop()


def drenar() -> int:
    return _drenar(TOPIC, TABLA, _esquema_logistica(), ["order_id"])


def drenar_clickstream() -> int:
    return _drenar(
        TOPIC_CLICKSTREAM,
        TABLA_CLICKSTREAM,
        _esquema_clickstream(),
        ["fecha", "product_id"],
    )
