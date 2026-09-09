"""Cliente HTTP de llama-server (D-35, D-34)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from tfm_nlsql.rutas import LLAMA_URL

N_PREDICT = 120
PARADA = ["<|im_end|>", "<|im_start|>"]


@dataclass(frozen=True)
class RespuestaLLM:
    texto: str
    prompt_n: int | None = None
    prompt_ms: float | None = None
    predicted_n: int | None = None
    predicted_ms: float | None = None


class ErrorLLM(RuntimeError):
    pass


def _post(ruta: str, cuerpo: dict, timeout: float) -> dict:
    data = json.dumps(cuerpo).encode("utf-8")
    req = Request(
        f"{LLAMA_URL.rstrip('/')}{ruta}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        detalle = e.read().decode("utf-8", errors="replace")
        raise ErrorLLM(f"llama-server {e.code}: {detalle}") from e
    except URLError as e:
        raise ErrorLLM(f"llama-server no responde en {LLAMA_URL}: {e.reason}") from e


def completar(
    prompt: str, *, n_predict: int = N_PREDICT, cache_prompt: bool = True
) -> RespuestaLLM:
    raw = _post(
        "/completion",
        {
            "prompt": prompt,
            "n_predict": n_predict,
            "temperature": 0.0,
            "cache_prompt": cache_prompt,
            "stop": PARADA,
        },
        timeout=180,
    )
    timings = raw.get("timings") or {}
    return RespuestaLLM(
        texto=raw.get("content") or raw.get("content", "") or "",
        prompt_n=timings.get("prompt_n"),
        prompt_ms=timings.get("prompt_ms"),
        predicted_n=timings.get("predicted_n"),
        predicted_ms=timings.get("predicted_ms"),
    )


def calentar(prompt: str) -> None:
    """P-07 / D-34: paga el prefill en frío antes de aceptar preguntas."""
    completar(prompt, n_predict=1)


def contar_fichas(texto: str) -> int:
    raw = _post("/tokenize", {"content": texto}, timeout=60)
    tokens = raw.get("tokens")
    if tokens is None:
        raise ErrorLLM(f"/tokenize no devolvió tokens: {raw!r}")
    return len(tokens)
