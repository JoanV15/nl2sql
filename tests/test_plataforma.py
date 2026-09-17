"""Dagster (D-03): skip explícito si Mongo no está; grafo sin Spark."""

from __future__ import annotations

import pytest

from tfm_nlsql.plataforma.activos import SKIP_MONGO, ejecutar_resenas


def test_resenas_skip_si_mongo_cerrado(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("tfm_nlsql.ingesta.mongo_local.puerto_mongo", lambda: False)
    assert ejecutar_resenas() is None
    assert SKIP_MONGO in capsys.readouterr().out


def test_grafo_lakehouse() -> None:
    pytest.importorskip("dagster")
    from tfm_nlsql.plataforma.defs import bronze, gold, resenas_mongo, silver

    def nombres(asset) -> set[str]:
        return {k.path[-1] for k in asset.asset_deps[asset.key]}

    assert nombres(bronze) == set()
    assert nombres(silver) == {"bronze"}
    assert nombres(resenas_mongo) == {"silver"}
    assert nombres(gold) == {"resenas_mongo"}
