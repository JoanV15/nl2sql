# Perfil consulta (D-62). El 7B no entra en la imagen.
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md CONTRATO_SEMANTICO.md /app/
COPY src /app/src
RUN pip install --no-cache-dir .

EXPOSE 8501
ENV TFM_GOLD_PATH=/datos/gold/gold.duckdb
ENV TFM_LLAMA_URL=http://host.docker.internal:8080
CMD ["streamlit", "run", "src/tfm_nlsql/interfaz/app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
