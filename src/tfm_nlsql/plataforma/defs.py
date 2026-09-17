"""Assets Dagster del lakehouse (D-03).

Comando: uv run --extra spark --extra dagster --extra mongo tfm-nlsql-plataforma
"""

from __future__ import annotations

import sys

from dagster import Definitions, Failure, asset, define_asset_job, materialize

from tfm_nlsql.plataforma.activos import (
    ejecutar_bronze,
    ejecutar_gold,
    ejecutar_resenas,
    ejecutar_silver,
)
from tfm_nlsql.plataforma.bronze import puerto_8080_abierto


def _exigir(rc: int | None, nombre: str) -> None:
    if rc:
        raise Failure(f"{nombre} falló ({rc})")


@asset(group_name="lakehouse")
def bronze() -> None:
    try:
        _exigir(ejecutar_bronze(), "bronze")
    except SystemExit as e:
        raise Failure(f"bronze: {e}") from e


@asset(group_name="lakehouse", deps=["bronze"])
def silver() -> None:
    try:
        _exigir(ejecutar_silver(), "silver")
    except SystemExit as e:
        raise Failure(f"silver: {e}") from e


@asset(group_name="lakehouse", deps=["silver"])
def resenas_mongo() -> None:
    try:
        rc = ejecutar_resenas()
    except SystemExit as e:
        raise Failure(f"resenas_mongo: {e}") from e
    if rc is None:
        return
    _exigir(rc, "resenas_mongo")


@asset(group_name="lakehouse", deps=["resenas_mongo"])
def gold() -> None:
    try:
        _exigir(ejecutar_gold(), "gold")
    except SystemExit as e:
        raise Failure(f"gold: {e}") from e


lakehouse = define_asset_job(
    "lakehouse",
    selection=[bronze, silver, resenas_mongo, gold],
)

defs = Definitions(
    assets=[bronze, silver, resenas_mongo, gold],
    jobs=[lakehouse],
)


def main() -> int:
    from tfm_nlsql.plataforma.adls import exigir_adls

    exigir_adls()
    if puerto_8080_abierto():
        print(
            "R-08: hay un proceso en 127.0.0.1:8080 (7B). "
            "Páralo antes de la plataforma.",
            file=sys.stderr,
        )
        return 1
    print(
        "tfm-nlsql-plataforma: bronze → silver → resenas_mongo → gold",
        flush=True,
    )
    resultado = materialize([bronze, silver, resenas_mongo, gold])
    return 0 if resultado.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
