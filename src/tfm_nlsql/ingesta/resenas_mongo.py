"""Reseñas Olist en Mongo y Silver por consulta (D-32). No hay plan B CSV."""

from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path

import duckdb

from tfm_nlsql.ingesta.construir_gold import main as construir_gold
from tfm_nlsql.ingesta.esquemas import ESQUEMAS
from tfm_nlsql.ingesta.mongo_local import COMO_LEVANTAR, URI, puerto_mongo
from tfm_nlsql.plataforma.bronze import fecha_ingesta, puerto_8080_abierto, sesion_spark
from tfm_nlsql.rutas import BRONZE, GOLD_DB, LANDING, SILVER

CSV_RESENAS = "olist_order_reviews_dataset.csv"
CAMPOS = ESQUEMAS[CSV_RESENAS]
TABLA = Path(CSV_RESENAS).stem
MARCA = "_from_mongo"
DB = "tfm"
COLECCION = "resenas"
LOTE = 2000
PEDIDO_D38 = "c88b1d1b157a9999ce368f218a407141"


def exigir_mongo() -> None:
    if not puerto_mongo():
        raise SystemExit(COMO_LEVANTAR)


def ruta_marca(silver: Path = SILVER) -> Path:
    return silver / TABLA / MARCA


def cliente():
    from pymongo import MongoClient

    c = MongoClient(URI, serverSelectionTimeoutMS=2000)
    c.admin.command("ping")
    return c


def documentos_de_csv(ruta: Path) -> list[dict]:
    with ruta.open(encoding="utf-8-sig", newline="") as fh:
        lector = csv.DictReader(fh)
        if lector.fieldnames is None or [c.strip() for c in lector.fieldnames] != list(
            CAMPOS
        ):
            raise SystemExit(f"Cabecera inesperada en {ruta}")
        return [{k: (fila.get(k) or None) for k in CAMPOS} for fila in lector]


def cargar_origen(docs: list[dict]) -> int:
    col = cliente()[DB][COLECCION]
    col.drop()
    if docs:
        for i in range(0, len(docs), LOTE):
            col.insert_many(docs[i : i + LOTE], ordered=False)
    return col.count_documents({})


def consultar() -> list[dict]:
    col = cliente()[DB][COLECCION]
    proy = {c: 1 for c in CAMPOS}
    proy["_id"] = 0
    return [{k: d.get(k) for k in CAMPOS} for d in col.find({}, proy)]


def promover_silver_desde_consulta(spark, docs: list[dict]) -> int:
    if not docs:
        raise SystemExit("La consulta a Mongo devolvió 0 reseñas. PARA.")
    landing = LANDING / "resenas_mongo"
    if landing.exists():
        shutil.rmtree(landing)
    landing.mkdir(parents=True)
    part = landing / "part.json"
    with part.open("w", encoding="utf-8") as fh:
        for d in docs:
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")
    fecha = fecha_ingesta()
    dest_br = BRONZE / "resenas_mongo" / f"fecha_ingesta={fecha}"
    if dest_br.exists():
        shutil.rmtree(dest_br)
    dest_br.mkdir(parents=True)
    shutil.copy2(part, dest_br / part.name)
    df = spark.read.json(str(BRONZE / "resenas_mongo"))
    dest_ag = SILVER / TABLA
    (
        df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .save(str(dest_ag))
    )
    n = spark.read.format("delta").load(str(dest_ag)).count()
    (dest_ag / MARCA).write_text("D-32\n", encoding="utf-8")
    print(f"  SILVER {TABLA} (Mongo): {n}")
    return n


def _multi_y_media(docs: list[dict], order_id: str) -> tuple[int, float | None]:
    scores: dict[str, list[float]] = {}
    for d in docs:
        oid = d.get("order_id")
        if not oid or d.get("review_score") is None:
            continue
        scores.setdefault(oid, []).append(float(d["review_score"]))
    n_multi = sum(1 for v in scores.values() if len(v) > 1)
    vals = scores.get(order_id)
    media = sum(vals) / len(vals) if vals else None
    return n_multi, media


def recuentos_gold() -> tuple[int, int, float | None]:
    if not GOLD_DB.is_file():
        return 0, 0, None
    con = duckdb.connect(str(GOLD_DB), read_only=True)
    con_nota = con.execute(
        "SELECT COUNT(*) FROM obt_pedidos WHERE nota_resena IS NOT NULL"
    ).fetchone()[0]
    fracc = con.execute(
        """
        SELECT COUNT(*) FROM obt_pedidos
        WHERE nota_resena IS NOT NULL
          AND nota_resena != CAST(nota_resena AS INTEGER)
        """
    ).fetchone()[0]
    muestra = con.execute(
        "SELECT nota_resena FROM obt_pedidos WHERE id_pedido = ?",
        [PEDIDO_D38],
    ).fetchone()
    return con_nota, fracc, None if muestra is None else muestra[0]


def ingerir_a_silver() -> int:
    """CSV Landing → Mongo → consulta → Silver. No construye Gold."""
    if puerto_8080_abierto():
        print(
            "R-08: hay un proceso en 127.0.0.1:8080 (7B). Páralo antes de Spark/Mongo.",
            file=sys.stderr,
        )
        return 1
    exigir_mongo()
    src = LANDING / CSV_RESENAS
    if not src.is_file():
        print(f"Falta {src}. Ejecuta tfm-nlsql-aterrizar. PARA.", file=sys.stderr)
        return 1
    docs_csv = documentos_de_csv(src)
    n_carga = cargar_origen(docs_csv)
    print(f"Mongo {DB}.{COLECCION}: {n_carga} documentos (origen simulado).")
    docs = consultar()
    n_multi, _media = _multi_y_media(docs, PEDIDO_D38)
    if n_multi == 0:
        print(
            "PARA: el grano de reseña se perdió al cargar Mongo (D-38).",
            file=sys.stderr,
        )
        return 1
    spark = sesion_spark()
    try:
        n_silver = promover_silver_desde_consulta(spark, docs)
    finally:
        spark.stop()
    if n_silver != len(docs):
        print(f"FALLO: Silver {n_silver} ≠ consulta {len(docs)}.", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    rc = ingerir_a_silver()
    if rc != 0:
        return rc
    docs = consultar()
    _n_multi, media_mongo = _multi_y_media(docs, PEDIDO_D38)
    rc = construir_gold()
    if rc != 0:
        return rc
    con_nota, fracc, media_gold = recuentos_gold()
    print(f"Gold: {con_nota} pedidos con nota_resena; {fracc} medias no enteras.")
    if con_nota == 0:
        print("FALLO: el recuento de reseñas en Gold se desplomó a 0.")
        return 1
    if fracc == 0:
        print("PARA: nota_resena ya no es media (D-38). El grano se rompió.")
        return 1
    if media_mongo is None or media_gold is None:
        print(f"PARA: falta el pedido {PEDIDO_D38} para comprobar D-38.")
        return 1
    if abs(float(media_gold) - media_mongo) > 1e-6:
        print(
            f"PARA: D-38 roto en {PEDIDO_D38}: Gold {media_gold} ≠ Mongo {media_mongo}."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
