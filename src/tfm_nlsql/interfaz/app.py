"""Interfaz Streamlit (D-39). Fecha de referencia visible; consulta vía consultar()."""

from __future__ import annotations

from pathlib import Path

from tfm_nlsql.interfaz.cli import FECHA_REFERENCIA
from tfm_nlsql.runtime.ejecutor import formatear
from tfm_nlsql.runtime.orquestador import ResultadoConsulta, consultar, supuestos_de

NIVEL1 = "¿Cuántos pedidos hemos hecho en total?"
PREGUNTA_57 = "¿Cuál es nuestro margen de beneficio?"


def _poner(pregunta: str) -> None:
    import streamlit as st

    st.session_state["pregunta"] = pregunta
    st.session_state["lanzar"] = True


def _mostrar(r: ResultadoConsulta) -> None:
    import streamlit as st

    supuestos = r.supuestos or supuestos_de(r.sql)
    if supuestos:
        st.subheader("Supuestos")
        for s in supuestos:
            st.write(s)
    if r.sql:
        st.subheader("SQL")
        st.code(r.sql, language="sql")
    if r.abstencion:
        st.warning(r.abstencion)
        return
    if r.error:
        st.error(f"Rechazado: {r.error}")
        if r.sql is None:
            return
    st.subheader("Resultado")
    st.code(formatear(r.columnas, r.filas))


def pagina() -> None:
    import streamlit as st

    st.set_page_config(page_title="NL-to-SQL Olist")
    st.title("NL-to-SQL Olist")
    st.info(f"Fecha de referencia: {FECHA_REFERENCIA}")

    st.text_area("Pregunta", key="pregunta", height=80)
    c1, c2, c3 = st.columns(3)
    c1.button("Nivel 1: pedidos totales", on_click=_poner, args=(NIVEL1,))
    c2.button("57: margen de beneficio", on_click=_poner, args=(PREGUNTA_57,))
    if c3.button("Consultar") and (st.session_state.get("pregunta") or "").strip():
        st.session_state["lanzar"] = True

    if not st.session_state.pop("lanzar", False):
        return
    pregunta = (st.session_state.get("pregunta") or "").strip()
    if not pregunta:
        st.warning("Escribe una pregunta.")
        return
    with st.spinner("Consultando…"):
        try:
            r = consultar(pregunta)
        except Exception as e:
            st.error(str(e))
            return
    _mostrar(r)


def main() -> None:
    import sys

    from streamlit.web.cli import main as stcli

    sys.argv = ["streamlit", "run", str(Path(__file__).resolve()), *sys.argv[1:]]
    raise SystemExit(stcli())


if __name__ == "__main__":
    pagina()
