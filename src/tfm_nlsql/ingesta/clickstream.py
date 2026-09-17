"""Clickstream simulado sobre id_producto y fechas reales (D-09, R-05).

Grano Kafka/Silver: día × producto. Gold añade categoría; no se inventan
columnas. es_simulado en el evento; el contrato ya declara la OBT simulada.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import sys

import duckdb

from tfm_nlsql.ingesta.construir_gold import main as construir_gold
from tfm_nlsql.ingesta.kafka_local import (
    BOOTSTRAP,
    TOPIC_CLICKSTREAM,
    producir,
    puerto_abierto,
    raiz_kafka,
)
from tfm_nlsql.plataforma.bronze import puerto_8080_abierto
from tfm_nlsql.plataforma.drenar_kafka import drenar_clickstream
from tfm_nlsql.rutas import GOLD_DB, SILVER


def evento_de(product_id: str, fecha: str) -> dict:
    h = int(
        hashlib.md5(
            f"{product_id}|{fecha}".encode(), usedforsecurity=False
        ).hexdigest(),
        16,
    )
    visitas = 5 + (h % 96)
    anadidos = visitas * ((h % 5) + 1) // 10
    compras = anadidos * (h % 4) // 5
    return {
        "fecha": fecha,
        "product_id": product_id,
        "num_visitas": visitas,
        "num_anadidos_carrito": anadidos,
        "num_carritos_abandonados": anadidos - compras,
        "num_compras": compras,
        "es_simulado": True,
    }


def pares_reales(n: int) -> list[tuple[str, str]]:
    items = SILVER / "olist_order_items_dataset"
    orders = SILVER / "olist_orders_dataset"
    if not items.is_dir() or not orders.is_dir():
        raise SystemExit(
            f"Falta Silver en {items} o {orders}. Ejecuta tfm-nlsql-silver."
        )
    con = duckdb.connect(":memory:")
    con.execute("INSTALL delta; LOAD delta;")
    filas = con.execute(
        f"""
        SELECT DISTINCT i.product_id,
               CAST(CAST(o.order_purchase_timestamp AS DATE) AS VARCHAR)
        FROM delta_scan('{items}') AS i
        JOIN delta_scan('{orders}') AS o ON i.order_id = o.order_id
        WHERE i.product_id IS NOT NULL
          AND o.order_purchase_timestamp IS NOT NULL
        """
    ).fetchall()
    pares = [(r[0], r[1]) for r in filas]
    if not pares:
        raise SystemExit("Silver no tiene pares producto-fecha.")
    if len(pares) <= n:
        return pares
    return random.Random(15).sample(pares, n)


def generar_y_publicar(n: int) -> int:
    eventos = [evento_de(pid, fecha) for pid, fecha in pares_reales(n)]
    producir(
        [json.dumps(e, ensure_ascii=False) for e in eventos],
        topic=TOPIC_CLICKSTREAM,
    )
    return len(eventos)


def recuento_gold() -> int:
    if not GOLD_DB.is_file():
        return 0
    con = duckdb.connect(str(GOLD_DB), read_only=True)
    return con.execute("SELECT COUNT(*) FROM obt_embudo_web").fetchone()[0]


def main() -> int:
    if puerto_8080_abierto():
        print(
            "R-08: hay un proceso en 127.0.0.1:8080 (7B). Páralo antes de Spark/Kafka.",
            file=sys.stderr,
        )
        return 1
    if not puerto_abierto(9092):
        print(
            f"Kafka no escucha en {BOOTSTRAP}. Arráncalo con:\n"
            "  uv run tfm-nlsql-kafka",
            file=sys.stderr,
        )
        return 1
    if not (raiz_kafka() / "bin" / "kafka-console-producer.sh").is_file():
        print("Falta la distro local de Kafka. Ejecuta `uv run tfm-nlsql-kafka`.")
        return 1
    n = int(os.environ.get("TFM_N_CLICKSTREAM", "3000"))
    publicados = generar_y_publicar(n)
    print(f"Publicados {publicados} eventos simulados (R-05) en Kafka.", flush=True)
    drenar_clickstream()
    rc = construir_gold()
    if rc != 0:
        return rc
    filas = recuento_gold()
    print(f"Gold: {filas} filas en obt_embudo_web.")
    if filas == 0:
        print("FALLO: obt_embudo_web quedó vacía.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
