# Plantilla de redacción — Memoria TFM

Normativa: 20 caras de cuerpo. Secciones 1–7 obligatorias. Sección 8, anexos
sin límite de caras pero no sustituyen el argumento del cuerpo.

Cupo orientativo (repartir 20): §3 = 2, §4 = 2, §5 = 5, §6 = 6, §7 = 4,
resumen + palabras clave = 1. Si falta espacio, recorta §6 (detalle de
ingesta) hacia anexo, **nunca** §7.

---

## 1. Resumen (~½ cara)

Tres frases, no más:

1. Qué problema: stakeholders preguntan en lenguaje natural; el SQL generado
   no puede ejecutarse a ciegas sobre un lakehouse.
2. Qué se construye: plataforma gobernada (Bronze/Silver/Gold) + runtime
   NL-to-SQL local con contrato semántico estático, validador AST y
   evaluación por *execution accuracy*.
3. Resultado estrella: Nivel 1, mismo contrato, 7/18 (3B) frente a 13/18
   (7B); la adherencia a la regla de censo (D-48) pasa de 8 banderas
   espurias a 2. Caché de prefijo: prefill 98 s → <0,5 s.

## 2. Palabras clave

Propuesta: *NL-to-SQL, contrato semántico, lakehouse, DataOps, linaje,
evaluación de LLM, DuckDB, dbt, ejecución local*.

## 3. Introducción (~2 caras)

### 3.1 Contexto

Marketplace Olist (Brasil). Preguntas de negocio en castellano. Dato
histórico hasta 2018-10-17 (D-15). El núcleo transaccional no cubre
telemetría logística ni clickstream (C-02): de ahí la ingesta híbrida.

### 3.2 Objetivos

- Funcional: responder el catálogo de `Preguntas.md` con SQL validado.
- Técnico: demostrar DataOps, linaje y gobierno sobre un lakehouse, no
  solo un chatbot.
- Académico: cubrir el temario del máster sin teatro de herramientas.

### 3.3 Justificación

Negocio: autoservicio analítico con soberanía del dato (D-17, D-18).
Técnica: un LLM sin contrato alucina columnas; un contrato sin validador
es teatro. Interés: el hallazgo C-08 (el few-shot manda más que la prosa
en 3B) es publicable en una memoria de máster.

Fuentes: `FUENTE.md` §Identidad, D-05, D-11, D-19.

## 4. Metodología (~2 caras)

Núcleo y anillos (D-23). Hitos de `ROADMAP.md`. SQL de referencia
**antes** de observar el sistema (D-21, D-50). Fecha de D-50 (2026-09-09)
**antes** de la pasada del contrato 1.1: no se relajó la métrica a
posteriori.

Métrica: igualdad exacta de conjuntos de filas, no del texto SQL, no del
«ganador». Ablaciones previstas: contrato, tamaño 3B/7B, autocorrección.

Fuentes: D-21, D-23, D-50, D-52, `ROADMAP.md`.

## 5. Arquitectura (~5 caras)

### 5.1 Diagrama

Copiar el Mermaid de `ARQUITECTURA.md`. Frontera: Spark Bronze→Silver;
DuckDB Silver→Gold y consulta. Polars fuera (D-04). OpenMetadata fuera
del runtime (D-06).

### 5.2 Justificación de herramientas

Una frase por componente, siempre con la alternativa descartada (está en
cada D-xx). No listar el stack como escaparate.

### 5.3 Costes

Hardware propio + Azure for Students (D-28). Inferencia local, sin API
de pago. Presupuesto RAM real 6–7 GB (C-03), no 16. Disco: C-07.

### 5.4 DataOps

Git, dbt tests, Dagster (Hito 5), CI acotada (D-25). Linaje: dbt +
orquestador; OpenMetadata opcional y sacrificable.

## 6. Solución tecnológica (~6 caras)

### 6.1 Fuentes

Olist CSV (real). REST tipos de cambio, Kafka eventos, MongoDB reseñas,
clickstream simulado — todo **etiquetado** (R-05). D-26, D-27, D-32.

### 6.2 Preparación y capas

Landing + cuarentena (D-08). Delta Silver (D-10, D-31). Gold: cuatro OBT
con grano (D-11, D-43). Nombres en castellano (D-36). Reconciliación
D-14. Definiciones D-12, D-38, D-44, D-45, D-48.

### 6.3 Runtime NL-to-SQL

Camino de una pregunta: contrato → ChatML (D-47) → llama.cpp → extractor
→ validador AST (D-19) → `EXPLAIN` (C-06) → DuckDB solo lectura → traza
(D-22). Prefijo invariante (D-33, D-34). Un reintento (D-20).

### 6.4 Ética y legal

Dataset público. Modelo local: el dato no sale del equipo (D-18). SQL
inyectado se corta en el AST, no en el prompt.

## 7. Resultados y conclusiones (~4 caras)

Esta sección se escribe **con cifras de `FUENTE.md`**. Estructura:

1. Criterio de hecho del Hito 1: 18/18 SQL válido.
2. Tabla 3B vs 7B (D-52). Hipótesis C-08.
3. Fallos que se quedan: 5, 9, 10, 13, 15. La 15 acierta el mes y falla
   D-50 por una columna extra: decirlo así.
4. Latencia y caché (P-07, C-04, C-09). Prefijo 3.067 / umbral 3.200.
5. Limitaciones: grano de reseña (D-51), Olist no recurrente (C-05),
   7B y plataforma no coexisten (D-53, R-08).
6. Trabajo futuro: Hitos 3–6 según punto de corte del roadmap.
7. Conclusión: el sistema acierta cuando el modelo cabe en la gobernanza;
   el contrato no es magia.

## 8. Anexos (sin cupo de 20 caras)

A. Catálogo de preguntas y SQL de referencia.
B. Tablas completas P-07 (tres fechas).
C. DDL Gold / extracto del contrato.
D. Decisiones D-01…D-53 (o enlace al repo; no volcar 70 páginas).
E. Capturas Streamlit (cuando exista).
F. Reformulaciones de enunciado (pregunta 16 / D-51).

---

## Lo que no entra en el cuerpo

- El 0/18 por ChatML (C-10): una frase en metodología o anexo, no el
  titular de resultados.
- Discusiones de stack descartadas: una línea por D-xx, no tres páginas.
- Logs de agentes, prompts de Cursor, historial de commits salvo el
  SHA de la ablación si se cita reproducibilidad.
