"""Pasos del lakehouse. Dagster los envuelve (D-03); no reescriben Spark."""

from __future__ import annotations

SKIP_MONGO = "SKIP: Mongo no escucha en 127.0.0.1:27017"


def ejecutar_bronze() -> int:
    from tfm_nlsql.plataforma.bronze import main

    return main()


def ejecutar_silver() -> int:
    from tfm_nlsql.plataforma.silver import main

    return main()


def ejecutar_resenas() -> int | None:
    """None = skip explícito. No cae al CSV."""
    from tfm_nlsql.ingesta.mongo_local import puerto_mongo

    if not puerto_mongo():
        print(SKIP_MONGO)
        return None
    from tfm_nlsql.ingesta.resenas_mongo import ingerir_a_silver

    return ingerir_a_silver()


def ejecutar_gold() -> int:
    from tfm_nlsql.ingesta.construir_gold import main

    return main()
