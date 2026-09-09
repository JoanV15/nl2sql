# NL-to-SQL sobre un Lakehouse gobernado

Trabajo Fin de Máster. Plataforma de datos de extremo a extremo que ingiere por
lote y por flujo, gobierna el dato en capas y expone una capa analítica sobre la
que un modelo de lenguaje local traduce preguntas de negocio en castellano a SQL
validado y ejecutado de forma segura.

Dataset base: [Olist Brazilian E-Commerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).

## Estado

Hito 1 cerrado (2026-09-09). Nivel 1: 13/18 con Qwen2.5-Coder-7B; 7/18 con 3B.
Siguiente: Hito 2. Entrega 17 de septiembre de 2026. Ver `ROADMAP.md`.

## Documentación

| Documento | Contenido |
|---|---|
| [`HANDOFF.md`](HANDOFF.md) | Relevo para un agente nuevo: estado y primer encargo |
| [`ROADMAP.md`](ROADMAP.md) | Hitos, criterio de hecho y punto de corte |
| [`ARQUITECTURA.md`](ARQUITECTURA.md) | Arquitectura consolidada, componentes y fronteras de cómputo |
| [`DECISIONES.md`](DECISIONES.md) | Registro de decisiones (D-01 a D-53) |
| [`CONTRATO_SEMANTICO.md`](CONTRATO_SEMANTICO.md) | Prefijo del modelo. No editar `[PREFIJO]` a la ligera |
| [`Preguntas.md`](Preguntas.md) | Catálogo de evaluación |
| [`memoria/`](memoria/) | Fuente + plantilla para redactar la memoria |
| [`AGENTS.md`](AGENTS.md) | Instrucciones para agentes de código |

`DECISIONES.md` es la fuente de verdad. Si otro documento lo contradice, manda
el registro de decisiones.

## Resumen técnico

**Plataforma.** Cinco orígenes con formatos y protocolos distintos: ficheros
CSV, API REST, eventos por Kafka y una base documental. Zona de aterrizaje con
cuarentena, Bronze inmutable, Silver en Delta Lake y Gold en DuckDB. Spark
procesa de Bronze a Silver, en lote y en micro-lote; dbt sobre DuckDB modela de
Silver a Gold. Dagster orquesta, OpenMetadata cataloga fuera de línea y GitHub
Actions ejerce de puerta de calidad.

**Capa analítica.** Cuatro tablas denormalizadas con grano declarado, nombradas
en castellano. El renombrado en la frontera de Gold es la capa semántica.

**Runtime.** Qwen2.5-Coder 7B cuantizado (3B como ablación), servido por `llama.cpp` en CPU. El
contexto es un contrato semántico estático y versionado, no una recuperación
dinámica de metadatos: la medición de latencia sobre el hardware objetivo dio
17,5 segundos de procesamiento del prompt en frío frente a menos de uno con la
caché de prefijo caliente, y esa caché solo se reutiliza si el prefijo no
cambia. El SQL generado pasa por un validador de AST y se ejecuta en modo solo
lectura, con un único reintento de autocorrección.

**Evaluación.** Precisión de ejecución sobre 61 preguntas estratificadas por
dificultad, con estudio de ablación sobre el contrato semántico, el tamaño de
modelo y el bucle de autocorrección. Un bloque específico mide la capacidad de
**no** responder cuando el dato no existe.

## Ejecución local

Requiere Docker Compose. La plataforma de datos y el runtime de inferencia se
levantan en perfiles separados y no conviven: el presupuesto real de memoria es
de 6 a 7 GB.

Instrucciones detalladas: pendientes de la primera iteración de implementación.
