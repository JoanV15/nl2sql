"""El SQL de referencia SELECT/WITH debe pasar el validador (no el modelo)."""

from pathlib import Path

import pytest

from tfm_nlsql.runtime.contrato import cargar_contrato
from tfm_nlsql.runtime.validador import (
    ErrorValidacion,
    inyectar_limite,
    validar_politica,
)

_, COLUMNAS, _ = cargar_contrato()
SQL_DIR = Path(__file__).resolve().parents[1] / "evaluacion" / "sql_referencia"


def _sql_select() -> list[Path]:
    out = []
    for p in sorted(SQL_DIR.glob("*.sql")):
        t = p.read_text(encoding="utf-8").strip().upper()
        if t.startswith("ABSTENCION:") or t.startswith("DELETE"):
            continue
        out.append(p)
    return out


@pytest.mark.parametrize("ruta", _sql_select(), ids=lambda p: p.stem)
def test_referencia_select_pasa_politica(ruta: Path) -> None:
    sql = ruta.read_text(encoding="utf-8")
    validar_politica(inyectar_limite(sql), COLUMNAS)


def test_la_63_la_rechaza_el_validador() -> None:
    sql = (SQL_DIR / "63.sql").read_text(encoding="utf-8")
    with pytest.raises(ErrorValidacion, match="solo se permiten SELECT y WITH"):
        validar_politica(inyectar_limite(sql), COLUMNAS)
