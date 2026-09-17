# Roadmap — TFM NL-to-SQL

**Entrega: 17 de septiembre de 2026.** Documento vivo: se actualiza al cerrar
cada hito.

Deriva del orden de anillos de D-23. Cada hito es una rebanada que deja el
sistema en un estado demostrable: si el calendario se rompe en cualquier punto,
lo construido hasta ahí se defiende solo.

## Cómo se usa

Un hito no se da por cerrado porque el código compile, sino cuando se
cumple su **criterio de hecho** y se ha hecho su **revisión**. Mientras un hito
esté abierto, no se empieza el siguiente.

Al cerrar cada hito, escribe el apartado correspondiente de la memoria. No lo
dejes para el final: `DECISIONES.md` ya contiene la justificación redactada, y
trasladarla en caliente cuesta una hora por hito y tres días al final.

---

## Hito 1 · Rebanada vertical *(cerrado 2026-08-12)*

**Objetivo.** Responder de extremo a extremo las 18 preguntas del Nivel 1 con el
modelo local, y medir la precisión.

**Alcance.** Estructura del proyecto (D-40, D-41). Gold con `obt_pedidos`,
`obt_lineas_pedido` y `obt_vendedores` desde los CSV con dbt-duckdb (D-43).
Runtime: constructor de prompt, cliente llama.cpp, validador AST, ejecutor en
solo lectura y traza (D-19, D-22). Interfaz de línea de comandos. SQL de
referencia y arnés de evaluación.

**Criterio de hecho.** Un comando acepta una pregunta y devuelve resultado y
SQL. Las 18 se ejecutan sin fallo del validador. Informe de precisión. Recuento
del contrato con `/tokenize` anotado.

**Cierre.** Contrato 1.1. Validador: 18/18 SQL válido. Precisión Nivel 1 con
el 7B (D-53): **13/18**. Ablación 3B: 7/18. Prefijo: 3.067 fichas. Commits
relevantes: `1332290`, `e0847f0`, `259b62f`. Los cinco KO restantes (5, 9,
10, 13, 15) son resultado experimental, no trabajo pendiente del Hito 1.

**Tu revisión.** Ejecuta tres preguntas a mano y lee el SQL generado. Abre la
traza y comprueba que registra lo que dice D-22. Verifica que el test de
reconciliación de D-14 pasa y que no está trucado.

---

## Hito 2 · Cobertura completa de preguntas e interfaz *(cerrado 2026-08-20)*

**Objetivo.** Cubrir los 46 casos que dependen solo de dato real, más el bloque
de abstención.

**Alcance.** SQL de referencia para Niveles 2 y 3 y para las preguntas 56 a 63.
Bucle de autocorrección con un solo reintento (D-20, D-35). Streamlit (D-39),
mostrando fecha de referencia, SQL generado y supuestos declarados.

**Criterio de hecho.** Precisión desglosada por nivel, nunca agregada. Las
preguntas 57 y 58 se abstienen; la 63 la rechaza el validador, no el modelo.

**Cierre.** Precisión 7B: Nivel 2 **5/16**, Nivel 3 **1/11**, abstención
**5/8**. Streamlit: `uv run tfm-nlsql-ui`. Commits: `75875af`, `beee57d`,
`886a379`, `d37c143`, `965971b`. La 63: el modelo se abstiene (bloque 6); el
validador rechaza el DELETE de referencia. Los KO no son trabajo pendiente.

**Tu revisión.** Aquí es donde el trabajo se gana o se pierde. Comprueba que la
abstención no es el modelo diciendo "no sé", sino la política del bloque 6 del
contrato funcionando. Y que la 62 resuelve el grano sin doble conteo.

---

## Hito 3 · Lakehouse real *(cerrado 2026-08-26)*

**Objetivo.** Sustituir la lectura directa de CSV por el recorrido gobernado.

**Alcance.** Landing con cuarentena (D-08). Spark de Bronze a Silver. Silver en
Delta Lake (D-10) con política de retención (D-31).

**Criterio de hecho.** Un fichero corrupto acaba en cuarentena y no en Bronze.
Silver es reprocesable e idempotente. Gold se reconstruye desde Silver sin
tocar los CSV.

**Cierre.** Cuarentena D-08. Silver Delta overwrite idempotente (**99441**
pedidos). Gold desde Silver con `delta_scan`; D-14 pasa. Gold ya no lee
Landing. pytest `tests/`: **84 passed**. Commits: `14269a6`, `efc9175`,
`b58ec61`. El atajo D-23 (CSV de Landing) queda sustituido.

**Tu revisión.** Rompe un CSV a propósito y comprueba que el sistema lo aísla
en lugar de tragárselo.

---

## Hito 4 · Ingesta híbrida *(cerrado 2026-08-29)*

**Objetivo.** Cerrar los orígenes que justifican la arquitectura (C-02, D-27).

**Alcance.** Kafka en KRaft con Spark Structured Streaming (D-09). Generadores
de eventos logísticos y clickstream, referenciando identificadores reales.
`obt_embudo_web`. Tipos de cambio por API. Base documental en MongoDB (D-32).

**Criterio de hecho.** Las preguntas 47, 48, 50, 51, 53, 54 y 55 entran en la
evaluación. La lista blanca del validador pasa a cuatro tablas.

**Cierre.** 47/48 Kafka logístico; 50/51 `obt_embudo_web`; 53–55 funnel+FX;
validador 4 tablas; Mongo D-32; R-05 en Streamlit. Commits: `66e4f66`,
`42d5a6b`, `8b6e800`, `6a0387a`, `8c108a7`. Kafka y Mongo corren como
binarios locales (WSL sin Docker); Compose queda para el Hito 5.

**Tu revisión.** Que todo lo simulado esté etiquetado como tal en la interfaz y
en la memoria (R-05). Es lo primero que preguntará el tribunal.

---

## Hito 5 · DataOps *(cerrado 2026-09-02)*

**Objetivo.** Orquestación e integración continua.

**Alcance.** Dagster con activos definidos por software (D-03). GitHub Actions
con linter, tests, `dbt build` sobre muestra y la comprobación de deriva entre
el contrato y el catálogo real de DuckDB (D-25).

**Criterio de hecho.** Un solo comando reconstruye la plataforma entera. La CI
falla si el contrato y el esquema divergen.

**Cierre.** `uv run --extra spark --extra dagster --extra mongo tfm-nlsql-plataforma`
reconstruye Bronze → Silver → reseñas-Mongo → Gold. CI `calidad.yml`: ruff,
pytest `-m "not spark"`, dbt sobre muestra y deriva D-25. Commits: `a3b9123`,
`b9a7530`. Compose sigue fuera: WSL sin Docker.

---

## Hito 6 · Gobierno y nube *(cerrado 2026-09-05)*

**Alcance.** OpenMetadata en perfil aislado (D-06). Almacenamiento en ADLS Gen2
(D-07, D-28).

**Criterio de hecho.** Ruta configurable hacia ADLS sin depender de ella para
el resto del sistema. OpenMetadata, si entra, fuera del runtime.

**Cierre.** ADLS: `e0ea3d8` + `bc0c867`. D-59: Landing, Bronze y cuarentena
siempre locales; solo `TFM_SILVER_PATH` admite abfs; Gold es DuckDB local
(D-07). Sin cuenta inventada. OpenMetadata y Compose **entran el 5 de
septiembre (D-62)** como perfiles excluyentes: catálogo de linaje dbt en
`localhost:8585` y UI de consulta contenida; el 7B sigue en el anfitrión.

---

## Hito 7 · Resultados y entrega

**Alcance.** Estudio de ablación de D-21: contrato semántico, tamaño de modelo
3B frente a 7B, y bucle de autocorrección. Memoria completa. Vídeo.

**Criterio de hecho.** Memoria entregada con la curva de degradación por nivel
de dificultad y las tres ablaciones.

**Calendario de cierre (septiembre de 2026).** El producto queda cerrado la
primera semana de septiembre (Hitos 1–6, D-60 a D-63). El resto del mes es
memoria y vídeo (ZIP del campus, no este repositorio) y versionado público
para la entrega del 17 a las 23:59.

---

## Punto de corte

Si a finales de agosto no está cerrado el Hito 4, se sacrifica en este orden y
se declara en la memoria como decisión de alcance, no como carencia:

1. **ADLS Gen2.** D-07 ya prevé el plan B local. Se documenta la ruta
   configurable como demostración de que el diseño no depende de la nube.
2. **OpenMetadata.** D-06 lo tiene fuera del runtime, así que su ausencia no
   afecta al sistema. El linaje sigue existiendo en dbt y Dagster.
3. **MongoDB.** Quinto origen; la amplitud de D-27 ya queda demostrada con
   CSV, API REST y Kafka.
4. **`obt_embudo_web` y el clickstream.** Retira las preguntas 50 y 51 del
   conjunto de evaluación, como el propio catálogo prevé.

Lo que **no** se sacrifica bajo ningún supuesto: la evaluación con SQL de
referencia, el bloque de abstención, y la memoria.

---

## Calendario

| Periodo | Qué |
|---|---|
| 28 jun – 14 jul | Diseño: catálogo de preguntas, arquitectura, `DECISIONES.md` |
| 15 – 31 jul | Pausa |
| 1 – 12 ago | Hito 1 · Rebanada vertical |
| 13 – 20 ago | Hito 2 · Cobertura de preguntas e interfaz |
| 21 – 26 ago | Hito 3 · Lakehouse real |
| 27 – 31 ago | Hito 4 · Ingesta híbrida |
| 1 – 3 sep | Hito 5 · DataOps |
| 4 – 5 sep | Hito 6 · Gobierno, Compose y OpenMetadata |
| 6 – 7 sep | D-60 a D-63 y cierre de producto |
| 8 – 17 sep | Memoria, vídeo, GitHub y versionado |
| 17 sep | Entrega |
