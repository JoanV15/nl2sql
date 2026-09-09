"""Especificación ejecutable de D-45: pago principal y sequential de desempate."""

import duckdb


def test_pago_principal_mayor_importe_desempate_sequential() -> None:
    con = duckdb.connect(":memory:")
    con.execute(
        """
        CREATE TABLE pagos (
          order_id VARCHAR,
          payment_sequential INTEGER,
          payment_type VARCHAR,
          payment_installments INTEGER,
          payment_value DOUBLE
        );
        INSERT INTO pagos VALUES
          ('A', 1, 'voucher', 1, 20),
          ('A', 2, 'credit_card', 3, 80),
          ('B', 1, 'boleto', 1, 50),
          ('B', 2, 'credit_card', 2, 50);
        """
    )
    filas = con.execute(
        """
        SELECT
          order_id,
          payment_type AS tipo_pago_principal,
          payment_installments AS num_plazos
        FROM pagos
        QUALIFY ROW_NUMBER() OVER (
          PARTITION BY order_id
          ORDER BY payment_value DESC, payment_sequential ASC
        ) = 1
        ORDER BY order_id
        """
    ).fetchall()
    assert filas == [("A", "credit_card", 3), ("B", "boleto", 1)]
