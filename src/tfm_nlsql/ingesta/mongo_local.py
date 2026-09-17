"""MongoDB local, cache acotada (D-32, R-08). Sin Docker: WSL no lo tiene."""

from __future__ import annotations

import os
import socket
import sys
import tarfile
import urllib.request
from pathlib import Path

from tfm_nlsql.plataforma.bronze import puerto_8080_abierto
from tfm_nlsql.rutas import RAIZ

MONGO_VERSION = "7.0.14"
MONGO_DIST = f"mongodb-linux-x86_64-ubuntu2204-{MONGO_VERSION}"
MONGO_URL = f"https://fastdl.mongodb.org/linux/{MONGO_DIST}.tgz"
HOST = "127.0.0.1"
PUERTO = 27017
URI = os.environ.get("TFM_MONGO_URI", f"mongodb://{HOST}:{PUERTO}")
CACHE = Path.home() / ".cache" / "tfm-nlsql"
COMO_LEVANTAR = (
    "Mongo no escucha en 127.0.0.1:27017. PARA.\n"
    "Levántalo con:\n"
    "  uv run tfm-nlsql-mongo\n"
    "Si tienes Docker Desktop:\n"
    "  docker run --rm -d -p 127.0.0.1:27017:27017 --name tfm-mongo mongo:7"
)


def puerto_mongo() -> bool:
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex((HOST, PUERTO)) == 0


def raiz_mongo() -> Path:
    return CACHE / MONGO_DIST


def _descargar() -> Path:
    dest = raiz_mongo()
    binario = dest / "bin" / "mongod"
    if binario.is_file():
        return dest
    CACHE.mkdir(parents=True, exist_ok=True)
    tgz = CACHE / f"{MONGO_DIST}.tgz"
    if not tgz.is_file():
        print(f"Descargando {MONGO_URL}")
        req = urllib.request.Request(MONGO_URL, headers={"User-Agent": "tfm-nlsql/0.1"})
        with urllib.request.urlopen(req, timeout=120) as resp, tgz.open("wb") as out:
            out.write(resp.read())
    with tarfile.open(tgz, "r:gz") as tar:
        tar.extractall(CACHE, filter="data")
    if not binario.is_file():
        raise SystemExit(f"No está {binario} tras extraer {tgz}")
    return dest


def _rutas_datos() -> tuple[Path, Path]:
    base = RAIZ / "datos" / "mongo"
    dbpath = base / "db"
    log = base / "mongod.log"
    dbpath.mkdir(parents=True, exist_ok=True)
    return dbpath, log


def main() -> int:
    if puerto_8080_abierto():
        print(
            "R-08: hay un proceso en 127.0.0.1:8080 (7B). Páralo antes de Mongo.",
            file=sys.stderr,
        )
        return 1
    if puerto_mongo():
        print(f"Mongo ya escucha en {URI}")
        return 0
    dest = _descargar()
    mongod = dest / "bin" / "mongod"
    dbpath, log = _rutas_datos()
    print(
        f"Mongo {MONGO_VERSION} (cache 256m) en {URI}. Ctrl-C para parar.",
        flush=True,
    )
    os.execve(
        str(mongod),
        [
            str(mongod),
            "--dbpath",
            str(dbpath),
            "--bind_ip",
            HOST,
            "--port",
            str(PUERTO),
            "--wiredTigerCacheSizeGB",
            "0.25",
            "--logpath",
            str(log),
            "--logappend",
        ],
        os.environ.copy(),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
