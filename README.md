# NL-to-SQL sobre un lakehouse gobernado

Trabajo Fin de Máster (UCM, Big Data & Data Engineering). Plataforma Medallion
sobre [Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) y un
runtime local que traduce preguntas en castellano a SQL DuckDB validado.

Los datos (`datos/`) y los pesos del modelo (`.gguf`) no van en git. Sin
reconstruir Gold y sin `llama-server` no hay chat.

## Cómo está hecho

Dos sistemas que **no se encienden a la vez** (el 7B, Spark y OpenMetadata no
caben en ~6–7 GB de RAM útil):

1. **Plataforma.** CSV de Olist, funnel de marketing, API de tipos de cambio,
   Kafka (logística y clickstream simulados) y Mongo (reseñas: canal documental,
   contenido del CSV). Landing con cuarentena → Bronze inmutable → Silver en
   Delta (Spark, lote y micro-lote) → Gold en DuckDB (dbt): cuatro tablas
   desnormalizadas en castellano, con grano declarado. Dagster materializa el
   grafo. OpenMetadata (perfil aparte) enseña linaje y glosario; **no** entra en
   el *prompt*.
2. **Runtime.** Qwen2.5-Coder-7B-Instruct Q4_K_M en CPU (`llama.cpp`,
   `127.0.0.1:8080`). El único contexto del modelo es
   [`CONTRATO_SEMANTICO.md`](CONTRATO_SEMANTICO.md) (prefijo fijo: así funciona
   la caché). Un validador AST deja pasar solo `SELECT`/`WITH` sobre Gold;
   DuckDB ejecuta en solo lectura. Si el dato no existe, el sistema se abstiene.

Fecha de negocio: **17 de octubre de 2018**. Facturación =
`importe_articulos` en BRL. ADLS es una URI opcional de Silver; este trabajo no
sube datos a Azure.

**Hitos 1–2**, contrato 1.1, `n_predict` 120 (no mezclar con 256 ni con el
contrato 1.2):

| Bloque | 7B | 3B |
|---|---|---|
| Nivel 1 | 13/18 | 7/18 |
| Nivel 2 | 5/16 | — |
| Nivel 3 | 1/11 | — |
| Abstención | 5/8 | — |

Métrica: igualdad exacta de conjuntos de filas, por nivel. El 3B es ablación;
el sistema es el 7B. Detalle en [`DECISIONES.md`](DECISIONES.md) y
[`evaluacion/resultados/`](evaluacion/resultados/).

| Documento | Qué |
|---|---|
| [`ARQUITECTURA.md`](ARQUITECTURA.md) | Diagramas y fronteras Spark / DuckDB |
| [`DECISIONES.md`](DECISIONES.md) | Registro D-01…D-63 |
| [`CONTRATO_SEMANTICO.md`](CONTRATO_SEMANTICO.md) | Prefijo del modelo |
| [`Preguntas.md`](Preguntas.md) | Catálogo (49 y 52 descartadas; 43 sin SQL) |
| [`ROADMAP.md`](ROADMAP.md) | Hitos y calendario |

---

## Tutorial: de cero a una pregunta en el portátil

Entorno de referencia: **WSL2 Ubuntu x86_64** (o Linux). El Mongo empaquetado
es `mongodb-linux-x86_64-ubuntu2204`. En Windows nativo no uses el
`tfm-nlsql-mongo` de este repo.

Hay **tres perfiles**. Nunca los tres a la vez:

| Perfil | Qué enciendes | Para qué |
|---|---|---|
| Plataforma | Spark, Kafka, Mongo. **7B apagado** | Construir Gold |
| Consulta | 7B + UI Streamlit. Kafka/Mongo/OM apagados | Preguntar |
| Catálogo | OpenMetadata en Docker. **7B apagado** | Ver linaje |

### 0. Hardware y disco

- RAM: 16 GB en el anfitrión ayudan; WSL limitado a **8 GB** y **6 CPU** es el
  techo con el que se diseñó el sistema.
- Disco: deja **≥25 GB** libres (Olist ~1 GB, GGUF ~4,7 GB, Kafka/Mongo en
  caché, imágenes Docker de OpenMetadata ~6 GB, JARs de Spark).
- Primera pregunta en frío: del orden de **uno o dos minutos** (prefill). Las
  siguientes, con caché caliente, bajan de un segundo de prefill. **Una
  pregunta cada vez** (`n_ctx` 4096).

En PowerShell del anfitrión Windows, `%UserProfile%\.wslconfig`:

```ini
[wsl2]
memory=8GB
processors=6
swap=2GB
```

Después, `wsl --shutdown`. Eso tumba cualquier `llama-server` que estuviera
dentro de WSL: habrá que relanzarlo.

### 1. Herramientas del sistema

Dentro de WSL:

```bash
sudo apt update
sudo apt install -y git curl build-essential cmake python3-venv openjdk-17-jdk
java -version    # 17 o superior (Spark 4 / Kafka)
```

[uv](https://docs.astral.sh/uv/):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
uv --version
```

Docker Desktop con integración WSL2 solo hace falta para la UI en contenedor o
para OpenMetadata. El chat también corre con `uv run tfm-nlsql-ui`.

### 2. Clonar e instalar Python

```bash
git clone https://github.com/JoanV15/nl2sql.git
cd nl2sql
uv sync --extra dev --extra landing --extra spark --extra mongo --extra dagster
```

Python ≥ 3.12. Comprueba el arnés sin Spark ni modelo:

```bash
uv run ruff check src tests evaluacion
uv run pytest -m "not spark" -q
```

### 3. Dataset Olist (Landing)

Hace falta una cuenta de [Kaggle](https://www.kaggle.com/settings) y un token
API. Crea `~/.kaggle/kaggle.json` (chmod 600) o exporta `KAGGLE_USERNAME` y
`KAGGLE_KEY`.

```bash
uv run tfm-nlsql-aterrizar
ls datos/landing/*.csv
```

Deben aparecer, entre otros, `olist_orders_dataset.csv` e
`olist_order_reviews_dataset.csv`.

### 4. Construir el lakehouse (7B apagado)

Nada puede escuchar en **8080**. Kafka y Mongo se quedan en terminales
propias.

```bash
ss -ltn | grep 8080 && echo "PARA el 7B / lo que ocupe 8080" || echo "8080 libre"
```

**Terminal A — Kafka** (descarga Apache Kafka 3.9.1 a `~/.cache/tfm-nlsql/` la
primera vez):

```bash
cd ~/ruta/nl2sql
uv run tfm-nlsql-kafka
# deja esta terminal abierta; Ctrl-C para parar
```

**Terminal B — Mongo** (binario Ubuntu 22.04):

```bash
cd ~/ruta/nl2sql
uv run tfm-nlsql-mongo
# deja esta terminal abierta
```

**Terminal C — Bronze → Silver → reseñas Mongo → Gold:**

```bash
cd ~/ruta/nl2sql
uv run tfm-nlsql-plataforma
```

La primera pasada de Spark baja JARs y puede tardar varios minutos. Gold
**exige** que las reseñas hayan pasado por Mongo (`_from_mongo` en Silver). Si
Mongo no escuchaba, el asset de reseñas se salta y Gold se niega.

Comprueba:

```bash
test -f datos/gold/gold.duckdb && echo "Gold OK" || echo "falta Gold"
```

### 5. Fuentes extra (Hito 4): Kafka, funnel y euros

Siguen con el 7B apagado y con Kafka/Mongo arriba. Publican 3.000 eventos
simulados (ids reales de Olist), drenan a Silver y reconstruyen Gold.

```bash
uv run tfm-nlsql-logistica
uv run tfm-nlsql-clickstream
uv run tfm-nlsql-captacion-fx    # Kaggle funnel + API Frankfurter (BRL→EUR, 2018-10-17)
```

Sin este paso, las preguntas de logística, embudo y facturación en euros no
tienen columnas que rellenar. El núcleo transaccional (pedidos, censo) ya
está en Gold tras el paso 4.

### 6. Apagar plataforma antes de preguntar

```bash
ss -ltn | grep -E ':9092|:27017'
```

Si salen esos puertos:

```bash
~/.cache/tfm-nlsql/kafka_2.13-3.9.1/bin/kafka-server-stop.sh
~/.cache/tfm-nlsql/mongodb-linux-x86_64-ubuntu2204-7.0.14/bin/mongod \
  --dbpath datos/mongo/db --shutdown
```

### 7. Modelo 7B y llama.cpp

Pesos (~4,7 GB). El nombre que espera este README:

```bash
mkdir -p ~/modelos
uvx --from 'huggingface_hub[cli]' huggingface-cli download \
  bartowski/Qwen2.5-Coder-7B-Instruct-GGUF \
  Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf \
  --local-dir ~/modelos
ls -lh ~/modelos/Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf
```

Servidor (no va en la imagen Docker; se sirve en el anfitrión):

```bash
git clone https://github.com/ggml-org/llama.cpp.git ~/llama.cpp
cmake -S ~/llama.cpp -B ~/llama.cpp/build
cmake --build ~/llama.cpp/build --config Release -j "$(nproc)" --target llama-server
```

**Terminal D — dejar corriendo:**

```bash
~/llama.cpp/build/bin/llama-server \
  -m ~/modelos/Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf \
  -c 4096 -t 6 --host 127.0.0.1 --port 8080
```

Espera a que imprima que escucha en 8080. El 3B (ablación, ~1,8 GB) no
coexiste con el 7B; no lo arranques a la vez.

### 8. Preguntar (perfil consulta)

Con Gold en `datos/gold/gold.duckdb` y el 7B en 8080.

Sin Docker:

```bash
uv run tfm-nlsql-ui
# http://localhost:8501
```

O una pregunta suelta (la primera calienta la caché del contrato):

```bash
uv run tfm-nlsql "¿Cuántos pedidos hemos hecho en total?"
```

Con Docker (el contenedor monta Gold en solo lectura y llama al 7B del host):

```bash
docker compose --profile consulta up --build
# http://localhost:8501
```

En la UI: fecha 2018-10-17, aviso de orígenes simulados, SQL a la vista. Prueba
el atajo de censo y una abstención (`¿Cuál es nuestro margen de beneficio?`).
Censo esperado: **99.441** pedidos.

### 9. Catálogo OpenMetadata (opcional, 7B apagado)

Para RAM: para `llama-server`, la UI y Kafka/Mongo.

```bash
docker compose -f docker/openmetadata/docker-compose.yml up -d
# espera a http://localhost:8585  (admin@open-metadata.org / admin)
docker stop openmetadata_ingestion    # Airflow ~1,6 GiB; no hace falta para el ingest
uv run tfm-nlsql-om
```

Airflow del *compose* sale en `http://localhost:18080` (no uses 8080: es el
del 7B). El conector oficial rechaza dbt 1.12; `tfm-nlsql-om` publica por REST
(PUT idempotente). El runtime **no** consulta este catálogo.

Glosario: <http://localhost:8585/glossary/Olist>.

Al acabar:

```bash
docker compose -f docker/openmetadata/docker-compose.yml down
```

### 10. Evaluación (opcional)

Gold construido. `--solo-referencia` no llama al modelo:

```bash
uv run python evaluacion/arnes.py --solo-referencia
```

Con el 7B en 8080, una pasada completa tarda **horas** en CPU. Los informes
canónicos ya están en `evaluacion/resultados/`. CI:

```bash
uv run python -m tfm_nlsql.plataforma.muestra   # dbt sobre muestra, no el Olist entero
```

---

## Configuración

Copia [`.env.example`](.env.example) si hace falta. Por defecto todo vive en
`datos/` (fuera de git).

| Variable | Por defecto | Notas |
|---|---|---|
| `TFM_LANDING_PATH` / `TFM_BRONZE_PATH` / `TFM_CUARENTENA_PATH` | `datos/…` | Siempre locales |
| `TFM_SILVER_PATH` | `datos/silver` | Única que admite `abfss://` (no ejercida aquí) |
| `TFM_GOLD_PATH` | `datos/gold/gold.duckdb` | DuckDB local; `abfs` se rechaza |
| `TFM_LLAMA_URL` | `http://127.0.0.1:8080` | En el *compose* de consulta: `host.docker.internal:8080` |
| `TFM_TRAZA_PATH` | `trazas/consultas.sqlite` | Pregunta, SQL, veredicto, latencia |
| `TFM_N_EVENTOS` / `TFM_N_CLICKSTREAM` | `3000` | |
| `SPARK_DRIVER_MEMORY` | `2g` | |

Si DuckDB no puede `delta_scan` sobre `abfs`, el proceso **para**; no cae al
disco en silencio.

## Si algo falla

| Síntoma | Qué mirar |
|---|---|
| `llama-server no responde` | Terminal D; `ss -ltn \| grep 8080` |
| Plataforma / Kafka / Mongo se niegan | Algo ocupa 8080: para el 7B |
| Gold: reseñas no vienen de Mongo | Terminal B arriba; `uv run tfm-nlsql-resenas` y otra vez `tfm-nlsql-gold` |
| Kafka no escucha | Terminal A; `uv run tfm-nlsql-kafka` |
| `kagglehub` 401 | Token en `~/.kaggle/kaggle.json` |
| WSL sin memoria / OOM | `.wslconfig`, cierra OM y Spark antes del 7B |
| Prefill de ~2 min cada vez | El contrato debe ser idéntico; no mezcles OM en el *prompt* |
| Primera pregunta interminable | Normal en frío; espera el prefill |
| Producto cartesiano 0,003 % | El validador vigente lo rechaza; no es un KPI |

Comandos de parada útil:

```bash
docker compose --profile consulta down
docker compose -f docker/openmetadata/docker-compose.yml down
# 7B: Ctrl-C en la terminal de llama-server
```
