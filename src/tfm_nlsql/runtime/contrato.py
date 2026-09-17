"""Prefijo invariante del contrato semántico (D-33, D-37)."""

from __future__ import annotations

import re
from functools import cache
from pathlib import Path

from tfm_nlsql.rutas import CONTRATO

_MARCA = "[PREFIJO]"
_NOTAS = re.compile(
    r"\*\*Notas de diseño\*\*.*?(?=\n### |\Z)",
    re.DOTALL,
)
_SQL = re.compile(r"```sql\n(.*?)```", re.DOTALL)
_CREATE = re.compile(
    r"CREATE TABLE (\w+)\s*\((.*?)\);",
    re.DOTALL | re.IGNORECASE,
)


def extraer_prefijo(markdown: str) -> str:
    """Concatena, en orden, el contenido que viaja al modelo."""
    bloques: list[str] = []
    for parte in markdown.split("\n## "):
        primera, _, resto = parte.partition("\n")
        if _MARCA not in primera:
            continue
        viajero = _contenido_viajero(resto)
        if viajero:
            bloques.append(viajero)
    return "\n\n".join(bloques).strip() + "\n"


def _contenido_viajero(cuerpo: str) -> str:
    sin_notas = _NOTAS.sub("", cuerpo)
    sqls = [s.strip() for s in _SQL.findall(sin_notas)]
    citas: list[str] = []
    for linea in sin_notas.splitlines():
        if linea.startswith("> "):
            citas.append(linea[2:])
        elif linea.strip() == ">":
            citas.append("")
    partes: list[str] = []
    if sqls:
        partes.append("\n\n".join(sqls))
    texto_citas = "\n".join(citas).strip()
    if texto_citas:
        partes.append(texto_citas)
    return "\n\n".join(partes)


def catalogo_columnas(prefijo: str) -> dict[str, frozenset[str]]:
    cat: dict[str, frozenset[str]] = {}
    for tabla, cuerpo in _CREATE.findall(prefijo):
        cols: list[str] = []
        for linea in cuerpo.splitlines():
            linea = linea.split("--", 1)[0].strip().rstrip(",")
            if not linea:
                continue
            cols.append(linea.split()[0])
        cat[tabla] = frozenset(cols)
    return cat


def version_contrato(markdown: str) -> str:
    m = re.search(r"\*\*Versión:\*\*\s*([0-9.]+)", markdown)
    return m.group(1) if m else "desconocida"


@cache
def cargar_contrato(
    ruta: Path | None = None,
) -> tuple[str, dict[str, frozenset[str]], str]:
    texto = (ruta or CONTRATO).read_text(encoding="utf-8")
    prefijo = extraer_prefijo(texto)
    return prefijo, catalogo_columnas(prefijo), version_contrato(texto)
