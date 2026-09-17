"""El prefijo se extrae de los bloques [PREFIJO] y no arrastra las notas."""

from tfm_nlsql.runtime.contrato import cargar_contrato
from tfm_nlsql.runtime.prompt import construir_prompt, prefijo_invariante


def test_prefijo_contiene_las_cuatro_tablas_del_contrato() -> None:
    prefijo, cat, version = cargar_contrato()
    assert version == "1.2"
    for t in ("obt_pedidos", "obt_lineas_pedido", "obt_vendedores", "obt_embudo_web"):
        assert f"CREATE TABLE {t}" in prefijo
        assert t in cat
    assert len(cat["obt_pedidos"]) == 32
    assert "Notas de diseño" not in prefijo
    assert "Control de presupuesto" not in prefijo
    assert "2018-10-17" in prefijo


def test_prefijo_incluye_patrones_n2n3_d63() -> None:
    prefijo, _, version = cargar_contrato()
    assert version == "1.2"
    assert "GROUP BY categoria_producto" in prefijo
    assert "CAST('2018-10-17' AS DATE)" in prefijo
    assert "INTERVAL 3 MONTH" in prefijo
    assert "CURRENT_DATE" not in prefijo
    assert "now()" not in prefijo
    assert "¿Qué categorías de producto vendieron más unidades en 2016 que en 2015?" in prefijo
    assert "¿Cuál es el ticket medio de los últimos tres meses?" in prefijo
    assert "¿Qué categorías crecieron más en 2018 respecto a 2017?" not in prefijo
    assert "today" not in prefijo


def test_pregunta_va_despues_del_prefijo_chatml() -> None:
    contrato, _, _ = cargar_contrato()
    cabeza = prefijo_invariante()
    prompt = construir_prompt("¿Cuánto facturamos en 2018?")
    assert cabeza.startswith("<|im_start|>system\n")
    assert cabeza.endswith("<|im_start|>user\n")
    assert contrato in cabeza
    assert prompt.startswith(cabeza)
    assert prompt.endswith("<|im_end|>\n<|im_start|>assistant\n")
    assert prompt[len(cabeza) :].startswith("Pregunta: ¿Cuánto facturamos en 2018?\n")


def test_dos_preguntas_comparten_cabeza_byte_a_byte() -> None:
    a = construir_prompt("¿Cuántos pedidos hemos hecho en total?")
    b = construir_prompt("¿Cuál es el ticket medio de un pedido?")
    cabeza = prefijo_invariante()
    assert a.startswith(cabeza)
    assert b.startswith(cabeza)
    assert a[: len(cabeza)] == b[: len(cabeza)]
