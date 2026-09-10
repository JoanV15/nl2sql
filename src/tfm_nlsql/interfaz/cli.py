"""Interfaz de línea de comandos."""

from __future__ import annotations

import argparse
import sys

from tfm_nlsql.runtime.ejecutor import formatear
from tfm_nlsql.runtime.orquestador import consultar

FECHA_REFERENCIA = "2018-10-17"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Pregunta en castellano → SQL validado sobre Gold."
    )
    parser.add_argument("pregunta", help="Pregunta de negocio en castellano")
    parser.add_argument(
        "--sin-calentar",
        action="store_true",
        help="No precalentar la caché de prefijo (D-34)",
    )
    args = parser.parse_args(argv)

    print(f"Fecha de referencia: {FECHA_REFERENCIA}", flush=True)
    try:
        r = consultar(args.pregunta, calentar_cache=not args.sin_calentar)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    if r.abstencion:
        print(r.abstencion)
        return 0
    if r.error and r.sql is None:
        print(f"Rechazado: {r.error}")
        if r.sql:
            print("\nSQL:\n", r.sql)
        return 1
    print("\nSQL:")
    print(r.sql)
    print("\nResultado:")
    print(formatear(r.columnas, r.filas))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
