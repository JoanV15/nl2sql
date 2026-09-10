# Fuente de verdad para la memoria

**Fecha de cierre de este volcado: 2026-09-09.** Todo lo posterior se añade
al final, no se reescribe lo ya medido. Si `DECISIONES.md` y este fichero
discrepan en una cifra, prevalece el JSON de evaluación o la tabla de D-52.

Este documento no es la memoria. Es el material con el que un agente, usando
`PLANTILLA.md`, debe redactarla sin inventar.

---

## Identidad

- **Qué:** TFM de Data Engineering. Lakehouse gobernado + NL-to-SQL local
  sobre Olist. Preguntas de negocio en castellano → SQL DuckDB validado.
- **Quién:** Joan (alumno). Tutores: Jorge Centeno, Alberto González.
- **Repo:** `git@github.com:JoanV15/nl2sql.git`. Rama de trabajo: `v1`.
- **Entrega:** 17 de septiembre de 2026. Vídeo 3–5 min. ZIP con nombre y
  apellidos unidos por guiones bajos.
- **Equipo:** AMD Ryzen 5 6600H (6C/12T), ~12,7 GB RAM usables en Windows,
  WSL2 limitado a 8 GB (`memory=8192MB`) y 6 CPU (antes 4). Inferencia CPU.
- **Modelo del sistema (D-53):** `Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf`
  (~4,7 GB) vía `llama-server` `127.0.0.1:8080`, `-c 4096 -t 6`.
- **Brazo de ablación:** mismo stack, 3B Q4_K_M (~1,8 GB). No coexisten.

---

## Estado del repositorio (2026-09-09 noche)

| Commit | Qué |
|---|---|
| `15d8451` | Documentación arquitectónica inicial |
| `1332290` | Hito 1 código: Gold 3 OBT, runtime, arnés |
| `e0847f0` | Contrato 1.1 (D-48 a D-51) |
| `259b62f` | Ablación 3B/7B (D-52), arnés con `--etiqueta` |

Gold: `datos/gold/gold.duckdb` (fuera de git). Landing CSV en
`datos/landing/` (fuera de git). Informes `nivel1_3b.json` y
`nivel1_7b.json` deben versionarse (excepción en `.gitignore`).

**Hito 1 cerrado.** Hito 2 no empezado: falta triaje de preguntas 19–55
(P-09) y SQL de referencia de niveles 2–3. Streamlit no existe.

**Contrato:** versión 1.1. Prefijo **3.067 fichas** (antes 2.890). Umbral
de alerta D-46: ~3.200. Ventana 4.096.

---

## Números que se pueden citar

### Precisión Nivel 1 (execution accuracy, D-50)

| Pasada | Modelo | Contrato | Aciertos | Precisión | Espurios `es_venta_valida` |
|---|---|---|---|---|---|
| Tras ChatML, antes 1.1 | 3B | 1.0 | 6/18 | 0,333 | (no instrumentado) |
| Contrato 1.1 | 3B | 1.1 | 7/18 | 0,389 | 8 |
| Ablación etiquetada | 3B | 1.1 | **7/18** | 0,389 | **8** (1,6,7,8,9,10,14,17) |
| Ablación etiquetada | 7B | 1.1 | **13/18** | 0,722 | **2** (9, 10) |

Metadatos D-52 (medias del arnés):

| | 3B | 7B |
|---|---|---|
| Prefill (fichas/s) | 27,88 | 12,77 |
| Generación (fichas/s) | 9,63 | 4,78 |
| Latencia media/pregunta | 4,17 s | 8,80 s |
| `n_ctx` / hilos | 4096 / 6 | 4096 / 6 |
| Versión contrato | 1.1 | 1.1 |

- 7B acierta y 3B no: **1, 6, 7, 8, 14, 17** (censo; el 7B quita la bandera).
- Regresiones 3B OK → 7B KO: **ninguna**.
- KO en ambos: **5, 9, 10, 13, 15**.
- 7B OK que el 3B de 1.1 también: 2, 3, 4, 11, 12, 16, 18.

Detalle de los cinco KO comunes (interpretación, no para «arreglar» en Hito 1):

| # | Qué hace el 7B | Lectura |
|---|---|---|
| 5 | Agrupa `macro_categoria` en vez de `categoria_producto`; no devuelve las 74 | Mapeo semántico / ranking sin top-N |
| 9 | Media de `dias_entrega` **con** `es_venta_valida` | D-48 no aplicada (plazo medio) |
| 10 | Método de pago más usado **con** bandera; ganador `credit_card` igual | D-48 no aplicada; D-50 falla por recuento |
| 13 | `importe_pagado` (o antes `importe_total`) en vez de `importe_articulos` | Bloque 3 no seguido |
| 15 | Acierta el mes (`DATE_TRUNC`) pero añade `RANK()` | Falla D-50 por columnas extra; la respuesta de negocio es correcta |

Validador: **18/18** SQL analizable y ejecutable en las pasadas post-D-47.

### Pregunta 16 y grano (D-51)

Enunciado original pedía reseñas de 1 estrella. Referencia contaba pedidos
con `nota_resena = 1` (media, D-38) y los llamaba `num_resenas`.

| Medida | Valor |
|---|---|
| Pedidos con media = 1 (referencia vieja) | 11.316 |
| Reseñas reales `review_score = 1` en el CSV | 11.424 |
| Pedidos con más de una reseña | 547 |
| Pedidos con media no entera | 123 |
| Filas CSV reseñas | 99.224 |

Enunciado vigente: «¿Cuántos pedidos recibieron una valoración media de una
estrella?». Ausencia declarada: reseñas individuales no contables a este grano.

### Prefill / caché (P-07)

No mezclar filas de distintas fechas (C-09).

**2026-09-01, Windows nativo, prefijo sintético ~2.540 fichas, 3B.**
Prefill frío 17,5 s (~145 fichas/s). Caliente ~0,07–1,3 s. Generación ~15 fichas/s.

**2026-09-07, WSL2, 4 CPU, prefijo real 2.890, 3B, ChatML aún no.**
Frío: 62,0 s (46,8 fichas/s). Caliente: 0,18–0,44 s. Generación 5,5 fichas/s.

**2026-09-09, WSL2, 6 CPU, prefijo 1.1 = 3.067, 3B, ChatML.**
Frío: 98,3 s (31,5 fichas/s). Caliente: 0,09–0,47 s. Generación ~10 fichas/s.

Lo que se afirma siempre: la caché reduce el prefill >99 %. D-34 paga el frío.

### Hardware y WSL

- `.wslconfig`: `memory=8192MB`, `processors=6` (fue 4), `swap=2048MB`.
- Subir de 4 a 6 CPU subió la generación del 3B de ~5,5 a ~9,6 fichas/s.
- Disco WSL (2026-09-09): ~54 GB usados / 1007 GB en `/home` — el cuello
  C-07 era el disco Windows (~51 GB libres entonces); actualizar si cambia.

---

## Hallazgos (mapa a la memoria)

| Id | Hallazgo | Dónde va |
|---|---|---|
| C-01 | Cuatro OBT, no una | §5, §6 Gold |
| C-02 | Huecos de Olist justifican streaming | §3, §6 fuentes |
| C-03 | 6–7 GB reales, no 16 | §5 costes |
| C-04 | Caché de prefijo es requisito | §5, §7 latencia |
| C-05 | Olist no es recurrente (~3 % repeat) | §7 limitaciones |
| C-06 | `EXPLAIN` = binding, no coste | §6 runtime |
| C-07 | Disco tan restrictivo como RAM | §5, recorte ADLS |
| C-08 | Few-shot > prosa en 3B; 7B cumple D-48 casi | **§7 titular** |
| C-09 | No comparar latencias entre OS/CPU | §7, anexo P-07 |
| C-10 | 0/18 fue ChatML | §4 o anexo, no titular |
| C-11 | El neto 6→7 ocultó regresión de la #1 | §4 metodología |

### Narrativa corta de C-08 (usar casi literal)

Se escribió en el contrato que el censo no filtra por venta válida (D-48).
El modelo de 3B ignoró la regla: 8 de 18 consultas llevaban la bandera
donde no tocaba. El few-shot enseñaba `es_venta_valida` y un año en dos
de tres ejemplos SQL. Añadir un ejemplo de censo sin bandera (D-49) no
bastó. El mismo contrato, mismo arnés, modelo 7B: 13/18 y 2 banderas
espurias, sin regresiones. Conclusión: la gobernanza por prosa escala
con la capacidad de seguir instrucciones; no sustituye al validador, y
el tamaño del modelo es parte del diseño, no un extra de última hora.

---

## Decisiones que el redactor no debe reabrir

D-01 DuckDB · D-02 dbt · D-03 Dagster · D-04 sin Polars · D-05 sin
LlamaIndex/LangChain · D-06 OpenMetadata fuera del runtime · D-11 cuatro
OBT · D-12 facturación = `importe_articulos` · D-17 LLM local · D-19
seguridad en AST · D-21 evaluación estratificada · D-33 contrato estático
· D-39 Streamlit · D-50 igualdad exacta de conjuntos · D-53 7B de sistema.

Lista completa: `DECISIONES.md`. Cada D tiene alternativa descartada:
eso es el material de «justificación de herramientas».

---

## Frases para el tribunal (ensayo)

- ¿Por qué no una estrella? Granos heterogéneos (C-01); el LLM no hace JOIN
  entre OBT a propósito.
- ¿Por qué no GPT-4? Soberanía (D-18) y coste; cloud queda como punto de
  curva, no como sistema.
- ¿Por qué local y no 100 % en Azure? RAM y disco del alumno; ruta
  configurable (D-07); plan B local ya previsto.
- ¿El 72 % no es bajo? Nivel 1 con 3B era 39 %; el salto es el resultado.
  Cinco fallos se dejan porque D-50 no se relaja. Un 18/18 en el propio
  test parecería amañado.
- ¿Dato simulado? Etiquetado (R-05). Resultados de negocio sobre Olist real.
- ¿SQL injection? AST + read_only + sin acceso externo + LIMIT 1000 + timeout.

---

## Lo que aún no está medido (no inventar)

- Precisión niveles 2 y 3.
- Ablación «con/sin contrato» y «con/sin reintento» (D-21; Hito 7).
- Modelo frontera en la nube (punto 3 de la curva D-29).
- Streamlit, Dagster, Kafka, MongoDB, ADLS, OpenMetadata: no existen aún.
- Coste Azure real: 0 € si no se ha provisionado ADLS.

---

## Cómo debe liderar el alumno (para el agente de código)

No aceptar «continúa». Cada encargo: un hito o un paso, criterio de hecho,
límite de lo que no tocar, «para y pregunta» si hay definición de negocio.
Revisar informes buscando **regresiones**, no solo el saldo. Las definiciones
(D-12, D-44, D-48) las cierra el alumno en `DECISIONES.md` antes del SQL.

---

## Encargo Hito 2 (primera mitad) — listo para pegar

Trabajas en un TFM. Modelo activo: Qwen2.5-Coder-7B. Rama `v1`.
Lee `HANDOFF.md` si acabas de arrancar.

**Paso 1. Triaje de alcance.** Recorre las preguntas 19 a 55 de
`Preguntas.md` y clasifícalas en tres grupos: las respondibles hoy con
`obt_pedidos`, `obt_lineas_pedido` y `obt_vendedores`; las que necesitan
`obt_embudo_web` u otros orígenes que llegan en el Hito 4; y las que no
son respondibles con ningún dato previsto y por tanto deben acabar en
abstención. Dame el reparto con una línea de motivo por pregunta antes
de escribir nada.

**Paso 2. SQL de referencia.** Solo para el primer grupo, y para el
bloque de abstención, las preguntas 56 a 63. Cada consulta debe
apoyarse en las definiciones canónicas de los bloques 3 y 4 del
contrato. Si al escribir una referencia detectas que el contrato no fija
una definición que la consulta necesita, no la inventes: anótala y sigue.

**Paso 3. Autoverificación.** Por cada referencia, ejecútala y
comprueba grano, alias y plausibilidad del número. Entrega por cada
consulta el número y una frase de qué mide exactamente.

**Paso 4. Parar.** No evalúes con el modelo. Las referencias las reviso yo.

**Límites.** No toques el contrato ni las preguntas del Nivel 1. No hagas
Streamlit. No amplíes la lista blanca del validador a `obt_embudo_web`.

**Registro.** El triaje del paso 1 se registra como decisión de alcance
del Hito 2. Commit y push a `origin/v1`.

---

## Hito 2 cerrado (2026-09-10)

Precisión 7B (`evaluacion/resultados/hito2_7b.json`, SHA `886a379` /
`d37c143`): Nivel 2 **5/16**, Nivel 3 **1/11**, abstención **5/8**. 57 y
58 se abstienen. 63: el modelo se abstiene (bloque 6); el validador
rechaza el DELETE de referencia. 62: grano correcto (`SUM(importe_total)`
en `obt_pedidos`); D-50 falla porque el generado omite `es_venta_valida`.
D-35 (`n_predict` 120) trunca las WITH de 27, 36, 40 y 41. Streamlit
existe: `uv run tfm-nlsql-ui`. P-09 resuelta → D-54. Los KO no son
trabajo pendiente.
