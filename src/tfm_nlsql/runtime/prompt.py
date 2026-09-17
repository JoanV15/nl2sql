"""Montaje del prompt: ChatML, contrato en sistema, pregunta al final (D-33, D-47)."""

from __future__ import annotations

from tfm_nlsql.runtime.contrato import cargar_contrato

_IM_START = "<|im_start|>"
_IM_END = "<|im_end|>"


def prefijo_invariante() -> str:
    """Cabeza idéntica byte a byte entre consultas: sistema + arranque de usuario."""
    contrato, _, _ = cargar_contrato()
    return f"{_IM_START}system\n{contrato}{_IM_END}\n{_IM_START}user\n"


def construir_prompt(
    pregunta: str, sql_rechazado: str | None = None, error: str | None = None
) -> str:
    cola = f"Pregunta: {pregunta.strip()}\n"
    if sql_rechazado is not None and error is not None:
        cola += (
            f"SQL anterior rechazado:\n{sql_rechazado}\n"
            f"Error: {error}\n"
            "Devuelve únicamente la consulta SQL corregida.\n"
        )
    return prefijo_invariante() + cola + f"{_IM_END}\n{_IM_START}assistant\n"
