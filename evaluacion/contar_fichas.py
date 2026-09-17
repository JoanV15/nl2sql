"""Recuento real de fichas del prefijo vía /tokenize (D-37)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tfm_nlsql.runtime.cliente import contar_fichas  # noqa: E402
from tfm_nlsql.runtime.contrato import cargar_contrato  # noqa: E402


def main() -> int:
    prefijo, _, _ = cargar_contrato()
    n = contar_fichas(prefijo)
    print(n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
