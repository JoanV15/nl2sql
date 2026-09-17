"""ADLS detrás de TFM_*_PATH (D-07). Local por defecto; sin cuenta no se inventa."""

from __future__ import annotations

from pathlib import Path

import pytest

from tfm_nlsql.plataforma.adls import (
    cuenta_de,
    exigir_adls,
    join_capa,
    uri_capa,
)
from tfm_nlsql.rutas import RAIZ, es_abfs

URI = "abfss://olist@tfmcuenta.dfs.core.windows.net/silver"


def test_default_local_no_es_abfs() -> None:
    bronze = RAIZ / "datos" / "bronze"
    assert not es_abfs(str(bronze))
    assert uri_capa("TFM_SILVER_PATH", bronze, {}) == str(bronze)


def test_uri_abfs_no_se_envuelve_en_path() -> None:
    got = uri_capa("TFM_SILVER_PATH", Path("/tmp/silver"), {"TFM_SILVER_PATH": URI})
    assert got == URI
    assert es_abfs(got)
    assert "abfss://" in got
    assert cuenta_de(got) == "tfmcuenta"


def test_join_capa_local_igual_que_path(tmp_path: Path) -> None:
    assert join_capa(tmp_path, "olist_orders_dataset") == str(
        tmp_path / "olist_orders_dataset"
    )


def test_join_capa_abfs_sin_spark() -> None:
    assert join_capa(URI, "olist_orders_dataset") == URI + "/olist_orders_dataset"


def test_para_sin_credenciales() -> None:
    with pytest.raises(SystemExit, match="PARA") as ctx:
        exigir_adls({"TFM_SILVER_PATH": URI})
    assert "AZURE_STORAGE_ACCOUNT_KEY" in str(ctx.value)


def test_para_sin_cuenta_en_uri() -> None:
    with pytest.raises(SystemExit, match="PARA") as ctx:
        exigir_adls({"TFM_SILVER_PATH": "abfss://solo-contenedor"})
    assert "inventa" in str(ctx.value).lower() or "cuenta" in str(ctx.value).lower()


def test_para_gold_abfs() -> None:
    with pytest.raises(SystemExit, match="PARA"):
        exigir_adls({"TFM_GOLD_PATH": URI})


def test_resolver_gold_abfs_para() -> None:
    from tfm_nlsql.rutas import resolver_gold

    with pytest.raises(SystemExit, match="no admite abfs"):
        resolver_gold(URI)


def test_para_landing_abfs() -> None:
    with pytest.raises(SystemExit, match="Landing"):
        exigir_adls(
            {
                "TFM_LANDING_PATH": URI,
                "AZURE_STORAGE_ACCOUNT_KEY": "x",
            }
        )


def test_para_sin_extra_azure() -> None:
    try:
        import azure.storage.filedatalake  # noqa: F401
    except ImportError:
        pass
    else:
        pytest.skip("extra azure instalado")
    with pytest.raises(SystemExit, match="extra azure"):
        exigir_adls(
            {
                "TFM_SILVER_PATH": URI,
                "AZURE_STORAGE_ACCOUNT_KEY": "x",
            }
        )


def test_local_no_exige_nada() -> None:
    exigir_adls({})
    exigir_adls({"TFM_SILVER_PATH": "/tmp/silver"})


def test_gold_honra_tfm_silver_path_abfs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TFM_SILVER_PATH", URI)
    from tfm_nlsql.ingesta.construir_gold import ruta_silver_para_dbt

    assert ruta_silver_para_dbt() == URI


def test_construir_gold_para_si_abfs_sin_clave(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TFM_SILVER_PATH", URI)
    monkeypatch.delenv("AZURE_STORAGE_ACCOUNT_KEY", raising=False)
    monkeypatch.delenv("AZURE_STORAGE_CONNECTION_STRING", raising=False)
    from tfm_nlsql.ingesta.construir_gold import main

    with pytest.raises(SystemExit, match="PARA"):
        main()


def test_construir_gold_no_pisa_abfs_con_resolve() -> None:
    texto = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "tfm_nlsql"
        / "ingesta"
        / "construir_gold.py"
    ).read_text(encoding="utf-8")
    assert "SILVER.resolve()" not in texto
    assert 'env["TFM_SILVER_PATH"] = silver' in texto
