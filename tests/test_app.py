from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from tfm_nlsql.interfaz.app import (
    ATAJOS,
    PEDIDOS_TOTALES,
    PLACEHOLDER,
    csv_resultado,
    dato,
    tabla,
)
from tfm_nlsql.interfaz.cli import mensaje_error

APP = Path(__file__).resolve().parents[1] / "src" / "tfm_nlsql" / "interfaz" / "app.py"


@pytest.fixture(autouse=True)
def _sin_prefill_real(monkeypatch) -> None:
    """pagina() llama a precalentar(); con el 7B en marcha AppTest espera 3 s."""
    from tfm_nlsql.runtime import orquestador

    monkeypatch.setattr(orquestador, "llama_escucha", lambda: False)


def _preguntar(at: AppTest) -> AppTest:
    clave = next(b.key for b in at.button if b.label == "Preguntar")
    return at.button(key=clave).click().run()


def _codigos_cuerpo(at: AppTest) -> list[str]:
    """Code blocks de la columna principal, fuera de los expanders."""
    return [
        at.main.children[i].value
        for i in sorted(at.main.children)
        if type(at.main.children[i]).__name__ == "Code"
    ]


def _orden_principal(at: AppTest) -> list[str]:
    nombres: list[str] = []
    for i in sorted(at.main.children):
        nodo = at.main.children[i]
        tipo = type(nodo).__name__
        if tipo == "Subheader":
            nombres.append(nodo.value)
        elif tipo == "Metric":
            nombres.append(f"metric:{nodo.label}")
        elif tipo == "Expander":
            nombres.append(f"expander:{nodo.label}")
    return nombres


def test_layout_inicio_limpio() -> None:
    at = AppTest.from_file(str(APP))
    at.run()
    assert at.exception is None or not list(at.exception)
    assert at.title[0].value == "Analítica de negocio Olist"
    assert any("2018-10-17" in c.value and "simulados" in c.value for c in at.caption)
    assert not at.info
    assert not at.metric
    assert not any(e.label == "Detalle técnico" for e in at.expander)
    assert any("Consultas sugeridas" in c.value for c in at.caption)
    etiquetas = [b.label for b in at.button]
    for etiqueta, _pregunta in ATAJOS:
        assert etiqueta in etiquetas
    assert "Preguntar" in etiquetas
    assert "Nueva consulta" in etiquetas
    assert at.text_input
    assert PLACEHOLDER in at.text_input[0].proto.placeholder
    assert not at.text_area


def test_inicio_no_llama_al_modelo(monkeypatch) -> None:
    from tfm_nlsql.runtime import cliente, orquestador

    monkeypatch.setattr(
        orquestador,
        "consultar",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("consultar")),
    )
    monkeypatch.setattr(orquestador, "precalentar", lambda: False)
    monkeypatch.setattr(
        cliente,
        "metadatos_servidor",
        lambda: (_ for _ in ()).throw(AssertionError("llama-server")),
    )
    at = AppTest.from_file(str(APP))
    at.run()
    assert at.exception is None or not list(at.exception)
    assert not at.metric
    assert any("prefill" in c.value and "D-34" in c.value for c in at.caption)


def test_panel_de_estado_tras_preguntar(monkeypatch) -> None:
    from tfm_nlsql.runtime import orquestador

    falso = orquestador.ResultadoConsulta(
        pregunta=PEDIDOS_TOTALES,
        sql="SELECT COUNT(*) AS n FROM obt_pedidos",
        columnas=["n"],
        filas=[(99441,)],
        id_traza=1,
        veredicto="aceptado",
    )
    monkeypatch.setattr(orquestador, "consultar", lambda *a, **k: falso)

    at = AppTest.from_file(str(APP))
    at.run()
    at.text_input[0].set_value(PEDIDOS_TOTALES)
    _preguntar(at)

    exp = next(e for e in at.expander if e.label == "Detalle técnico")
    textos = (
        [m.value for m in exp.markdown]
        + [e.value for e in exp.error]
        + [c.value for c in exp.caption]
    )
    assert any("Gold" in t or "gold.duckdb" in t for t in textos)
    assert any("Contrato semántico" in t for t in textos)


def test_consultar_sin_pregunta_avisa() -> None:
    at = AppTest.from_file(str(APP))
    at.run()
    _preguntar(at)
    assert any("Escribe una pregunta" in w.value for w in at.warning)


def test_sql_no_esta_en_el_cuerpo_si_en_como_se_ha_calculado(monkeypatch) -> None:
    from tfm_nlsql.runtime import orquestador

    falso = orquestador.ResultadoConsulta(
        pregunta=PEDIDOS_TOTALES,
        sql="-- supuesto: solo ventas válidas\nSELECT COUNT(*) AS n FROM obt_pedidos",
        columnas=["n"],
        filas=[(99441,)],
        id_traza=7,
        veredicto="aceptado",
    )
    monkeypatch.setattr(orquestador, "consultar", lambda *a, **k: falso)

    at = AppTest.from_file(str(APP))
    at.run()
    at.text_input[0].set_value(PEDIDOS_TOTALES)
    _preguntar(at)

    assert at.exception is None or not list(at.exception)
    assert any(m.value == "99.441" for m in at.metric)
    cuerpo = _codigos_cuerpo(at)
    assert not any("SELECT" in (c or "") or "obt_pedidos" in (c or "") for c in cuerpo)
    como = next(e for e in at.expander if e.label == "Cómo se ha calculado")
    assert any("SELECT" in c.value and "obt_pedidos" in c.value for c in como.code)
    assert any("solo ventas válidas" in m.value for m in como.markdown)
    assert como.proto.expanded is False
    tech = next(e for e in at.expander if e.label == "Detalle técnico")
    assert tech.label != como.label
    assert any("obt_pedidos" in m.value for m in tech.markdown)


def test_panel_de_etapas_e_historial(monkeypatch) -> None:
    from tfm_nlsql.runtime import orquestador

    falso = orquestador.ResultadoConsulta(
        pregunta=PEDIDOS_TOTALES,
        sql="SELECT COUNT(*) AS n FROM obt_pedidos",
        columnas=["n"],
        filas=[(99441,)],
        id_traza=9,
        prompt_n=3067,
        predicted_n=17,
        veredicto="aceptado",
        total_ms=8800.0,
        etapas=[
            {"etapa": orquestador.ETAPA_GENERACION, "ms": 8500.0, "ok": True},
            {"etapa": orquestador.ETAPA_AST, "ms": 3.1, "ok": True},
            {"etapa": orquestador.ETAPA_EXPLAIN, "ms": 5.4, "ok": True},
            {"etapa": orquestador.ETAPA_EJECUCION, "ms": 12.0, "ok": True},
        ],
    )
    monkeypatch.setattr(orquestador, "consultar", lambda *a, **k: falso)

    at = AppTest.from_file(str(APP))
    at.run()
    at.text_input[0].set_value(PEDIDOS_TOTALES)
    _preguntar(at)

    exp = next(e for e in at.expander if e.label == "Detalle técnico")
    etapas = next(d.value for d in exp.dataframe if "Etapa" in d.value)
    assert list(etapas["Etapa"]) == [e["etapa"] for e in falso.etapas]
    assert not any(m.label == "Fichas generadas" for m in at.metric)
    assert PEDIDOS_TOTALES in [b.label for b in at.button]
    assert not at.success
    assert any(":green[✓]" in m.value and "Respondida" in m.value for m in at.markdown)

    at.run()
    assert PEDIDOS_TOTALES in [b.label for b in at.button]


def test_layout_resultado_antes_que_detalle_tecnico(monkeypatch) -> None:
    from tfm_nlsql.runtime import orquestador

    falso = orquestador.ResultadoConsulta(
        pregunta=PEDIDOS_TOTALES,
        sql="SELECT COUNT(*) AS n FROM obt_pedidos",
        columnas=["n"],
        filas=[(99441,)],
        id_traza=3,
        veredicto="aceptado",
        etapas=[{"etapa": orquestador.ETAPA_GENERACION, "ms": 1100.0, "ok": True}],
    )
    monkeypatch.setattr(orquestador, "consultar", lambda *a, **k: falso)

    at = AppTest.from_file(str(APP))
    at.run()
    at.text_input[0].set_value(PEDIDOS_TOTALES)
    _preguntar(at)

    orden = _orden_principal(at)
    assert orden.index("Resultado") < orden.index("expander:Cómo se ha calculado")
    assert orden.index("expander:Cómo se ha calculado") < orden.index(
        "expander:Detalle técnico"
    )


def test_historial_relanza(monkeypatch) -> None:
    from tfm_nlsql.runtime import orquestador

    llamadas: list[str] = []

    def fake(pregunta: str, **k):
        llamadas.append(pregunta)
        return orquestador.ResultadoConsulta(
            pregunta=pregunta,
            sql="SELECT COUNT(*) AS n FROM obt_pedidos",
            columnas=["n"],
            filas=[(99441,)],
            veredicto="aceptado",
        )

    monkeypatch.setattr(orquestador, "consultar", fake)

    at = AppTest.from_file(str(APP))
    at.run()
    at.text_input[0].set_value(PEDIDOS_TOTALES)
    _preguntar(at)
    assert llamadas == [PEDIDOS_TOTALES]

    hist = next(b for b in at.button if b.label == PEDIDOS_TOTALES)
    hist.click().run()
    assert llamadas == [PEDIDOS_TOTALES, PEDIDOS_TOTALES]


def test_csv_del_resultado(monkeypatch) -> None:
    from tfm_nlsql.runtime import orquestador

    falso = orquestador.ResultadoConsulta(
        pregunta=PEDIDOS_TOTALES,
        sql="SELECT COUNT(*) AS n FROM obt_pedidos",
        columnas=["n"],
        filas=[(99441,)],
        veredicto="aceptado",
    )
    monkeypatch.setattr(orquestador, "consultar", lambda *a, **k: falso)

    at = AppTest.from_file(str(APP))
    at.run()
    at.text_input[0].set_value(PEDIDOS_TOTALES)
    _preguntar(at)

    botones = list(at.download_button)
    assert any(b.label == "Descargar CSV" for b in botones)
    assert botones[0].proto.url.endswith(".csv")
    assert not any(c.value == "Copiar" for c in at.caption)
    assert not _codigos_cuerpo(at)


def test_sugeridas_desaparecen_al_preguntar(monkeypatch) -> None:
    from tfm_nlsql.runtime import orquestador

    falso = orquestador.ResultadoConsulta(
        pregunta=PEDIDOS_TOTALES,
        sql="SELECT COUNT(*) AS n FROM obt_pedidos",
        columnas=["n"],
        filas=[(99441,)],
        veredicto="aceptado",
    )
    monkeypatch.setattr(orquestador, "consultar", lambda *a, **k: falso)

    at = AppTest.from_file(str(APP))
    at.run()
    at.text_input[0].set_value(PEDIDOS_TOTALES)
    _preguntar(at)

    etiquetas = [b.label for b in at.button]
    assert "Categorías más vendidas" not in etiquetas
    assert not any("Consultas sugeridas" in c.value for c in at.caption)
    assert not at.title


def test_no_lanza_si_el_modelo_esta_ocupado(monkeypatch) -> None:
    from tfm_nlsql.runtime import orquestador

    monkeypatch.setattr(
        orquestador,
        "consultar",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no debía consultar")),
    )
    orquestador._EN_CURSO.acquire()
    try:
        at = AppTest.from_file(str(APP))
        at.run()
        assert at.text_input[0].proto.disabled
        lanzadores = [
            b for b in at.button if b.label in {"Preguntar", *[e for e, _ in ATAJOS]}
        ]
        assert lanzadores and all(b.proto.disabled for b in lanzadores)
    finally:
        orquestador._EN_CURSO.release()


def test_tabla_conserva_columnas_repetidas() -> None:
    assert tabla(["n", "n"], [(1, 2)]) == {"n": [1], "n_1": [2]}


def test_dato_sin_prefijo_moneda() -> None:
    assert dato("num_pedidos", 99441) == "99.441"
    assert dato("facturacion", 1234.5) == "1.234,50"
    assert dato("ticket_medio", 10) == "10"
    assert dato("importe_articulos", 1000) == "1.000"
    assert "R$" not in dato("facturacion", 1)
    assert "€" not in dato("facturacion", 1)
    assert not dato("facturacion", 1).startswith("$")


def test_csv_resultado_stdlib() -> None:
    texto = csv_resultado(["n"], [(99441,)])
    assert texto.splitlines()[0] == "n"
    assert "99441" in texto


def test_error_en_castellano_sin_dump_de_sqlglot() -> None:
    crudo = (
        "SQL no analizable: Expecting ). Line 1, Col: 42.\n"
        "  SELECT * FROM obt_pedidos WHERE (id_pedido\n                 ~~~~~~~~~"
    )
    mensaje = mensaje_error(crudo)
    assert "\n" not in mensaje
    assert "Line 1" not in mensaje and "~~~" not in mensaje
    assert mensaje.startswith("El modelo no devolvió una consulta SQL analizable")
    assert mensaje_error("tabla no permitida: clientes").startswith(
        "La consulta usa una tabla que no está en la capa Gold"
    )
    assert "lectura" in mensaje_error("solo se permiten SELECT y WITH")
