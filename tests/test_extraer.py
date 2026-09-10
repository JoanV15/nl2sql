from tfm_nlsql.runtime.orquestador import extraer_salida, supuestos_de

_RUIDO = """```
SELECT COUNT(id_pedido) AS total_pedidos
FROM obt_pedidos;
```

Pregunta: ¿Cuántos clientes hemos atendido?
```
SELECT COUNT(DISTINCT id_cliente_persona) AS total_clientes
FROM obt_pedidos;
```
"""


def test_extrae_sql_pelado() -> None:
    sql, abs_ = extraer_salida("SELECT 1 FROM obt_pedidos")
    assert abs_ is None
    assert "SELECT 1" in sql


def test_extrae_abstencion() -> None:
    sql, abs_ = extraer_salida("ABSTENCION: no existe el coste del producto")
    assert sql is None
    assert abs_.startswith("ABSTENCION:")


def test_limpia_cercas() -> None:
    sql, abs_ = extraer_salida("```sql\nSELECT 1\n```")
    assert abs_ is None
    assert sql == "SELECT 1"


def test_corta_en_la_primera_sentencia_aunque_llegue_ruido() -> None:
    sql, abs_ = extraer_salida(_RUIDO)
    assert abs_ is None
    assert sql == "SELECT COUNT(id_pedido) AS total_pedidos\nFROM obt_pedidos"
    assert "clientes" not in sql


def test_cerca_sin_cierre_no_arranca_por_fence() -> None:
    sql, abs_ = extraer_salida(
        "```sql\nWITH x AS (SELECT 1 FROM obt_pedidos)\nSELECT * FROM x"
    )
    assert abs_ is None
    assert sql is not None
    assert not sql.startswith("```")
    assert sql.startswith("WITH")


def test_supuestos_de_comentario_inicial() -> None:
    sql = "-- supuesto: electronica = macro\nSELECT 1"
    assert supuestos_de(sql) == ["supuesto: electronica = macro"]
    assert supuestos_de(None) == []
