"""El SQL de referencia del Nivel 1 debe pasar el validador (no el modelo)."""

from pathlib import Path

from tfm_nlsql.runtime.contrato import cargar_contrato
from tfm_nlsql.runtime.validador import inyectar_limite, validar_politica

_, COLUMNAS, _ = cargar_contrato()
SQL_DIR = Path(__file__).resolve().parents[1] / "evaluacion" / "sql_referencia"


def test_las_18_referencia_pasan_politica() -> None:
    for n in range(1, 19):
        sql = (SQL_DIR / f"{n:02d}.sql").read_text(encoding="utf-8")
        validar_politica(inyectar_limite(sql), COLUMNAS)
