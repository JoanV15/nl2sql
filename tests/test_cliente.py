"""El cliente HTTP no deja escapar TimeoutError del socket (prefill 7B)."""

from __future__ import annotations

from urllib.request import Request

import pytest

from tfm_nlsql.runtime import cliente
from tfm_nlsql.runtime.cliente import ErrorLLM, _leer, calentar


def test_timeout_de_socket_es_error_llm(monkeypatch) -> None:
    def boom(*_a, **_k):
        raise TimeoutError("timed out")

    monkeypatch.setattr(cliente, "urlopen", boom)
    with pytest.raises(ErrorLLM, match="timeout"):
        _leer(Request("http://127.0.0.1:8080/completion"), 180)


def test_calentar_espera_el_prefill_del_7b(monkeypatch) -> None:
    visto: dict[str, float] = {}

    def fake_completar(prompt, *, n_predict=256, cache_prompt=True, timeout=180):
        visto["n_predict"] = n_predict
        visto["timeout"] = timeout
        return cliente.RespuestaLLM(texto="")

    monkeypatch.setattr(cliente, "completar", fake_completar)
    calentar("x")
    assert visto["n_predict"] == 1
    assert visto["timeout"] == 360
