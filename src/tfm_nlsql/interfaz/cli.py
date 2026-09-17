"""Interfaz de línea de comandos."""

from __future__ import annotations

import argparse
import sys

from tfm_nlsql.runtime.ejecutor import formatear
from tfm_nlsql.runtime.orquestador import consultar

FECHA_REFERENCIA = "2018-10-17"

# El motivo técnico se reinyecta al modelo (D-20) y se persiste en la traza
# (D-22); aquí solo se traduce para la persona que mira la pantalla.
_MOTIVOS = (
    ("sql no analizable", "El modelo no devolvió una consulta SQL analizable."),
    ("el modelo no devolvió sql", "El modelo no devolvió ninguna consulta."),
    ("solo se permiten select", "Solo se admiten consultas de lectura: SELECT y WITH."),
    ("solo se admite una sentencia", "La respuesta traía varias sentencias SQL."),
    (
        "función de tabla no permitida",
        "La consulta intentaba leer ficheros fuera de la capa Gold.",
    ),
    ("tabla no permitida", "La consulta usa una tabla que no está en la capa Gold."),
    (
        "columna no permitida",
        "La consulta usa una columna que no existe en el contrato semántico.",
    ),
    (
        "producto cartesiano",
        "La consulta cruza dos tablas sin condición de enlace: el resultado "
        "sería un producto cartesiano.",
    ),
    ("binding", "DuckDB no reconoce alguna tabla o columna de la consulta."),
    (
        "no existe gold",
        "No se encuentra la capa Gold. Reconstrúyela con «uv run tfm-nlsql-gold».",
    ),
    (
        "llama-server no responde",
        "El modelo no responde. Levanta llama-server en 127.0.0.1:8080.",
    ),
    ("consulta superó", "La consulta tardó demasiado y se canceló."),
)


def mensaje_error(error: str) -> str:
    """Traduce el motivo técnico del validador a una frase legible."""
    texto = (error or "").strip()
    for clave, frase in _MOTIVOS:
        if clave in texto.lower():
            # Solo se cita el detalle si es un identificador: los volcados de
            # sqlglot y de DuckDB llevan espacios y no dicen nada al usuario.
            detalle = texto.rsplit(": ", 1)[1].strip() if ": " in texto else ""
            cita = detalle if len(detalle.split()) == 1 else ""
            return f"{frase} ({cita})" if 0 < len(cita) <= 60 else frase
    return texto.splitlines()[0] if texto else "Error desconocido."


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
        print(f"Error: {mensaje_error(str(e))}", file=sys.stderr)
        return 2

    if r.abstencion:
        print(r.abstencion)
        return 0
    if r.error and r.sql is None:
        print(f"Rechazado: {mensaje_error(r.error)}")
        print(f"Motivo técnico: {r.error.splitlines()[0]}", file=sys.stderr)
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
