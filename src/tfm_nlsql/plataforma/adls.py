"""Backend ADLS Gen2 detrás de TFM_*_PATH (D-07, D-28). No inventa cuenta."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from pathlib import Path

from tfm_nlsql.rutas import es_abfs

VARS_ALMACEN = (
    "TFM_LANDING_PATH",
    "TFM_BRONZE_PATH",
    "TFM_SILVER_PATH",
    "TFM_CUARENTENA_PATH",
)
VARS_COPIA_LOCAL = (
    "TFM_LANDING_PATH",
    "TFM_BRONZE_PATH",
    "TFM_CUARENTENA_PATH",
)
_URI = re.compile(
    r"^abfss?://([^@]+)@([^.]+)\.dfs\.core\.windows\.net(/.*)?$",
    re.IGNORECASE,
)
HADOOP_AZURE = "org.apache.hadoop:hadoop-azure:3.4.2"
COMO_CREDENCIALES = (
    "ADLS sin credenciales. PARA.\n"
    "Exporta AZURE_STORAGE_ACCOUNT_KEY o AZURE_STORAGE_CONNECTION_STRING.\n"
    "La cuenta y el contenedor van en la URI abfs; no se inventan (D-07, D-28)."
)
COMO_EXTRA = (
    "ADLS requiere el extra azure. PARA.\n  uv run --extra azure --extra spark …"
)
COMO_CUENTA = (
    "URI abfs sin contenedor@cuenta.dfs.core.windows.net. PARA.\n"
    "No se inventa la cuenta. Ejemplo:\n"
    "  abfss://contenedor@CUENTA.dfs.core.windows.net/silver"
)
COMO_GOLD = "Gold es DuckDB local (D-07). TFM_GOLD_PATH no admite abfs. PARA."
COMO_COPIA = (
    "Landing/Bronze/cuarentena siguen en disco local (copia CSV). PARA.\n"
    "Pon la URI abfs solo en TFM_SILVER_PATH."
)
COMO_DUCKDB_ABFS = (
    "DuckDB no puede delta_scan abfs aquí. PARA.\n"
    "No se lee el Silver local. Gold sigue TFM_SILVER_PATH (D-07)."
)


def cuenta_de(uri: str) -> str | None:
    m = _URI.match(uri.rstrip("/"))
    return None if m is None else m.group(2)


def contenedor_de(uri: str) -> str | None:
    m = _URI.match(uri.rstrip("/"))
    return None if m is None else m.group(1)


def uri_capa(var: str, default: Path, entorno: Mapping[str, str] | None = None) -> str:
    env = os.environ if entorno is None else entorno
    crudo = env.get(var)
    if not crudo:
        return str(default)
    return crudo.rstrip("/") if es_abfs(crudo) else str(Path(crudo))


def join_capa(base: Path | str, *partes: str) -> str:
    s = str(base).rstrip("/")
    if es_abfs(s):
        return "/".join([s, *partes])
    p = Path(s)
    for x in partes:
        p /= x
    return str(p)


def _uris(entorno: Mapping[str, str]) -> list[str]:
    return [entorno[k] for k in VARS_ALMACEN if es_abfs(entorno.get(k, ""))]


def exigir_adls(entorno: Mapping[str, str] | None = None) -> None:
    env = os.environ if entorno is None else entorno
    if es_abfs(env.get("TFM_GOLD_PATH", "")):
        raise SystemExit(COMO_GOLD)
    uris = _uris(env)
    if not uris:
        return
    if any(es_abfs(env.get(k, "")) for k in VARS_COPIA_LOCAL):
        raise SystemExit(COMO_COPIA)
    for u in uris:
        if cuenta_de(u) is None or contenedor_de(u) is None:
            raise SystemExit(COMO_CUENTA)
    if not env.get("AZURE_STORAGE_ACCOUNT_KEY") and not env.get(
        "AZURE_STORAGE_CONNECTION_STRING"
    ):
        raise SystemExit(COMO_CREDENCIALES)
    try:
        import azure.storage.filedatalake  # noqa: F401
    except ImportError:
        raise SystemExit(COMO_EXTRA) from None


def exigir_duckdb_abfs(uri: str) -> None:
    """Si DuckDB no carga azure/delta para abfs, PARA. No hay plan B local."""
    import duckdb

    if not es_abfs(uri):
        return
    con = duckdb.connect(":memory:")
    try:
        try:
            con.execute("LOAD delta")
        except duckdb.Error:
            con.execute("INSTALL delta; LOAD delta;")
        try:
            con.execute("LOAD azure")
        except duckdb.Error:
            con.execute("INSTALL azure; LOAD azure;")
    except duckdb.Error as e:
        raise SystemExit(f"{COMO_DUCKDB_ABFS}\nURI: {uri}\n{e}") from e
    finally:
        con.close()


def configurar_spark_adls(builder, extra_packages: list[str] | None = None):
    uris = _uris(os.environ)
    paquetes = list(extra_packages or [])
    if not uris:
        return builder, paquetes
    exigir_adls()
    cuenta = cuenta_de(uris[0])
    clave = os.environ.get("AZURE_STORAGE_ACCOUNT_KEY")
    if cuenta and clave:
        builder = builder.config(
            f"spark.hadoop.fs.azure.account.key.{cuenta}.dfs.core.windows.net",
            clave,
        )
    if HADOOP_AZURE not in paquetes:
        paquetes.append(HADOOP_AZURE)
    return builder, paquetes
