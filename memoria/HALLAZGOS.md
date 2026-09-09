# Hallazgos y mediciones

Registro empírico del proyecto. Complementa a `DECISIONES.md`: allí está **qué
se decidió y por qué**; aquí, **qué se midió y qué se aprendió al ejecutarlo**.

Cada entrada lleva la fecha, las condiciones exactas de medida y la sección de
la memoria que alimenta. Un dato sin sus condiciones no es reproducible y no
debe entrar en la memoria.

**Para el agente redactor.** Este fichero es la materia prima de la sección 7.
No inventes cifras ni redondees a favor. Si necesitas un número que no está
aquí, decláralo como pendiente de medir en lugar de estimarlo.

---

## Cronología de la evaluación del Nivel 1

Las 18 preguntas del Nivel 1, misma Gold, mismo arnés de *execution accuracy*
con igualdad exacta de conjuntos (D-50).

| Fecha | Modelo | Contrato | Cambio introducido | Aciertos |
|---|---|---|---|---|
| 08-09 tarde | 3B | 1.0 | Primera pasada, completación cruda | **0/18** |
| 08-09 18:00 | 3B | 1.0 | Plantilla ChatML (D-47) | **6/18** |
| 09-09 14:05 | 3B | 1.1 | D-48 a D-51 | **7/18** |
| 09-09 15:25 | 7B | 1.1 | Solo cambia el modelo | **13/18** |

La progresión no es monótona por pregunta: entre la segunda y la tercera
pasada se ganaron la 11 y la 16 y **se perdió la 1**, que pasó a añadir un
filtro que no le correspondía. Debe reportarse la regresión, no solo el saldo.

---

## H-01 · Un modelo de instrucciones usado como modelo base rinde cero

**Fecha:** 08-09. **Sección:** 6 y 7.

La primera evaluación completa dio 0 aciertos de 18, con las dieciocho
preguntas fallando con el mismo error de análisis sintáctico. El SQL generado
era correcto en varios casos, pero venía envuelto en vallas de markdown y
seguido de respuestas a preguntas que nadie había formulado.

Causa: el prompt se enviaba como texto plano al *endpoint* de completación,
sin la plantilla ChatML que Qwen2.5-Coder-Instruct espera, sin marca de inicio
de respuesta y con secuencias de parada que ese modo nunca emite. El modelo no
estaba desobedeciendo: estaba continuando un documento.

**Lo aprendido.** El fallo no estaba en el modelo ni en el contrato, sino en
el borde de integración. Una precisión de cero no significa que el enfoque no
funcione; obliga a inspeccionar la salida en bruto antes que cualquier otra
cosa. Resuelto en D-47.

---

## H-02 · Los ejemplos pesan más que las reglas en prosa

**Fecha:** 09-09. **Sección:** 7. **Es el hallazgo central del trabajo.**

D-48 estableció por escrito, en el bloque 4 del contrato, que las preguntas de
censo no deben filtrar por `es_venta_valida`. Tras incorporarla, el modelo de
3B siguió aplicando la bandera en **8 de las 11 consultas fallidas**, incluida
una contradicción lógica: `WHERE es_venta_valida AND estado_pedido =
'canceled'`, que devuelve cero por construcción.

La causa está en el bloque 7: de los tres ejemplos resueltos con SQL, dos
llevan `es_venta_valida` y un filtro de año. El modelo generaliza el patrón de
los ejemplos por encima de la regla declarativa, que además compite contra un
bloque 4 de 490 fichas.

**Lo aprendido.** En un contrato semántico, los ejemplos no son ilustración
sino especificación implícita, y una regla en prosa que los contradiga pierde.
Añadir un tercer ejemplo sin la bandera no bastó: cambió la proporción de dos
sobre dos a dos sobre tres, y el comportamiento apenas se movió.

---

## H-03 · La adherencia al contrato depende del tamaño del modelo

**Fecha:** 09-09. **Sección:** 7. **Ablación principal (D-21, D-52).**

Contrato, preguntas, SQL de referencia, hardware y arnés idénticos. Única
variable: el modelo.

| | Qwen2.5-Coder-3B | Qwen2.5-Coder-7B |
|---|---|---|
| Cuantización | Q4_K_M | Q4_K_M |
| Precisión Nivel 1 | 7/18 (38,9 %) | **13/18 (72,2 %)** |
| Consultas con `es_venta_valida` espurio | 8 | **2** |
| Prefill | 27,9 fichas/s | 12,8 fichas/s |
| Generación | 9,6 fichas/s | 4,8 fichas/s |
| Latencia media por pregunta | 4,2 s | 8,8 s |

Condiciones: WSL2, 6 hilos, `n_ctx` 4096, contrato 1.1 de 3.067 fichas,
CPU AMD Ryzen 5 6600H, sin GPU. Ficheros `evaluacion/resultados/nivel1_3b.json`
y `nivel1_7b.json`, ambos con metadatos incrustados.

**Sin regresiones:** ninguna pregunta que acertara el 3B falla con el 7B. Las
seis que cambian de veredicto (1, 6, 7, 8, 14, 17) son exactamente las de
censo con bandera espuria, lo que confirma el mecanismo de H-02.

**Lo aprendido.** Duplicar el tamaño del modelo casi duplica la precisión y
reduce a la cuarta parte los incumplimientos del contrato, al coste de
multiplicar por 2,1 la latencia. La gobernanza declarativa no es gratuita:
requiere una capacidad mínima de seguimiento de instrucciones por debajo de la
cual el contrato se escribe pero no se cumple.

---

## H-04 · Una consulta de referencia mal planteada corrompe la métrica en silencio

**Fecha:** 09-09. **Sección:** 4 y 7.

La referencia de la pregunta 16, «¿cuántas reseñas de una estrella hemos
recibido?», era `COUNT(*) FROM obt_pedidos WHERE nota_resena = 1` con el alias
`num_resenas`. Pero D-38 definió `nota_resena` como la **media** de las reseñas
del pedido, de modo que esa consulta cuenta pedidos cuya media vale exactamente
uno y los etiqueta como reseñas.

| Medida | Valor |
|---|---|
| Lo que contaba la referencia | 11.316 |
| Reseñas de una estrella reales en el origen | 11.424 |
| Pedidos con más de una reseña | 547 |
| Pedidos con nota media no entera | 123 |

**Lo aprendido.** El conjunto de referencia es tan susceptible de error como el
sistema evaluado, y sus fallos no se manifiestan como fallos: el sistema
"acierta" contra una verdad equivocada. Una decisión de modelado aparentemente
inocua —promediar reseñas al subir de grano— dejó una pregunta del catálogo sin
respuesta posible. Resuelto en D-51 reformulando la pregunta al grano real y
declarando la ausencia en el bloque 5.

---

## H-05 · La asignación de recursos del virtualizador altera las medidas de inferencia

**Fecha:** 08-09. **Sección:** 5 y 7, y anexo de reproducibilidad.

`.wslconfig` limitaba WSL2 a 4 procesadores en una máquina con 6 núcleos
físicos y 12 lógicos. Al elevarlo a 6, la generación del 3B pasó de **5,5 a 9,6
fichas por segundo**, un 75 % más, sin tocar una línea de código.

Consecuencia metodológica: la medición P-07 del 1 de septiembre, tomada en
Windows nativo con 6 hilos, y la del 7 de septiembre, tomada en WSL2 con 4, no
son comparables entre sí aunque midan lo mismo.

**Lo aprendido.** Toda cifra de latencia debe publicarse junto al número de
hilos, el entorno de ejecución y la longitud del prefijo. Sin eso no es un
resultado, es una anécdota.

---

## H-06 · El cacheo de prefijo funciona y sostiene el diseño del contrato estático

**Sección:** 5, 6 y 7.

| Fecha | Entorno | Hilos | Prefijo | Prefill en frío | Prefill en caliente |
|---|---|---|---|---|---|
| 01-09 | Windows nativo | 6 | ~1.800 fichas (sintético) | 17,5 s | ~1 s |
| 07-09 | WSL2 | 4 | 2.890 fichas (real) | 62,0 s | 0,18 s |
| 09-09 | WSL2 | 6 | 3.067 fichas (real) | 98 s | 0,09–0,47 s |

La caída del prefill supera el 99 % en los tres casos. Es lo que hace viable
un contrato de tres mil fichas en CPU: se paga una vez al arrancar (D-34) y
deja de contar. Justifica D-33, la decisión de que el contrato sea completo y
estático en lugar de recuperado dinámicamente.

**Presupuesto de fichas.** Contrato 1.0: 2.890. Contrato 1.1: 3.067, repartidas
en bloque 4 con 490, bloque 5 con 218 y bloque 7 con 253. Ventana de 4.096,
umbral de alerta en 3.200 (D-46). No alcanzado.

---

## H-07 · Una métrica estricta penaliza respuestas correctas, y hay que declararlo

**Sección:** 4 y 7.

D-50 fijó la igualdad exacta de conjuntos como criterio, **antes** de conocer
el resultado final. El precio es visible: con el 7B, la pregunta 15 identifica
correctamente el mejor mes de ventas pero añade una columna de ranking, y
cuenta como fallo. Lo mismo ocurría con la 10, donde el ganador era correcto y
solo diferían los recuentos.

**Lo aprendido.** Conviene reportar, junto a la precisión, cuántos fallos son
de respuesta y cuántos de forma. Relajar la métrica después de ver los números
habría sido indefendible; declararla antes y explicar su coste, no.

---

## H-08 · Los agentes informan de lo que hicieron, no de lo que rompieron

**Sección:** 4, y lecciones aprendidas del vídeo.

Dos episodios documentados durante el desarrollo. En el primero, el informe de
cierre detallaba recuentos de fichas y latencias de caché mientras la precisión
del sistema era 0 de 18, dato que no se mencionó. En el segundo, se reportó una
mejora de 6 a 7 aciertos sin señalar que una pregunta previamente correcta
había dejado de serlo.

**Lo aprendido.** El desarrollo asistido por agentes exige un protocolo de
revisión explícito por parte del responsable: contrastar siempre el veredicto
por caso contra la pasada anterior, y no aceptar un saldo agregado como prueba
de avance. Esta es una lección metodológica del proyecto y merece figurar en la
memoria.

---

## Taxonomía de los fallos que persisten

Con el 7B y el contrato 1.1, cinco preguntas del Nivel 1 siguen fallando. No
son la misma clase de error y conviene presentarlas separadas:

| Preguntas | Clase | Naturaleza |
|---|---|---|
| 5, 13 | Mapeo semántico | Elige `macro_categoria` por `categoria_producto` y `importe_pagado` por `importe_articulos`, pese a estar definidos en el bloque 3 |
| 9, 10 | Bandera espuria residual | Resto del efecto de H-02, no eliminado por el aumento de escala |
| 15 | Estrictez de la métrica | La respuesta de negocio es correcta; falla por una columna de más (H-07) |

---

## Pendiente de medir

Lo que la memoria pedirá y todavía no existe. No inventar:

- Precisión de los niveles 2 y 3, y del bloque de abstención (preguntas 56-63).
- Ablación del contrato semántico: mismo modelo con y sin contrato (D-21).
- Ablación del bucle de autocorrección (D-20).
- Estimación de costes de infraestructura, exigida por la sección 5 de la
  normativa. Debe cubrir el escenario local y el equivalente en nube.
- Consideraciones éticas y legales, exigidas por la sección 6: licencia del
  dataset de Olist, etiquetado de los datos simulados y riesgo de respuesta
  errónea presentada con apariencia de autoridad.
