"""Protocolo P-07 sobre el prefijo real del contrato."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tfm_nlsql.runtime.cliente import completar  # noqa: E402
from tfm_nlsql.runtime.prompt import construir_prompt  # noqa: E402


def _fila(etiqueta: str, r) -> dict:
    prompt_ms = r.prompt_ms or 0.0
    predicted_ms = r.predicted_ms or 0.0
    prompt_n = r.prompt_n or 0
    predicted_n = r.predicted_n or 0
    return {
        "escenario": etiqueta,
        "prompt_n": prompt_n,
        "prompt_ms": round(prompt_ms, 1),
        "prefill_tok_s": (
            round(prompt_n / (prompt_ms / 1000), 1) if prompt_ms else None
        ),
        "predicted_n": predicted_n,
        "predicted_ms": round(predicted_ms, 1),
        "gen_tok_s": round(predicted_n / (predicted_ms / 1000), 1)
        if predicted_ms
        else None,
        "total_ms": round(prompt_ms + predicted_ms, 1),
    }


def main() -> int:
    p1 = construir_prompt("¿Cuántos pedidos hemos hecho en total?")
    p2 = construir_prompt("¿Cuál es el ticket medio de un pedido?")
    p3 = construir_prompt("¿Cuántos clientes tenemos en cada estado?")
    filas = [
        _fila("A — en frío, sin caché", completar(p1, cache_prompt=False)),
        _fila("B — misma pregunta, caché poblada", completar(p1, cache_prompt=True)),
        _fila(
            "C — caché caliente, pregunta distinta", completar(p2, cache_prompt=True)
        ),
        _fila("D — caché caliente, tercera pregunta", completar(p3, cache_prompt=True)),
    ]
    print(json.dumps(filas, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
