"""Contexto de negocio en OpenMetadata. No entra en el runtime (D-06, D-33)."""

from __future__ import annotations

import urllib.error

GLOSARIO = "Olist"
CLASIFICACION = "origen"
TAG_REAL = "origen.real"
TAG_SIMULADO = "origen.simulado"

# Conjunto cerrado del encargo. Definiciones = contrato / D-12 / D-13 / D-15 / D-48.
TERMINOS: tuple[dict, ...] = (
    {
        "nombre": "Facturación",
        "definicion": (
            "Facturación, GMV, ventas e ingresos significan importe_articulos, "
            "que excluye los portes (D-12)."
        ),
        "sinonimos": ("GMV", "ventas", "ingresos"),
        "columnas": (
            "obt_pedidos.importe_articulos",
            "obt_lineas_pedido.importe_articulos",
            "obt_vendedores.importe_articulos",
        ),
    },
    {
        "nombre": "Caja cobrada",
        "definicion": (
            "Caja cobrada y dinero ingresado significan importe_pagado. "
            "Incluye recargos de financiación y vales."
        ),
        "sinonimos": ("dinero ingresado",),
        "columnas": ("obt_pedidos.importe_pagado",),
    },
    {
        "nombre": "Portes",
        "definicion": (
            "Portes, envío, gastos de envío y flete significan importe_flete. "
            "Es lo cobrado al cliente, no lo pagado al transportista."
        ),
        "sinonimos": ("envío", "flete", "gastos de envío"),
        "columnas": (
            "obt_pedidos.importe_flete",
            "obt_lineas_pedido.importe_flete",
        ),
    },
    {
        "nombre": "Ticket medio",
        "definicion": (
            "Ticket medio y AOV son importe_articulos dividido entre el "
            "número de pedidos distintos. No existe una columna ticket_medio."
        ),
        "sinonimos": ("AOV",),
        "columnas": (),
    },
    {
        "nombre": "Cliente",
        "definicion": (
            "Cliente significa persona: contar id_cliente_persona distintos, "
            "nunca id_cliente_pedido (pregunta 28)."
        ),
        "sinonimos": (),
        "columnas": ("obt_pedidos.id_cliente_persona",),
    },
    {
        "nombre": "Venta válida",
        "definicion": (
            "Una venta es válida cuando estado_pedido no es canceled ni "
            "unavailable. La bandera es_venta_valida lo precalcula, pero "
            "estado_pedido sigue disponible (D-13)."
        ),
        "sinonimos": (),
        "columnas": (
            "obt_pedidos.es_venta_valida",
            "obt_lineas_pedido.es_venta_valida",
        ),
    },
    {
        "nombre": "Censo frente a ventas",
        "definicion": (
            "Contar clientes, reseñas, métodos de pago o pedidos es un censo "
            "sobre el total: no se filtra por es_venta_valida. La bandera "
            "solo aplica cuando la pregunta trata de ventas, importes o "
            "facturación (D-48)."
        ),
        "sinonimos": (),
        "columnas": (),
    },
    {
        "nombre": "Pedido tardío",
        "definicion": (
            "Un pedido llega tarde cuando dias_desviacion_entrega es mayor que cero."
        ),
        "sinonimos": (),
        "columnas": ("obt_pedidos.dias_desviacion_entrega",),
    },
    {
        "nombre": "Reseña negativa",
        "definicion": (
            "Una reseña es negativa cuando nota_resena es menor o igual que 2."
        ),
        "sinonimos": (),
        "columnas": (
            "obt_pedidos.nota_resena",
            "obt_lineas_pedido.nota_resena",
        ),
    },
    {
        "nombre": "Fecha de referencia",
        "definicion": (
            "Fecha de referencia: 2018-10-17. Toda expresión temporal relativa "
            "se resuelve contra esta fecha, nunca contra la fecha del "
            "sistema (D-15)."
        ),
        "sinonimos": (),
        "columnas": (),
    },
    {
        "nombre": "Macro-categoría",
        "definicion": (
            "macro_categoria toma doce valores: Electrónica e Informática, "
            "Electrodomésticos, Hogar y Muebles, Moda y Accesorios, Belleza y "
            "Salud, Deporte Juguetes y Ocio, Bricolaje Jardín y Construcción, "
            "Cultura Libros y Papelería, Alimentación y Bebidas, Bebé y "
            "Mascotas, Automoción, Otros y B2B. Los productos sin categoría "
            "se agrupan en Otros y B2B."
        ),
        "sinonimos": (),
        "columnas": (
            "obt_lineas_pedido.macro_categoria",
            "obt_embudo_web.macro_categoria",
        ),
    },
    {
        "nombre": "Categoría de producto",
        "definicion": (
            "categoria_producto conserva los nombres originales de Olist en "
            "portugués. No se traduce. Ante un término en castellano que "
            "abarque varias categorías, usar macro_categoria."
        ),
        "sinonimos": (),
        "columnas": (
            "obt_lineas_pedido.categoria_producto",
            "obt_embudo_web.categoria_producto",
        ),
    },
)

DOMINIOS: tuple[dict, ...] = (
    {
        "nombre": "Pedidos",
        "tabla": "obt_pedidos",
        "descripcion": (
            "Grano: un registro por pedido (id_pedido). Preguntas de pedidos, "
            "caja, portes y reseña a este grano."
        ),
    },
    {
        "nombre": "Líneas de pedido",
        "tabla": "obt_lineas_pedido",
        "descripcion": (
            "Grano: un registro por línea (id_pedido + num_linea). Un pedido "
            "con tres artículos ocupa tres filas."
        ),
    },
    {
        "nombre": "Vendedores",
        "tabla": "obt_vendedores",
        "descripcion": (
            "Grano: un registro por vendedor (id_vendedor). Censo completo; "
            "agregados de por vida, sin filtro temporal."
        ),
    },
    {
        "nombre": "Embudo web",
        "tabla": "obt_embudo_web",
        "descripcion": (
            "Grano: un registro por día y producto (fecha + id_producto). "
            "Clickstream simulado (R-05)."
        ),
    },
)

DESCRIPCION_OBT: dict[str, str] = {
    "obt_pedidos": (
        "Un registro por pedido (id_pedido). Pedidos del marketplace: estado, "
        "importes (facturación sin portes), cliente-persona y reseña. Toda "
        "pregunta sobre pedidos se responde aquí."
    ),
    "obt_lineas_pedido": (
        "Un registro por línea (id_pedido + num_linea). Detalle de artículos, "
        "categoría y vendedor. Los atributos de pedido se repiten en cada "
        "línea y no son aditivos."
    ),
    "obt_vendedores": (
        "Un registro por vendedor (id_vendedor). Censo completo, también "
        "quienes nunca vendieron. Los agregados cubren toda la vida del "
        "vendedor, sin filtro temporal."
    ),
    "obt_embudo_web": (
        "Un registro por día y producto (fecha + id_producto). Embudo de "
        "visitas a compra. Procede de clickstream simulado: no es dato "
        "transaccional real (R-05)."
    ),
}

ORIGEN_TABLA: dict[str, str] = {
    "obt_pedidos": TAG_REAL,
    "obt_lineas_pedido": TAG_REAL,
    "obt_vendedores": TAG_REAL,
    "obt_embudo_web": TAG_SIMULADO,
    "stg_clickstream": TAG_SIMULADO,
    "stg_eventos_logisticos": TAG_SIMULADO,
}

COLUMNAS_SIMULADAS: tuple[str, ...] = (
    "obt_pedidos.id_transportista",
    "obt_pedidos.tipo_incidencia",
)


def _etiqueta(fqn: str, fuente: str) -> dict:
    return {
        "tagFQN": fqn,
        "source": fuente,
        "labelType": "Manual",
        "state": "Confirmed",
    }


def _enlaces() -> dict[str, dict[str, list[str]]]:
    por_tabla: dict[str, dict[str, list[str]]] = {}
    for termino in TERMINOS:
        fqn = f"{GLOSARIO}.{termino['nombre']}"
        for ref in termino["columnas"]:
            tabla, col = ref.split(".", 1)
            por_tabla.setdefault(tabla, {}).setdefault(col, []).append(fqn)
    return por_tabla


def _simulado_por_tabla() -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for ref in COLUMNAS_SIMULADAS:
        tabla, col = ref.split(".", 1)
        out.setdefault(tabla, set()).add(col)
    return out


def _llamar(peticion, metodo: str, ruta: str, token: str, cuerpo=None) -> dict:
    try:
        return peticion(metodo, ruta, token, cuerpo)
    except urllib.error.HTTPError as e:
        raise RuntimeError(
            f"{metodo} {ruta}: {e.code} {e.read().decode()[:600]}"
        ) from e


def _get(peticion, ruta: str, token: str) -> dict | None:
    try:
        return peticion("GET", ruta, token)
    except urllib.error.HTTPError as e:
        detalle = e.read().decode()
        if e.code == 404:
            return None
        raise RuntimeError(f"GET {ruta}: {e.code} {detalle[:600]}") from e


def _columna_put(col: dict, tags: list[dict]) -> dict:
    item = {"name": col["name"], "dataType": col["dataType"]}
    if col.get("dataLength"):
        item["dataLength"] = col["dataLength"]
    if col.get("description"):
        item["description"] = col["description"]
    if tags:
        item["tags"] = tags
    return item


def _anotar_tabla(
    peticion,
    token: str,
    servicio: str,
    nombre: str,
    *,
    descripcion: str | None,
    dominio: str | None,
    tag_tabla: str | None,
    glosario_cols: dict[str, list[str]],
    cols_simuladas: set[str],
    exigida: bool,
) -> None:
    fqn = f"{servicio}.gold.main.{nombre}"
    tabla = _get(peticion, f"/v1/tables/name/{fqn}?fields=columns,tags,domain", token)
    if tabla is None:
        if exigida:
            raise RuntimeError(f"Falta {fqn}; publica el linaje dbt antes.")
        return
    columnas = []
    for col in tabla["columns"]:
        tags = [_etiqueta(g, "Glossary") for g in glosario_cols.get(col["name"], [])]
        if col["name"] in cols_simuladas:
            tags.append(_etiqueta(TAG_SIMULADO, "Classification"))
        columnas.append(_columna_put(col, tags))
    esquema = tabla.get("databaseSchema") or {}
    cuerpo: dict = {
        "name": nombre,
        "tableType": tabla.get("tableType") or "Regular",
        "columns": columnas,
        "databaseSchema": esquema.get("fullyQualifiedName") or f"{servicio}.gold.main",
    }
    if descripcion:
        cuerpo["description"] = descripcion
    elif tabla.get("description"):
        cuerpo["description"] = tabla["description"]
    if dominio:
        cuerpo["domain"] = dominio
    if tag_tabla:
        cuerpo["tags"] = [_etiqueta(tag_tabla, "Classification")]
    _llamar(peticion, "PUT", "/v1/tables", token, cuerpo)


def publicar_negocio(peticion, token: str, servicio: str) -> None:
    """Glosario, dominios, origen.* y descripciones. Idempotente (PUT)."""
    _llamar(
        peticion,
        "PUT",
        "/v1/glossaries",
        token,
        {
            "name": GLOSARIO,
            "description": (
                "Términos de negocio de Olist alineados con el contrato "
                "semántico. OpenMetadata no alimenta el prompt (D-06, D-33)."
            ),
        },
    )
    for termino in TERMINOS:
        cuerpo = {
            "name": termino["nombre"],
            "description": termino["definicion"],
            "glossary": GLOSARIO,
        }
        if termino["sinonimos"]:
            cuerpo["synonyms"] = list(termino["sinonimos"])
        _llamar(peticion, "PUT", "/v1/glossaryTerms", token, cuerpo)
    _llamar(
        peticion,
        "PUT",
        "/v1/classifications",
        token,
        {
            "name": CLASIFICACION,
            "description": (
                "Procedencia del dato (R-05). El grano vive en el dominio, "
                "no en un tag por columna. Una OBT real puede tener columnas "
                "simuladas (logística)."
            ),
            "mutuallyExclusive": False,
        },
    )
    for nombre, desc in (
        ("real", "Dato transaccional real de Olist."),
        (
            "simulado",
            "Dato simulado (clickstream o eventos logísticos). No usar como "
            "evidencia transaccional (R-05).",
        ),
    ):
        _llamar(
            peticion,
            "PUT",
            "/v1/tags",
            token,
            {
                "name": nombre,
                "description": desc,
                "classification": CLASIFICACION,
            },
        )
    for dominio in DOMINIOS:
        _llamar(
            peticion,
            "PUT",
            "/v1/domains",
            token,
            {
                "name": dominio["nombre"],
                "displayName": dominio["nombre"],
                "description": dominio["descripcion"],
                "domainType": "Consumer-aligned",
            },
        )
    enlaces = _enlaces()
    simuladas = _simulado_por_tabla()
    dominio_de = {d["tabla"]: d["nombre"] for d in DOMINIOS}
    for nombre, tag in ORIGEN_TABLA.items():
        _anotar_tabla(
            peticion,
            token,
            servicio,
            nombre,
            descripcion=DESCRIPCION_OBT.get(nombre),
            dominio=dominio_de.get(nombre),
            tag_tabla=tag,
            glosario_cols=enlaces.get(nombre, {}),
            cols_simuladas=simuladas.get(nombre, set()),
            exigida=nombre.startswith("obt_"),
        )
