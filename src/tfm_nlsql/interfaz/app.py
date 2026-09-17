"""Interfaz Streamlit (D-39, R-05). Conversación: el dato aparece al preguntar."""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from pathlib import Path

from tfm_nlsql.interfaz.cli import FECHA_REFERENCIA, mensaje_error
from tfm_nlsql.runtime.orquestador import (
    ResultadoConsulta,
    consultar,
    modelo_ocupado,
    precalentar,
    reservar_modelo,
    supuestos_de,
)
from tfm_nlsql.runtime.validador import tablas_gold_citadas
from tfm_nlsql.rutas import GOLD_DB, LLAMA_URL

PEDIDOS_TOTALES = "¿Cuántos pedidos hemos hecho en total?"
FACTURACION_2018 = "¿Cuánto facturamos en 2018?"
TICKET_MEDIO = "¿Cuál es el ticket medio de un pedido?"
CATEGORIAS = "¿Qué categorías de producto venden más?"
CLIENTES_ESTADO = "¿Cuántos clientes tenemos en cada estado?"
PAGO = "¿Cuál es el método de pago más usado?"
RESENAS = "¿Cuál es la nota media de las reseñas?"
EMBUDO = "¿Qué categorías acumulan más carritos abandonados?"
LINEAS = "¿Cuántos artículos suele llevar un pedido?"

PLACEHOLDER = "¿Qué métrica o dato de Olist necesitas consultar hoy?"

ATAJOS = (
    ("Pedidos totales", PEDIDOS_TOTALES),
    ("Facturación 2018", FACTURACION_2018),
    ("Ticket medio", TICKET_MEDIO),
    ("Categorías más vendidas", CATEGORIAS),
    ("Clientes por estado", CLIENTES_ESTADO),
    ("Método de pago más usado", PAGO),
    ("Valoración media", RESENAS),
    ("Carritos abandonados", EMBUDO),
    ("Artículos por pedido", LINEAS),
)

AVISO_SIMULADO = (
    "Logística y clickstream/embudo son simulados (ids reales). "
    "Las reseñas circulan por Mongo; el contenido es el CSV de Olist."
)
BANNER = f"Fecha de referencia: {FECHA_REFERENCIA} · {AVISO_SIMULADO}"

VEREDICTOS = {
    "aceptado": "Respondida",
    "abstencion": "Abstención declarada",
    "rechazado": "Rechazada por el validador",
    "error_ejecucion": "Error al ejecutar la consulta",
    "error_runtime": "Modelo no disponible",
    "pendiente": "Sin veredicto",
}

FILAS_EN_GRAFICA = 20
_MES = re.compile(r"^\d{4}-\d{2}")


def veredicto_humano(veredicto: str) -> str:
    return VEREDICTOS.get(veredicto, veredicto)


def _poner(pregunta: str) -> None:
    import streamlit as st

    st.session_state["pregunta"] = pregunta
    st.session_state["lanzar"] = True


def _nueva_consulta() -> None:
    import streamlit as st

    st.session_state.pop("ultimo", None)
    st.session_state["pregunta"] = ""


def tabla(columnas: Sequence[str], filas: Sequence[tuple]) -> dict[str, list]:
    """Columnas → valores, con nombres únicos para no perder columnas repetidas."""
    nombres: list[str] = []
    for i, c in enumerate(columnas):
        nombres.append(c if c not in nombres else f"{c}_{i}")
    return {n: [f[i] for f in filas] for i, n in enumerate(nombres)}


def _es_numero(valor) -> bool:
    return isinstance(valor, int | float | Decimal) and not isinstance(valor, bool)


def _es_fecha(valor) -> bool:
    return isinstance(valor, date) or (
        isinstance(valor, str) and bool(_MES.match(valor))
    )


def forma_resultado(columnas: Sequence[str], filas: Sequence[tuple]) -> str:
    """Cómo se lee mejor el resultado: métrica, serie, ranking o tabla."""
    if not columnas or not filas:
        return "tabla"
    if len(filas) == 1 and len(columnas) == 1:
        return "metrica"
    if len(columnas) == 2 and len(filas) > 1 and _es_numero(filas[0][1]):
        if _es_fecha(filas[0][0]):
            return "serie"
        if isinstance(filas[0][0], str):
            return "ranking"
    return "tabla"


def _numero(valor) -> str:
    """Formato de negocio: miles con punto y decimales con coma."""
    if not _es_numero(valor):
        return "—" if valor is None else str(valor)
    if isinstance(valor, int):
        return f"{valor:,}".replace(",", ".")
    crudo = f"{float(valor):,.2f}"
    entero, _, decimal = crudo.partition(".")
    return f"{entero.replace(',', '.')},{decimal}"


def dato(columna: str, valor) -> str:
    """Cifra para pantalla. Sin R$, € ni $: el contrato ya fija BRL (D-12)."""
    del columna
    return _numero(valor)


def _etiqueta(columna: str) -> str:
    return columna.replace("_", " ").capitalize()


def csv_resultado(columnas: Sequence[str], filas: Sequence[tuple]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(columnas)
    w.writerows(filas)
    return buf.getvalue()


def resumen_dato(r: ResultadoConsulta) -> str:
    if r.veredicto != "aceptado" or not r.columnas:
        return "—"
    if forma_resultado(r.columnas, r.filas) == "metrica":
        return dato(r.columnas[0], r.filas[0][0])
    return f"{len(r.filas)} filas"


def _metadatos_modelo() -> tuple[bool, dict | str]:
    from tfm_nlsql.runtime.cliente import metadatos_servidor

    try:
        return True, metadatos_servidor()
    except Exception as e:  # noqa: BLE001 — el panel informa, no interrumpe
        return False, mensaje_error(str(e))


def _csv(columnas: Sequence[str], filas: Sequence[tuple]) -> None:
    import streamlit as st

    st.download_button(
        "Descargar CSV",
        data=csv_resultado(columnas, filas),
        file_name="resultado.csv",
        mime="text/csv",
    )


def _pintar_resultado(r: ResultadoConsulta) -> None:
    import streamlit as st

    if not r.columnas:
        return
    st.subheader("Resultado")
    datos = tabla(r.columnas, r.filas)
    forma = forma_resultado(r.columnas, r.filas)
    if forma == "metrica":
        texto = dato(r.columnas[0], r.filas[0][0])
        with st.container(border=True):
            st.metric(_etiqueta(r.columnas[0]), texto)
        _csv(r.columnas, r.filas)
        return
    if forma in ("serie", "ranking"):
        eje, valor = list(datos)[0], list(datos)[1]
        recorte = {k: v[:FILAS_EN_GRAFICA] for k, v in datos.items()}
        grafica = st.line_chart if forma == "serie" else st.bar_chart
        grafica(recorte, x=eje, y=valor)
        if len(r.filas) > FILAS_EN_GRAFICA:
            st.caption(
                f"La gráfica muestra las {FILAS_EN_GRAFICA} primeras de "
                f"{len(r.filas)} filas; la tabla, todas."
            )
    st.dataframe(datos, width="stretch")
    st.caption(f"{len(r.filas)} filas")
    _csv(r.columnas, r.filas)


def _mostrar(r: ResultadoConsulta) -> None:
    import streamlit as st

    if r.abstencion:
        st.warning(r.abstencion)
    elif r.error:
        st.error(mensaje_error(r.error))
    _pintar_resultado(r)


def _como_calculado(r: ResultadoConsulta) -> None:
    """SQL y supuestos para auditar (D-39). Cerrado. Cero inferencia extra."""
    import streamlit as st

    if not r.sql and not (r.supuestos or supuestos_de(r.sql)):
        return
    with st.expander("Cómo se ha calculado", expanded=False):
        supuestos = (r.supuestos or supuestos_de(r.sql))[:4]
        if supuestos:
            for s in supuestos:
                st.markdown(f"- {s}")
        else:
            st.caption("El SQL no declara supuestos en comentarios.")
        if r.sql:
            st.code(r.sql, language="sql")


def _detalle_tecnico(r: ResultadoConsulta) -> None:
    """Instrumentación (D-22). Solo después de una pregunta."""
    import streamlit as st

    from tfm_nlsql.runtime.contrato import cargar_contrato

    with st.expander("Detalle técnico"):
        if GOLD_DB.exists():
            mb = GOLD_DB.stat().st_size / 1_048_576
            st.markdown(f"- Gold: `{GOLD_DB}` ({mb:,.0f} MB)")
        else:
            st.error(f"Gold no encontrado en {GOLD_DB}. Ejecuta «tfm-nlsql-gold».")
        _, columnas, version = cargar_contrato()
        st.caption(
            f"Contrato semántico {version} · {len(columnas)} tablas Gold: "
            + ", ".join(f"{t} ({len(c)} col.)" for t, c in sorted(columnas.items()))
        )
        vivo, meta = _metadatos_modelo()
        if vivo and isinstance(meta, dict):
            st.markdown(
                f"- Modelo: `{meta.get('modelo') or 'desconocido'}`\n"
                f"- Cuantización: `{meta.get('cuantizacion')}`\n"
                f"- Ventana de contexto: {meta.get('n_ctx')} fichas\n"
                f"- Hilos: {meta.get('hilos')}\n"
                f"- Servidor: `{LLAMA_URL}`"
            )
        else:
            st.error(f"Modelo: {meta}")
        citadas = tablas_gold_citadas(r.sql or "")
        st.markdown(
            "- Tablas Gold en el SQL: "
            + (", ".join(f"`{t}`" for t in citadas) if citadas else "ninguna")
        )
        st.divider()
        st.markdown(
            f"- Veredicto: `{r.veredicto}`\n"
            f"- Traza persistida: "
            f"{'#' + str(r.id_traza) if r.id_traza is not None else '—'}\n"
            f"- Fichas: {r.prompt_n or '—'} de prompt, "
            f"{r.predicted_n or '—'} generadas\n"
            f"- Latencia total: {_ms(r.total_ms)}"
        )
        if r.etapas:
            st.dataframe(
                {
                    "Etapa": [e["etapa"] for e in r.etapas],
                    "ms": [e["ms"] for e in r.etapas],
                    "Estado": [
                        "correcta" if e.get("ok") else "fallida" for e in r.etapas
                    ],
                    "Detalle": [e.get("detalle", "") for e in r.etapas],
                },
                width="stretch",
            )
        for intento in r.reintentos:
            st.caption(f"Reintento (D-20): {mensaje_error(intento.get('error', ''))}")
            st.code(intento.get("sql", ""), language="sql")
        if r.error:
            st.caption("Motivo técnico del validador:")
            st.code(r.error, language="text")


def _ms(valor: float | None) -> str:
    return "—" if valor is None else f"{valor / 1000:.2f} s"


def _marca(veredicto: str) -> str:
    if veredicto == "aceptado":
        return ":green[✓]"
    if veredicto == "abstencion":
        return "○"
    return "✗"


def _sidebar(ocupado: bool) -> None:
    import streamlit as st

    filas = st.session_state.get("historial") or []
    with st.sidebar:
        st.markdown("**Historial**")
        st.button(
            "Nueva consulta",
            on_click=_nueva_consulta,
            disabled=ocupado or not st.session_state.get("ultimo"),
            width="stretch",
        )
        if not filas:
            st.caption("Las preguntas de esta sesión aparecerán aquí.")
            return
        for i, f in enumerate(filas):
            st.markdown(
                f"{_marca(f['veredicto'])} {veredicto_humano(f['veredicto'])}"
                f" · {f['dato']}"
            )
            st.button(
                f["pregunta"],
                key=f"hist_{i}",
                on_click=_poner,
                args=(f["pregunta"],),
                disabled=ocupado,
                width="stretch",
            )


def _resumen(r: ResultadoConsulta) -> dict:
    return {
        "pregunta": r.pregunta,
        "veredicto": r.veredicto,
        "dato": resumen_dato(r),
    }


def _caja_pregunta(ocupado: bool) -> bool:
    import streamlit as st

    with st.form("consulta", border=False):
        q, b = st.columns([8, 1.2])
        q.text_input(
            "Tu pregunta",
            key="pregunta",
            placeholder=PLACEHOLDER,
            disabled=ocupado,
            label_visibility="collapsed",
        )
        return b.form_submit_button("Preguntar", disabled=ocupado)


def _sugeridas(ocupado: bool) -> None:
    import streamlit as st

    st.caption("Consultas sugeridas")
    cols = st.columns(3)
    for i, (etiqueta, pregunta) in enumerate(ATAJOS):
        cols[i % 3].button(
            etiqueta,
            on_click=_poner,
            args=(pregunta,),
            disabled=ocupado,
            width="stretch",
        )


def _inicio(ocupado: bool) -> bool:
    import streamlit as st

    _, centro, _ = st.columns([1, 2, 1])
    with centro:
        st.title("Analítica de negocio Olist")
        st.caption(BANNER)
        enviado = _caja_pregunta(ocupado)
    _sugeridas(ocupado)
    return enviado


def _conversacion(r: ResultadoConsulta, ocupado: bool) -> bool:
    import streamlit as st

    st.caption(BANNER)
    st.markdown(f"**{r.pregunta}**")
    _mostrar(r)
    _como_calculado(r)
    _detalle_tecnico(r)
    return _caja_pregunta(ocupado)


def pagina() -> None:
    import streamlit as st

    st.set_page_config(
        page_title="Analítica de negocio Olist",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    ocupado = modelo_ocupado()

    if not st.session_state.get("_prefill_hecho"):
        with st.spinner("Preparando el modelo (caché del contrato)…"):
            st.session_state["_prefill_ok"] = precalentar()
        st.session_state["_prefill_hecho"] = True

    if st.session_state.get("_prefill_hecho") and not st.session_state.get("_prefill_ok"):
        st.caption(
            "El modelo no estaba listo al abrir. La primera pregunta pagará "
            "el prefill (~2 min, D-34)."
        )

    if st.session_state.pop("lanzar", False):
        pregunta = (st.session_state.get("pregunta") or "").strip()
        if pregunta:
            _consultar_y_guardar(pregunta)

    _sidebar(ocupado)

    ultimo = st.session_state.get("ultimo")
    enviado = _conversacion(ultimo, ocupado) if ultimo else _inicio(ocupado)

    if enviado:
        pregunta = (st.session_state.get("pregunta") or "").strip()
        if not pregunta:
            st.warning("Escribe una pregunta.")
        else:
            previo = st.session_state.get("ultimo")
            _consultar_y_guardar(pregunta)
            if st.session_state.get("ultimo") is not previo:
                st.rerun()


def _consultar_y_guardar(pregunta: str) -> None:
    """El resultado vive en la sesión: sobrevive a los redibujados de Streamlit."""
    import streamlit as st

    with reservar_modelo() as libre:
        if not libre:
            st.warning(
                "Hay una consulta en curso. El modelo atiende una a la vez: "
                "espera a que termine (R-08)."
            )
            return
        with st.spinner("Analizando la base de datos…"):
            try:
                r = consultar(pregunta)
            except Exception as e:  # noqa: BLE001 — se traduce y se muestra
                r = ResultadoConsulta(
                    pregunta=pregunta, sql=None, error=str(e), veredicto="error_runtime"
                )
    st.session_state["ultimo"] = r
    st.session_state.setdefault("historial", []).insert(0, _resumen(r))


def main() -> None:
    import sys

    from streamlit.web.cli import main as stcli

    sys.argv = ["streamlit", "run", str(Path(__file__).resolve()), *sys.argv[1:]]
    raise SystemExit(stcli())


if __name__ == "__main__":
    pagina()
