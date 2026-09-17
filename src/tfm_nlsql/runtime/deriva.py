"""Deriva D-25: columnas Gold vs catalogo_columnas() del prefijo. No interpola."""

from __future__ import annotations

import re

TABLAS_GOLD = (
    "obt_pedidos",
    "obt_lineas_pedido",
    "obt_vendedores",
    "obt_embudo_web",
)

_CREATE = re.compile(
    r"CREATE TABLE (\w+)\s*\((.*?)\);",
    re.DOTALL | re.IGNORECASE,
)


class DerivaContrato(AssertionError):
    """El catálogo del prefijo y Gold no coinciden."""


def columnas_gold(ruta_db) -> dict[str, frozenset[str]]:
    import duckdb

    con = duckdb.connect(str(ruta_db), read_only=True)
    try:
        cat: dict[str, frozenset[str]] = {}
        for t in TABLAS_GOLD:
            filas = con.execute(f"DESCRIBE {t}").fetchall()
            cat[t] = frozenset(str(r[0]) for r in filas)
        return cat
    finally:
        con.close()


def quitar_columna_prefijo(prefijo: str, tabla: str, columna: str) -> str:
    def _reemplazar(m: re.Match[str]) -> str:
        if m.group(1) != tabla:
            return m.group(0)
        lineas = []
        for ln in m.group(2).splitlines():
            nucleo = ln.split("--", 1)[0].strip().rstrip(",")
            if nucleo.split()[:1] == [columna]:
                continue
            lineas.append(ln)
        cuerpo = "\n".join(lineas)
        return f"CREATE TABLE {tabla} (\n{cuerpo}\n);"

    nuevo, n = _CREATE.subn(_reemplazar, prefijo)
    if n == 0:
        raise ValueError(tabla)
    return nuevo


def comprobar_deriva(
    cat_contrato: dict[str, frozenset[str]],
    cat_gold: dict[str, frozenset[str]],
) -> None:
    faltan = []
    for t in TABLAS_GOLD:
        a = cat_contrato.get(t, frozenset())
        b = cat_gold.get(t, frozenset())
        if a != b:
            faltan.append(
                f"{t}: contrato-gold={sorted(a - b)} gold-contrato={sorted(b - a)}"
            )
    extra = sorted(set(cat_contrato) - set(TABLAS_GOLD))
    if extra:
        faltan.append(f"tablas de más en contrato: {extra}")
    if faltan:
        raise DerivaContrato("; ".join(faltan))
