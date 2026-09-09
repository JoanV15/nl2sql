"""Aterriza los CSV de Olist en datos/landing/ con kagglehub (sin pandas)."""

from __future__ import annotations

import shutil
from pathlib import Path

from tfm_nlsql.ingesta.construir_gold import CSV_OBLIGATORIOS
from tfm_nlsql.rutas import LANDING

DATASET = "olistbr/brazilian-ecommerce"


def aterrizar() -> Path:
    import kagglehub

    origen = Path(kagglehub.dataset_download(DATASET))
    LANDING.mkdir(parents=True, exist_ok=True)
    csvs = list(origen.glob("*.csv"))
    if not csvs:
        csvs = list(origen.rglob("*.csv"))
    for csv in csvs:
        shutil.copy2(csv, LANDING / csv.name)
    faltan = [n for n in CSV_OBLIGATORIOS if not (LANDING / n).is_file()]
    if faltan:
        raise SystemExit(
            f"La descarga de {DATASET} no trajo: {', '.join(faltan)}. "
            f"Origen: {origen}"
        )
    return LANDING


def main() -> int:
    dest = aterrizar()
    presentes = sorted(p.name for p in dest.glob("*.csv"))
    print(f"Landing: {dest}")
    print("CSV:", ", ".join(presentes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
