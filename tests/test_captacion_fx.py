"""El tipo de referencia es 2018-10-17; otra fecha de la API se rechaza."""

import pytest

from tfm_nlsql.ingesta.captacion_fx import FECHA_REFERENCIA, parse_frankfurter


def test_parse_frankfurter_fecha_de_referencia() -> None:
    fila = parse_frankfurter(
        {"amount": 1.0, "base": "BRL", "date": "2018-10-17", "rates": {"EUR": 0.23207}}
    )
    assert fila["fecha"] == FECHA_REFERENCIA
    assert fila["eur_por_brl"] == 0.23207


def test_parse_frankfurter_rechaza_otra_fecha() -> None:
    with pytest.raises(ValueError, match="2018-10-17"):
        parse_frankfurter(
            {
                "amount": 1.0,
                "base": "BRL",
                "date": "2018-10-16",
                "rates": {"EUR": 0.23},
            }
        )
