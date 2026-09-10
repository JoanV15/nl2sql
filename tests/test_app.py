from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "src" / "tfm_nlsql" / "interfaz" / "app.py"


def test_fecha_visible_sin_clic_y_botones_de_lanzar() -> None:
    at = AppTest.from_file(str(APP))
    at.run()
    assert at.exception is None or not list(at.exception)
    assert any("2018-10-17" in i.value for i in at.info)
    etiquetas = [b.label for b in at.button]
    assert "Nivel 1: pedidos totales" in etiquetas
    assert "57: margen de beneficio" in etiquetas
    assert "Consultar" in etiquetas
