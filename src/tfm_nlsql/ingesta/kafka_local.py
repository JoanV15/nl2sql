"""Kafka KRaft de un solo broker, heap acotado (D-09, R-08)."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

from tfm_nlsql.plataforma.bronze import puerto_8080_abierto
from tfm_nlsql.rutas import RAIZ

KAFKA_VERSION = "3.9.1"
KAFKA_DIST = f"kafka_2.13-{KAFKA_VERSION}"
KAFKA_URL = (
    f"https://archive.apache.org/dist/kafka/{KAFKA_VERSION}/{KAFKA_DIST}.tgz"
)
BOOTSTRAP = "127.0.0.1:9092"
TOPIC = "eventos_logisticos"
TOPIC_CLICKSTREAM = "eventos_clickstream"
CACHE = Path.home() / ".cache" / "tfm-nlsql"


def puerto_abierto(puerto: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", puerto)) == 0


def raiz_kafka() -> Path:
    return CACHE / KAFKA_DIST


def _descargar() -> Path:
    dest = raiz_kafka()
    if (dest / "bin" / "kafka-server-start.sh").is_file():
        return dest
    CACHE.mkdir(parents=True, exist_ok=True)
    tgz = CACHE / f"{KAFKA_DIST}.tgz"
    if not tgz.is_file():
        print(f"Descargando {KAFKA_URL}")
        urllib.request.urlretrieve(KAFKA_URL, tgz)
    with tarfile.open(tgz, "r:gz") as tar:
        tar.extractall(CACHE, filter="data")
    return dest


def _server_properties() -> Path:
    logs = RAIZ / "datos" / "kafka-logs"
    logs.mkdir(parents=True, exist_ok=True)
    props = logs / "server.properties"
    props.write_text(
        "\n".join(
            [
                "process.roles=broker,controller",
                "node.id=1",
                "controller.quorum.voters=1@127.0.0.1:9093",
                "listeners=PLAINTEXT://127.0.0.1:9092,CONTROLLER://127.0.0.1:9093",
                "advertised.listeners=PLAINTEXT://127.0.0.1:9092",
                "inter.broker.listener.name=PLAINTEXT",
                "controller.listener.names=CONTROLLER",
                "listener.security.protocol.map=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT",
                f"log.dirs={logs / 'kraft'}",
                "num.network.threads=2",
                "num.io.threads=2",
                "num.partitions=1",
                "offsets.topic.replication.factor=1",
                "transaction.state.log.replication.factor=1",
                "transaction.state.log.min.isr=1",
                "log.retention.hours=24",
                "group.initial.rebalance.delay.ms=0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return props


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env["KAFKA_HEAP_OPTS"] = os.environ.get("KAFKA_HEAP_OPTS", "-Xmx256m -Xms256m")
    env["LOG_DIR"] = str(RAIZ / "datos" / "kafka-logs" / "app")
    Path(env["LOG_DIR"]).mkdir(parents=True, exist_ok=True)
    return env


def asegurar_cluster() -> Path:
    dest = _descargar()
    props = _server_properties()
    kraft = RAIZ / "datos" / "kafka-logs" / "kraft"
    if not (kraft / "meta.properties").is_file():
        uuid = subprocess.check_output(
            [str(dest / "bin" / "kafka-storage.sh"), "random-uuid"],
            env=_env(),
            text=True,
        ).strip()
        subprocess.check_call(
            [
                str(dest / "bin" / "kafka-storage.sh"),
                "format",
                "-t",
                uuid,
                "-c",
                str(props),
            ],
            env=_env(),
        )
    return dest


def crear_topic(dest: Path, topic: str = TOPIC) -> None:
    subprocess.check_call(
        [
            str(dest / "bin" / "kafka-topics.sh"),
            "--bootstrap-server",
            BOOTSTRAP,
            "--create",
            "--if-not-exists",
            "--topic",
            topic,
            "--partitions",
            "1",
            "--replication-factor",
            "1",
        ],
        env=_env(),
    )


def producir(lineas: list[str], topic: str = TOPIC) -> None:
    dest = raiz_kafka()
    crear_topic(dest, topic)
    proc = subprocess.run(
        [
            str(dest / "bin" / "kafka-console-producer.sh"),
            "--bootstrap-server",
            BOOTSTRAP,
            "--topic",
            topic,
        ],
        input="\n".join(lineas) + "\n",
        text=True,
        env=_env(),
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit("kafka-console-producer falló")


def main() -> int:
    if puerto_8080_abierto():
        print(
            "R-08: hay un proceso en 127.0.0.1:8080 (7B). "
            "Páralo antes de Kafka.",
            file=sys.stderr,
        )
        return 1
    if puerto_abierto(9092):
        print(f"Kafka ya escucha en {BOOTSTRAP}")
        return 0
    dest = asegurar_cluster()
    props = _server_properties()
    print(f"Kafka KRaft (256m) en {BOOTSTRAP}. Ctrl-C para parar.", flush=True)
    os.execve(
        str(dest / "bin" / "kafka-server-start.sh"),
        [str(dest / "bin" / "kafka-server-start.sh"), str(props)],
        _env(),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
