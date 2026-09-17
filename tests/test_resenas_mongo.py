"""Reseñas por Mongo (D-32): PARA si no hay servicio; skip si no corre."""

from __future__ import annotations

from pathlib import Path

import pytest

from tfm_nlsql.ingesta.construir_gold import _comprobar_resenas_mongo
from tfm_nlsql.ingesta.mongo_local import COMO_LEVANTAR, puerto_mongo
from tfm_nlsql.ingesta.resenas_mongo import (
    CAMPOS,
    _multi_y_media,
    documentos_de_csv,
    exigir_mongo,
)


def test_d38_media_de_dos_resenas() -> None:
    docs = [
        {"order_id": "a", "review_score": "1"},
        {"order_id": "a", "review_score": "5"},
        {"order_id": "b", "review_score": "4"},
    ]
    n_multi, media = _multi_y_media(docs, "a")
    assert n_multi == 1
    assert media == 3.0


def test_exigir_mongo_para_si_no_escucha(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("tfm_nlsql.ingesta.resenas_mongo.puerto_mongo", lambda: False)
    with pytest.raises(SystemExit, match="PARA"):
        exigir_mongo()
    assert "tfm-nlsql-mongo" in COMO_LEVANTAR


def test_gold_exige_marca_mongo(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="Mongo"):
        _comprobar_resenas_mongo(tmp_path / "silver")


def test_camino_mongo_consulta() -> None:
    if not puerto_mongo():
        pytest.skip("Mongo no corre")
    pymongo = pytest.importorskip("pymongo")
    from tfm_nlsql.ingesta.mongo_local import URI
    from tfm_nlsql.ingesta.resenas_mongo import COLECCION, DB

    col = pymongo.MongoClient(URI, serverSelectionTimeoutMS=2000)[DB][
        f"{COLECCION}_test"
    ]
    col.drop()
    col.insert_many(
        [
            {k: None for k in CAMPOS}
            | {"review_id": "r1", "order_id": "o1", "review_score": "1"},
            {k: None for k in CAMPOS}
            | {"review_id": "r2", "order_id": "o1", "review_score": "5"},
        ]
    )
    docs = list(col.find({}, {c: 1 for c in CAMPOS} | {"_id": 0}))
    n_multi, media = _multi_y_media(docs, "o1")
    col.drop()
    assert n_multi == 1
    assert media == 3.0


def test_documentos_csv_conservan_ids(tmp_path: Path) -> None:
    csv = tmp_path / "r.csv"
    csv.write_text(
        ",".join(CAMPOS) + "\nr1,o1,4,t,m,2018-01-01,2018-01-02\n",
        encoding="utf-8",
    )
    docs = documentos_de_csv(csv)
    assert docs[0]["review_id"] == "r1"
    assert docs[0]["order_id"] == "o1"
    assert docs[0]["review_score"] == "4"
