"""Catálogo cerrado Olist. OM en vivo solo si TFM_OM_URL responde."""

from __future__ import annotations

import urllib.error
import urllib.request

import pytest

from tfm_nlsql.plataforma.om_ingest import OM_UI, SERVICIO, _jwt, _peticion
from tfm_nlsql.plataforma.om_negocio import (
    COLUMNAS_SIMULADAS,
    DESCRIPCION_OBT,
    DOMINIOS,
    GLOSARIO,
    ORIGEN_TABLA,
    TAG_SIMULADO,
    TERMINOS,
)

NOMBRES = (
    "Facturación",
    "Caja cobrada",
    "Portes",
    "Ticket medio",
    "Cliente",
    "Venta válida",
    "Censo frente a ventas",
    "Pedido tardío",
    "Reseña negativa",
    "Fecha de referencia",
    "Macro-categoría",
    "Categoría de producto",
)


def test_doce_terminos_cerrados() -> None:
    assert tuple(t["nombre"] for t in TERMINOS) == NOMBRES
    assert len(TERMINOS) == 12


def test_sinonimos_y_enlaces_del_encargo() -> None:
    por = {t["nombre"]: t for t in TERMINOS}
    assert por["Facturación"]["sinonimos"] == ("GMV", "ventas", "ingresos")
    assert por["Facturación"]["columnas"] == (
        "obt_pedidos.importe_articulos",
        "obt_lineas_pedido.importe_articulos",
        "obt_vendedores.importe_articulos",
    )
    assert por["Caja cobrada"]["sinonimos"] == ("dinero ingresado",)
    assert por["Caja cobrada"]["columnas"] == ("obt_pedidos.importe_pagado",)
    assert por["Portes"]["sinonimos"] == ("envío", "flete", "gastos de envío")
    assert por["Portes"]["columnas"] == (
        "obt_pedidos.importe_flete",
        "obt_lineas_pedido.importe_flete",
    )
    assert por["Ticket medio"]["sinonimos"] == ("AOV",)
    assert por["Ticket medio"]["columnas"] == ()
    assert por["Cliente"]["columnas"] == ("obt_pedidos.id_cliente_persona",)
    assert "id_cliente_pedido" in por["Cliente"]["definicion"]
    assert por["Venta válida"]["columnas"] == (
        "obt_pedidos.es_venta_valida",
        "obt_lineas_pedido.es_venta_valida",
    )
    assert "D-13" in por["Venta válida"]["definicion"]
    assert por["Censo frente a ventas"]["columnas"] == ()
    assert "D-48" in por["Censo frente a ventas"]["definicion"]
    assert por["Pedido tardío"]["columnas"] == ("obt_pedidos.dias_desviacion_entrega",)
    assert por["Reseña negativa"]["columnas"] == (
        "obt_pedidos.nota_resena",
        "obt_lineas_pedido.nota_resena",
    )
    assert por["Fecha de referencia"]["columnas"] == ()
    assert "2018-10-17" in por["Fecha de referencia"]["definicion"]
    assert por["Macro-categoría"]["columnas"] == (
        "obt_lineas_pedido.macro_categoria",
        "obt_embudo_web.macro_categoria",
    )
    assert "portugués" in por["Categoría de producto"]["definicion"]
    assert por["Categoría de producto"]["columnas"] == (
        "obt_lineas_pedido.categoria_producto",
        "obt_embudo_web.categoria_producto",
    )


def test_no_inventa_columnas() -> None:
    cols = [c for t in TERMINOS for c in t["columnas"]]
    assert all("ticket_medio" not in c for c in cols)
    assert "obt_pedidos.id_cliente_pedido" not in cols
    assert all(c.split(".", 1)[0].startswith("obt_") for c in cols)


def test_dominios_y_origen() -> None:
    assert tuple(d["nombre"] for d in DOMINIOS) == (
        "Pedidos",
        "Líneas de pedido",
        "Vendedores",
        "Embudo web",
    )
    assert {d["tabla"] for d in DOMINIOS} == set(DESCRIPCION_OBT)
    assert ORIGEN_TABLA["obt_embudo_web"] == TAG_SIMULADO
    assert ORIGEN_TABLA["obt_pedidos"] == "origen.real"
    assert ORIGEN_TABLA["stg_clickstream"] == TAG_SIMULADO
    assert "obt_pedidos.id_transportista" in COLUMNAS_SIMULADAS
    assert "obt_pedidos.tipo_incidencia" in COLUMNAS_SIMULADAS
    for d in DOMINIOS:
        assert "Grano:" in d["descripcion"]


def _om_responde() -> bool:
    try:
        urllib.request.urlopen(f"{OM_UI}/api/v1/system/version", timeout=2)
        return True
    except (OSError, urllib.error.URLError):
        return False


@pytest.mark.skipif(not _om_responde(), reason="OpenMetadata no responde")
def test_glosario_olist_via_api() -> None:
    token = _jwt()
    terms = _peticion("GET", "/v1/glossaryTerms?limit=100", token)
    olist = [
        t
        for t in terms.get("data", [])
        if str(t.get("fullyQualifiedName", "")).startswith(f"{GLOSARIO}.")
    ]
    assert {t["name"] for t in olist} >= set(NOMBRES)
    fact = next(t for t in olist if t["name"] == "Facturación")
    assert set(fact.get("synonyms") or []) == {"GMV", "ventas", "ingresos"}
    tabla = _peticion(
        "GET",
        f"/v1/tables/name/{SERVICIO}.gold.main.obt_pedidos?fields=columns,tags,domain",
        token,
    )
    ia = next(c for c in tabla["columns"] if c["name"] == "importe_articulos")
    assert f"{GLOSARIO}.Facturación" in {x.get("tagFQN") for x in ia.get("tags") or []}
    assert (tabla.get("domain") or {}).get("name") == "Pedidos"
    assert "origen.real" in {x.get("tagFQN") for x in tabla.get("tags") or []}
    trans = next(c for c in tabla["columns"] if c["name"] == "id_transportista")
    assert TAG_SIMULADO in {x.get("tagFQN") for x in trans.get("tags") or []}
    embudo = _peticion(
        "GET",
        f"/v1/tables/name/{SERVICIO}.gold.main.obt_embudo_web?fields=tags,domain",
        token,
    )
    assert TAG_SIMULADO in {x.get("tagFQN") for x in embudo.get("tags") or []}
    assert (embudo.get("domain") or {}).get("name") == "Embudo web"
