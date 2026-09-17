"""Publica el linaje dbt en OpenMetadata (D-62). No entra en el runtime."""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from tfm_nlsql.plataforma.om_negocio import GLOSARIO, publicar_negocio
from tfm_nlsql.rutas import RAIZ

OM_UI = os.environ.get("TFM_OM_URL", "http://127.0.0.1:8585")
SERVICIO = "tfm_nlsql_gold"
RECETA = RAIZ / "docker" / "openmetadata" / "ingest" / "dbt.yaml"
DBT = RAIZ / "dbt"
# El parser de OM 1.6.5 rechaza el manifiesto dbt 1.12
# (pydantic extra_forbidden). Subida por REST; el conector oficial
# queda en docker/openmetadata/ingest/dbt.yaml por si OM sube de versión.

_TIPOS = {
    "VARCHAR": "VARCHAR",
    "INTEGER": "INT",
    "BIGINT": "BIGINT",
    "DOUBLE": "DOUBLE",
    "FLOAT": "FLOAT",
    "BOOLEAN": "BOOLEAN",
    "DATE": "DATE",
    "TIMESTAMP": "TIMESTAMP",
    "DECIMAL": "DECIMAL",
    "HUGEINT": "BIGINT",
}


def receta_con_token(token: str, origen: Path | None = None) -> str:
    ruta = origen or RECETA
    return ruta.read_text(encoding="utf-8").replace("${OM_JWT}", token)


def _peticion(metodo: str, ruta: str, token: str, cuerpo: dict | None = None) -> dict:
    data = None if cuerpo is None else json.dumps(cuerpo).encode()
    cabeceras = {"Authorization": f"Bearer {token}"}
    if cuerpo is not None:
        cabeceras["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"{OM_UI}/api{ruta}", data=data, headers=cabeceras, method=metodo
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        bruto = resp.read().decode()
        return json.loads(bruto) if bruto else {}


def _asegurar_servicio(token: str) -> None:
    """El catálogo exige un DatabaseService previo; no es el runtime (D-06)."""
    try:
        _peticion("GET", f"/v1/services/databaseServices/name/{SERVICIO}", token)
        return
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
    _peticion(
        "POST",
        "/v1/services/databaseServices",
        token,
        {
            "name": SERVICIO,
            "displayName": "Gold DuckDB (dbt)",
            "description": (
                "Capa Gold Olist. Linaje Silver->Gold via dbt. "
                "Fuera del runtime NL-to-SQL (D-06, D-62)."
            ),
            "serviceType": "CustomDatabase",
            "connection": {
                "config": {
                    "type": "CustomDatabase",
                    "sourcePythonClass": (
                        "metadata.ingestion.source.database"
                        ".common_db_source.CommonDbSourceService"
                    ),
                    "connectionOptions": {},
                }
            },
        },
    )


def _jwt() -> str:
    if os.environ.get("OM_JWT"):
        return os.environ["OM_JWT"].strip()
    clave = base64.b64encode(b"admin").decode()
    cuerpo = json.dumps(
        {"email": "admin@open-metadata.org", "password": clave}
    ).encode()
    req = urllib.request.Request(
        f"{OM_UI}/api/v1/users/login",
        data=cuerpo,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        raise SystemExit(
            "OpenMetadata no responde en "
            f"{OM_UI}. Levanta el perfil catálogo (D-62) y para el 7B (R-08)."
        ) from e
    token = data.get("accessToken") or data.get("token")
    if not token:
        raise SystemExit("Login a OpenMetadata sin token. Crea OM_JWT desde la UI.")
    return token


def _dbt_docs() -> None:
    dbt = shutil.which("dbt")
    if dbt is None:
        raise SystemExit("dbt no está en PATH; ejecuta dentro de `uv run`.")
    env = os.environ.copy()
    env.setdefault("TFM_GOLD_PATH", str(RAIZ / "datos" / "gold" / "gold.duckdb"))
    r = subprocess.run(
        [
            dbt,
            "docs",
            "generate",
            "--project-dir",
            str(DBT),
            "--profiles-dir",
            str(DBT),
        ],
        cwd=str(DBT),
        env=env,
        check=False,
    )
    if r.returncode or not (DBT / "target" / "manifest.json").exists():
        raise SystemExit("dbt docs generate falló; hace falta Gold y el manifiesto.")


def _tipo(crudo: str) -> dict:
    base = crudo.split("(", 1)[0].upper()
    om = _TIPOS.get(base, "VARCHAR")
    col: dict = {"dataType": om}
    if om == "VARCHAR":
        col["dataLength"] = 256
    return col


def _columnas(uid: str, nodo: dict, catalogo: dict) -> list[dict]:
    cat = (catalogo.get("nodes") or {}).get(uid, {})
    cols_cat = cat.get("columns") or {}
    if cols_cat:
        orden = sorted(cols_cat.values(), key=lambda c: c.get("index") or 0)
        desc_yml = {
            n: (meta.get("description") or "").strip()
            for n, meta in (nodo.get("columns") or {}).items()
        }
        salida = []
        for c in orden:
            nombre = c["name"]
            item = {"name": nombre, **_tipo(c.get("type") or "VARCHAR")}
            if desc_yml.get(nombre):
                item["description"] = desc_yml[nombre]
            salida.append(item)
        return salida
    yml = nodo.get("columns") or {}
    if yml:
        return [
            {"name": n, **_tipo("VARCHAR")}
            | ({"description": meta["description"]} if meta.get("description") else {})
            for n, meta in yml.items()
        ]
    return [
        {
            "name": "nodo",
            "dataType": "VARCHAR",
            "dataLength": 64,
            "description": "Nodo dbt de Silver; no materializado en Gold.",
        }
    ]


def _publicar(token: str) -> None:
    manifiesto = json.loads((DBT / "target" / "manifest.json").read_text())
    catalogo = json.loads((DBT / "target" / "catalog.json").read_text())
    _peticion(
        "PUT",
        "/v1/databases",
        token,
        {
            "name": "gold",
            "service": SERVICIO,
            "description": "Capa Gold DuckDB.",
        },
    )
    _peticion(
        "PUT",
        "/v1/databaseSchemas",
        token,
        {
            "name": "main",
            "database": f"{SERVICIO}.gold",
        },
    )
    ids: dict[str, str] = {}
    for uid, nodo in manifiesto.get("nodes", {}).items():
        if nodo.get("resource_type") not in {"model", "seed"}:
            continue
        nombre = nodo.get("alias") or nodo.get("name")
        cuerpo = {
            "name": nombre,
            "description": (nodo.get("description") or "").strip() or None,
            "tableType": "Regular" if uid in (catalogo.get("nodes") or {}) else "View",
            "columns": _columnas(uid, nodo, catalogo),
            "databaseSchema": f"{SERVICIO}.gold.main",
        }
        if not cuerpo["description"]:
            del cuerpo["description"]
        creado = _peticion("PUT", "/v1/tables", token, cuerpo)
        ids[uid] = creado["id"]
    for uid, padres in (manifiesto.get("parent_map") or {}).items():
        if uid not in ids:
            continue
        for padre in padres:
            if padre not in ids:
                continue
            _peticion(
                "PUT",
                "/v1/lineage",
                token,
                {
                    "edge": {
                        "fromEntity": {"id": ids[padre], "type": "table"},
                        "toEntity": {"id": ids[uid], "type": "table"},
                    }
                },
            )


def main() -> int:
    _dbt_docs()
    token = _jwt()
    _asegurar_servicio(token)
    _publicar(token)
    publicar_negocio(_peticion, token, SERVICIO)
    print(
        f"Linaje y glosario publicados. UI: {OM_UI}  "
        "(admin@open-metadata.org / admin)  "
        f"Glosario: {OM_UI}/glossary/{GLOSARIO}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
