# Roadmap — TFM NL-to-SQL

**Entrega: 17 de septiembre de 2026.** Documento vivo: se actualiza al cerrar
cada hito.

Deriva del orden de anillos de D-23. Cada hito es una rebanada que deja el
sistema en un estado demostrable: si el calendario se rompe en cualquier punto,
lo construido hasta ahí se defiende solo.

## Cómo se usa

Un hito no se da por cerrado porque el agente diga que terminó, sino cuando se
cumple su **criterio de hecho** y tú has hecho su **revisión**. Mientras un hito
esté abierto, no se empieza el siguiente.

Al cerrar cada hito, escribe el apartado correspondiente de la memoria. No lo
dejes para el final: `DECISIONES.md` ya contiene la justificación redactada, y
trasladarla en caliente cuesta una hora por hito y tres días al final.

---

## Hito 1 · Rebanada vertical *(en curso)*

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

**Tu revisión.** Ejecuta tres preguntas a mano y lee el SQL generado. Abre la
traza y comprueba que registra lo que dice D-22. Verifica que el test de
reconciliación de D-14 pasa y que no está trucado.

---

## Hito 2 · Cobertura completa de preguntas e interfaz

**Objetivo.** Cubrir los 46 casos que dependen solo de dato real, más el bloque
de abstención.

**Alcance.** SQL de referencia para Niveles 2 y 3 y para las preguntas 56 a 63.
Bucle de autocorrección con un solo reintento (D-20, D-35). Streamlit (D-39),
mostrando fecha de referencia, SQL generado y supuestos declarados.

**Criterio de hecho.** Precisión desglosada por nivel, nunca agregada. Las
preguntas 57 y 58 se abstienen; la 63 la rechaza el validador, no el modelo.

**Tu revisión.** Aquí es donde el trabajo se gana o se pierde. Comprueba que la
abstención no es el modelo diciendo "no sé", sino la política del bloque 6 del
contrato funcionando. Y que la 62 resuelve el grano sin doble conteo.

---

## Hito 3 · Lakehouse real

**Objetivo.** Sustituir la lectura directa de CSV por el recorrido gobernado.

**Alcance.** Landing con cuarentena (D-08). Spark de Bronze a Silver. Silver en
Delta Lake (D-10) con política de retención (D-31).

**Criterio de hecho.** Un fichero corrupto acaba en cuarentena y no en Bronze.
Silver es reprocesable e idempotente. Gold se reconstruye desde Silver sin
tocar los CSV.

**Tu revisión.** Rompe un CSV a propósito y comprueba que el sistema lo aísla
en lugar de tragárselo.

---

## Hito 4 · Ingesta híbrida

**Objetivo.** Cerrar los orígenes que justifican la arquitectura (C-02, D-27).

**Alcance.** Kafka en KRaft con Spark Structured Streaming (D-09). Generadores
de eventos logísticos y clickstream, referenciando identificadores reales.
`obt_embudo_web`. Tipos de cambio por API. Base documental en MongoDB (D-32).

**Criterio de hecho.** Las preguntas 47, 48, 50, 51, 53, 54 y 55 entran en la
evaluación. La lista blanca del validador pasa a cuatro tablas.

**Tu revisión.** Que todo lo simulado esté etiquetado como tal en la interfaz y
en la memoria (R-05). Es lo primero que preguntará el tribunal.

---

## Hito 5 · DataOps

**Objetivo.** Orquestación e integración continua.

**Alcance.** Dagster con activos definidos por software (D-03). GitHub Actions
con linter, tests, `dbt build` sobre muestra y la comprobación de deriva entre
el contrato y el catálogo real de DuckDB (D-25).

**Criterio de hecho.** Un solo comando reconstruye la plataforma entera. La CI
falla si el contrato y el esquema divergen.

---

## Hito 6 · Gobierno y nube *(sacrificable)*

**Alcance.** OpenMetadata en perfil aislado (D-06). Almacenamiento en ADLS Gen2
(D-07, D-28).

Primero de la lista de recortes. Ver punto de corte.

---

## Hito 7 · Resultados y entrega

**Alcance.** Estudio de ablación de D-21: contrato semántico, tamaño de modelo
3B frente a 7B, y bucle de autocorrección. Memoria completa. Vídeo.

**Criterio de hecho.** Memoria entregada con la curva de degradación por nivel
de dificultad y las tres ablaciones.

**Reserva innegociable: del 14 al 16 de septiembre.** No se toca código en esos
días salvo para corregir algo que rompa la demo.

---

## Punto de corte

Si el 12 de septiembre no está cerrado el Hito 4, se sacrifica en este orden y
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

| Días | Hito |
|---|---|
| 8–9 sep | 1 · Rebanada vertical |
| 9–10 sep | 2 · Cobertura de preguntas e interfaz |
| 10–11 sep | 3 · Lakehouse real |
| 11–12 sep | 4 · Ingesta híbrida |
| 12–13 sep | 5 · DataOps |
| 13 sep | 6 · Gobierno y nube *(sacrificable)* |
| 14–16 sep | 7 · Ablaciones, memoria y vídeo |
| 17 sep | Entrega |
