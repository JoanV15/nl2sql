"""Orquesta generación, validación, un reintento y ejecución (D-19, D-20, D-35)."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from tfm_nlsql.runtime.cliente import RespuestaLLM, calentar, completar
from tfm_nlsql.runtime.contrato import cargar_contrato
from tfm_nlsql.runtime.ejecutor import conexion_lectura, ejecutar, validar_binding
from tfm_nlsql.runtime.prompt import construir_prompt
from tfm_nlsql.runtime.traza import RegistroTraza, persistir
from tfm_nlsql.runtime.validador import (
    ErrorValidacion,
    inyectar_limite,
    validar_politica,
)
from tfm_nlsql.rutas import GOLD_DB

_CERCA_BLOQUE = re.compile(
    r"```(?:sql)?\s*\n?(.*?)(?:```|$)", re.DOTALL | re.IGNORECASE
)
_calentado = False


@dataclass
class ResultadoConsulta:
    pregunta: str
    sql: str | None
    columnas: list[str] = field(default_factory=list)
    filas: list[tuple] = field(default_factory=list)
    abstencion: str | None = None
    supuestos: list[str] = field(default_factory=list)
    error: str | None = None
    id_traza: int | None = None
    prompt_n: int | None = None
    prompt_ms: float | None = None
    predicted_n: int | None = None
    predicted_ms: float | None = None


def extraer_salida(texto: str) -> tuple[str | None, str | None]:
    t = texto.strip()
    if t.upper().startswith("ABSTENCION:"):
        return None, t.split("\n", 1)[0].strip()
    bloque = _CERCA_BLOQUE.search(t)
    if bloque:
        t = bloque.group(1).strip()
    t = re.split(r"\n(?:Pregunta:|<\|im_end\|>|<\|im_start\|>)", t, maxsplit=1)[0]
    t = t.strip()
    if ";" in t:
        t = t.split(";", 1)[0].strip()
    return (t or None), None


def supuestos_de(sql: str | None) -> list[str]:
    if not sql:
        return []
    return [
        ln.lstrip()[2:].strip()
        for ln in sql.splitlines()
        if ln.lstrip().startswith("--")
    ]


def validar_para_ejecutar(sql: str, columnas: dict[str, frozenset[str]], con) -> str:
    """Inyecta LIMIT, valida política y binding. Devuelve la cadena a ejecutar."""
    reescrito = inyectar_limite(sql)
    validar_politica(reescrito, columnas)
    validar_binding(con, reescrito)
    return reescrito


def consultar(
    pregunta: str,
    *,
    gold: Path | None = None,
    calentar_cache: bool = True,
) -> ResultadoConsulta:
    global _calentado
    _, columnas, version = cargar_contrato()
    t0 = time.perf_counter()
    if calentar_cache and not _calentado:
        calentar(construir_prompt("calentamiento"))
        _calentado = True
    t_calor = time.perf_counter()

    prompt = construir_prompt(pregunta)
    gen = completar(prompt)
    primera = gen
    sql_crudo, abstencion = extraer_salida(gen.texto)
    supuestos = supuestos_de(sql_crudo)
    reintentos: list[dict] = []
    veredicto = "pendiente"
    sql_final: str | None = None
    error: str | None = None
    columnas_out: list[str] = []
    filas: list[tuple] = []
    t_gen = time.perf_counter()

    if abstencion:
        veredicto = "abstencion"
    elif not sql_crudo:
        veredicto = "rechazado"
        error = "el modelo no devolvió SQL"
    else:
        try:
            with conexion_lectura(gold or GOLD_DB) as con:
                sql_final, veredicto, error, reintentos, gen_corr = _ciclo(
                    pregunta, sql_crudo, columnas, con
                )
                if gen_corr is not None:
                    gen = gen_corr
                    sql_corr, _ = extraer_salida(gen_corr.texto)
                    supuestos = supuestos_de(sql_corr)
                if sql_final is not None:
                    columnas_out, filas = ejecutar(con, sql_final)
                    veredicto = "aceptado"
        except FileNotFoundError:
            veredicto = "error_ejecucion"
            error = f"no existe Gold en {gold or GOLD_DB}"
        except Exception as e:
            veredicto = "error_ejecucion"
            error = str(e)

    t_fin = time.perf_counter()
    id_traza = persistir(
        RegistroTraza(
            pregunta=pregunta,
            version_contrato=version,
            prompt=prompt,
            sql_crudo=sql_crudo,
            veredicto_validador=veredicto,
            reintentos=reintentos,
            sql_final=sql_final,
            latencia={
                "calentamiento_ms": (t_calor - t0) * 1000,
                "generacion_ms": (t_gen - t_calor) * 1000,
                "total_ms": (t_fin - t0) * 1000,
                "prompt_ms": gen.prompt_ms,
                "predicted_ms": gen.predicted_ms,
            },
            tokens={
                "prompt_n": gen.prompt_n,
                "predicted_n": gen.predicted_n,
            },
            filas_devueltas=len(filas) if veredicto == "aceptado" else None,
            error=error,
        )
    )
    return ResultadoConsulta(
        pregunta=pregunta,
        sql=sql_final,
        columnas=columnas_out,
        filas=filas,
        abstencion=abstencion,
        supuestos=supuestos,
        error=error,
        id_traza=id_traza,
        prompt_n=primera.prompt_n,
        prompt_ms=primera.prompt_ms,
        predicted_n=primera.predicted_n,
        predicted_ms=primera.predicted_ms,
    )


def _ciclo(
    pregunta: str,
    sql_crudo: str,
    columnas: dict[str, frozenset[str]],
    con,
) -> tuple[str | None, str, str | None, list[dict], RespuestaLLM | None]:
    reintentos: list[dict] = []
    gen_corr: RespuestaLLM | None = None
    actual = sql_crudo
    ultimo_error = "reintentos agotados"
    for intento in range(2):
        try:
            return (
                validar_para_ejecutar(actual, columnas, con),
                "aceptado",
                None,
                reintentos,
                gen_corr,
            )
        except ErrorValidacion as e:
            ultimo_error = e.motivo
            if intento == 0:
                reintentos.append({"sql": actual, "error": e.motivo})
                prompt = construir_prompt(pregunta, actual, e.motivo)
                gen_corr = completar(prompt)
                sql2, abst = extraer_salida(gen_corr.texto)
                if abst or not sql2:
                    return None, "rechazado", e.motivo, reintentos, gen_corr
                actual = sql2
    return None, "rechazado", ultimo_error, reintentos, gen_corr
