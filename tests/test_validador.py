"""El validador opera sobre el AST (D-19), no sobre palabras clave."""

from __future__ import annotations

import pytest

from tfm_nlsql.runtime.contrato import cargar_contrato
from tfm_nlsql.runtime.validador import (
    ErrorValidacion,
    inyectar_limite,
    tablas_gold_citadas,
    validar_politica,
)

_, COLUMNAS, _ = cargar_contrato()


def acepta(sql: str) -> None:
    validar_politica(inyectar_limite(sql), COLUMNAS)


def rechaza(sql: str, trozo: str) -> None:
    with pytest.raises(ErrorValidacion) as ctx:
        validar_politica(inyectar_limite(sql), COLUMNAS)
    assert trozo.lower() in str(ctx.value).lower()


def test_acepta_select_simple() -> None:
    acepta("SELECT COUNT(*) AS n FROM obt_pedidos")


def test_acepta_with_y_subconsulta() -> None:
    acepta(
        """
        WITH t AS (
          SELECT estado_cliente, COUNT(*) AS n
          FROM obt_pedidos
          GROUP BY estado_cliente
        )
        SELECT * FROM t WHERE n > (
          SELECT AVG(n) FROM t
        )
        """
    )


def test_acepta_autoagregacion() -> None:
    acepta(
        """
        SELECT id_pedido, SUM(importe_articulos) AS s
        FROM obt_lineas_pedido
        GROUP BY id_pedido
        """
    )


def test_rechaza_insert() -> None:
    with pytest.raises(ErrorValidacion, match="SELECT"):
        validar_politica("INSERT INTO obt_pedidos (id_pedido) VALUES ('x')", COLUMNAS)


def test_rechaza_delete() -> None:
    with pytest.raises(ErrorValidacion, match="SELECT"):
        validar_politica("DELETE FROM obt_pedidos", COLUMNAS)


def test_rechaza_drop() -> None:
    with pytest.raises(ErrorValidacion, match="SELECT"):
        validar_politica("DROP TABLE obt_pedidos", COLUMNAS)


def test_rechaza_sentencias_multiples() -> None:
    with pytest.raises(ErrorValidacion, match="una sentencia"):
        validar_politica(
            "SELECT 1 FROM obt_pedidos; SELECT 2 FROM obt_pedidos", COLUMNAS
        )


def test_acepta_obt_embudo_web() -> None:
    acepta(
        "SELECT categoria_producto, SUM(num_carritos_abandonados) AS n "
        "FROM obt_embudo_web GROUP BY categoria_producto"
    )


def test_rechaza_columna_inexistente() -> None:
    rechaza("SELECT no_existe FROM obt_pedidos", "no_existe")


def test_rechaza_columna_de_otra_tabla_cualificada() -> None:
    rechaza("SELECT obt_pedidos.id_vendedor FROM obt_pedidos", "id_vendedor")


def test_rechaza_funcion_de_tabla() -> None:
    with pytest.raises(ErrorValidacion, match="función de tabla|tabla no permitida"):
        validar_politica(
            "SELECT * FROM read_csv_auto('datos/landing/olist_orders_dataset.csv')",
            COLUMNAS,
        )


def test_rechaza_coma_sin_condicion() -> None:
    rechaza(
        "SELECT COUNT(*) AS n FROM obt_pedidos, obt_vendedores",
        "producto cartesiano",
    )


def test_rechaza_cross_join_y_join_pelado() -> None:
    rechaza(
        "SELECT COUNT(*) AS n FROM obt_pedidos CROSS JOIN obt_vendedores",
        "producto cartesiano",
    )
    rechaza(
        "SELECT COUNT(*) AS n FROM obt_pedidos JOIN obt_vendedores",
        "producto cartesiano",
    )


def test_rechaza_el_cartesiano_de_la_traza_149() -> None:
    """0,003 % de clientes recurrentes frente al 3,12 % real: D-35 trunco el ON."""
    rechaza(
        """
        WITH clientes AS (
          SELECT id_cliente_persona, COUNT(*) AS num_pedidos
          FROM obt_pedidos GROUP BY id_cliente_persona
        ), recurrentes AS (
          SELECT COUNT(*) AS num_clientes_recurrentes
          FROM clientes WHERE num_pedidos > 1
        )
        SELECT (SELECT num_clientes_recurrentes FROM recurrentes) * 100.0 / COUNT(*)
                 AS porcentaje_clientes_recurrentes,
               AVG(importe_articulos) AS clv_promedio
        FROM clientes, obt_pedidos
        """,
        "producto cartesiano",
    )


def test_acepta_join_con_condicion() -> None:
    """El cruce no está prohibido: lo que se rechaza es el cruce sin condición."""
    acepta(
        """
        SELECT p.id_pedido
        FROM obt_pedidos AS p
        JOIN obt_lineas_pedido AS l ON p.id_pedido = l.id_pedido
        """
    )
    acepta(
        """
        WITH totales AS (
          SELECT id_pedido, SUM(importe_articulos) AS s
          FROM obt_lineas_pedido GROUP BY id_pedido
        )
        SELECT id_pedido, s
        FROM totales
        JOIN obt_pedidos USING (id_pedido)
        """
    )


def test_acepta_columnas_cualificadas_por_el_alias_de_un_cte() -> None:
    """`FROM totales AS t` con `t.columna`: el alias es un nombre derivado."""
    acepta(
        """
        WITH totales AS (
          SELECT id_pedido, SUM(importe_articulos) AS s
          FROM obt_lineas_pedido GROUP BY id_pedido
        )
        SELECT t.id_pedido, t.s
        FROM totales AS t
        JOIN obt_pedidos AS p ON t.id_pedido = p.id_pedido
        """
    )


def test_el_alias_de_un_cte_no_abre_la_lista_blanca() -> None:
    """Aliasar un CTE no legitima una tabla física fuera de la lista."""
    rechaza("SELECT c.x FROM clientes AS c", "tabla no permitida")


def test_acepta_subconsulta_escalar_en_vez_de_cruce() -> None:
    """La alternativa que el validador deja abierta para un porcentaje."""
    acepta(
        """
        SELECT COUNT(*) * 100.0 / (SELECT COUNT(*) FROM obt_pedidos) AS pct
        FROM obt_pedidos
        WHERE estado_pedido = 'canceled'
        """
    )


def test_inyecta_limit() -> None:
    sql = inyectar_limite("SELECT id_pedido FROM obt_pedidos")
    assert "LIMIT 1000" in sql.upper().replace(" ", "") or "LIMIT 1000" in sql.upper()


def test_respeta_limit_menor() -> None:
    sql = inyectar_limite("SELECT id_pedido FROM obt_pedidos LIMIT 5")
    assert "5" in sql


def test_tablas_gold_citadas_solo_lista_blanca() -> None:
    assert tablas_gold_citadas("SELECT 1 FROM obt_pedidos") == ["obt_pedidos"]
    assert tablas_gold_citadas(
        "SELECT * FROM obt_pedidos JOIN obt_lineas_pedido USING (id_pedido)"
    ) == ["obt_pedidos", "obt_lineas_pedido"]
    assert "clientes" not in tablas_gold_citadas("SELECT 1 FROM clientes")
    assert tablas_gold_citadas(
        "WITH t AS (SELECT 1 AS n FROM obt_pedidos) SELECT n FROM t"
    ) == ["obt_pedidos"]
