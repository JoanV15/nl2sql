from pathlib import Path

from tfm_nlsql.plataforma.om_ingest import receta_con_token
from tfm_nlsql.runtime import orquestador

RAIZ = Path(__file__).resolve().parents[1]


def test_receta_dbt_no_lleva_placeholder_tras_sustituir() -> None:
    texto = receta_con_token("token-de-prueba")
    assert "${OM_JWT}" not in texto
    assert "token-de-prueba" in texto
    assert "tfm_nlsql_gold" in texto
    assert "openmetadata-server:8585" in texto


def test_compose_consulta_no_empaqueta_el_gguf() -> None:
    compose = (RAIZ / "docker-compose.yml").read_text(encoding="utf-8")
    assert 'profiles: ["consulta"]' in compose
    assert "host.docker.internal:8080" in compose
    assert ".gguf" not in compose
    dockerfile = (RAIZ / "docker" / "consulta" / "Dockerfile").read_text(
        encoding="utf-8"
    )
    assert "streamlit" in dockerfile
    assert ".gguf" not in dockerfile


def test_catalogo_no_ocupa_el_puerto_del_7b() -> None:
    compose = (RAIZ / "docker" / "openmetadata" / "docker-compose.yml").read_text(
        encoding="utf-8"
    )
    assert '"18080:8080"' in compose
    assert '"8080:8080"' not in compose
    assert "openmetadata-server" in compose


def test_orquestador_no_importa_openmetadata() -> None:
    fuente = Path(orquestador.__file__).read_text(encoding="utf-8")
    assert "openmetadata" not in fuente.lower()
    assert "om_ingest" not in fuente
    assert "om_negocio" not in fuente


def test_ingest_usa_dbt_del_path() -> None:
    from tfm_nlsql.plataforma import om_ingest

    fuente = Path(om_ingest.__file__).read_text(encoding="utf-8")
    assert 'which("dbt")' in fuente
    assert '"-m"' not in fuente
    assert "/v1/tables" in fuente
    assert "/v1/lineage" in fuente
    assert "publicar_negocio" in fuente
    assert om_ingest.SERVICIO == "tfm_nlsql_gold"
