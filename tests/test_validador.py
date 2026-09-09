"""El validador opera sobre el AST (D-19), no sobre palabras clave."""

from __future__ import annotations

import pytest

from tfm_nlsql.runtime.contrato import cargar_contrato
from tfm_nlsql.runtime.validador import (
    ErrorValidacion,
    inyectar_limite,
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


def test_rechaza_obt_embudo_web() -> None:
    rechaza("SELECT * FROM obt_embudo_web", "obt_embudo_web")


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


def test_inyecta_limit() -> None:
    sql = inyectar_limite("SELECT id_pedido FROM obt_pedidos")
    assert "LIMIT 1000" in sql.upper().replace(" ", "") or "LIMIT 1000" in sql.upper()


def test_respeta_limit_menor() -> None:
    sql = inyectar_limite("SELECT id_pedido FROM obt_pedidos LIMIT 5")
    assert "5" in sql
