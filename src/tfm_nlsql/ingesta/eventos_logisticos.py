"""Eventos logísticos simulados sobre id_pedido reales (D-09, R-05).

tipo_incidencia: NULL, extraviado o dañado (comentario del contrato, no se toca
el [PREFIJO]). id_transportista con prefijo sim_.
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
    producir,
    puerto_abierto,
    raiz_kafka,
)
from tfm_nlsql.plataforma.bronze import puerto_8080_abierto
from tfm_nlsql.plataforma.drenar_kafka import drenar
from tfm_nlsql.rutas import GOLD_DB, SILVER

TRANSPORTISTAS = ("sim_correios", "sim_jadlog", "sim_loggi")
INCIDENCIAS = ("extraviado", "dañado")


def evento_de(order_id: str) -> dict:
    h = int(hashlib.md5(order_id.encode(), usedforsecurity=False).hexdigest(), 16)
    tipo = INCIDENCIAS[h % 2] if h % 20 < 2 else None
    return {
        "order_id": order_id,
        "id_transportista": TRANSPORTISTAS[h % len(TRANSPORTISTAS)],
        "tipo_incidencia": tipo,
        "es_simulado": True,
    }


def ids_reales(n: int) -> list[str]:
    ruta = SILVER / "olist_orders_dataset"
    if not ruta.is_dir():
        raise SystemExit(f"Falta Silver en {ruta}. Ejecuta tfm-nlsql-silver.")
    con = duckdb.connect(":memory:")
    con.execute("INSTALL delta; LOAD delta;")
    filas = con.execute(
        f"SELECT order_id FROM delta_scan('{ruta}') WHERE order_id IS NOT NULL"
    ).fetchall()
    ids = [r[0] for r in filas]
    if not ids:
        raise SystemExit("Silver de pedidos está vacío.")
    if len(ids) <= n:
        return ids
    return random.Random(15).sample(ids, n)


def generar_y_publicar(n: int) -> int:
    eventos = [evento_de(oid) for oid in ids_reales(n)]
    producir([json.dumps(e, ensure_ascii=False) for e in eventos])
    return len(eventos)


def recuento_gold() -> tuple[int, int]:
    if not GOLD_DB.is_file():
        return 0, 0
    con = duckdb.connect(str(GOLD_DB), read_only=True)
    trans = con.execute(
        "SELECT COUNT(*) FROM obt_pedidos WHERE id_transportista IS NOT NULL"
    ).fetchone()[0]
    inc = con.execute(
        "SELECT COUNT(*) FROM obt_pedidos WHERE tipo_incidencia IS NOT NULL"
    ).fetchone()[0]
    return trans, inc


def main() -> int:
    if puerto_8080_abierto():
        print(
            "R-08: hay un proceso en 127.0.0.1:8080 (7B). "
            "Páralo antes de Spark/Kafka.",
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
    n = int(os.environ.get("TFM_N_EVENTOS", "3000"))
    publicados = generar_y_publicar(n)
    print(f"Publicados {publicados} eventos simulados (R-05) en Kafka.", flush=True)
    drenar()
    rc = construir_gold()
    if rc != 0:
        return rc
    trans, inc = recuento_gold()
    print(f"Gold: {trans} pedidos con transportista, {inc} con incidencia.")
    if trans == 0 or inc == 0:
        print("FALLO: la muestra no rellenó id_transportista y tipo_incidencia.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
