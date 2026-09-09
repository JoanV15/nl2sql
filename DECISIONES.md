# Registro de Decisiones — TFM NL-to-SQL

Bitácora de las decisiones de diseño del proyecto, con su justificación y las
alternativas descartadas.

**Para qué sirve este fichero.** La Normativa TFM exige justificar las
herramientas elegidas (Sección 5), exponer las limitaciones identificadas
(Sección 7) y describir la metodología por fases (Sección 4). Este registro es
el borrador de esas tres secciones. Reconstruir las justificaciones de memoria
al final del proyecto es de donde salen los argumentos débiles que un tribunal
detecta.

**Cómo mantenerlo.** Cada vez que se tome una decisión no trivial, añadir una
entrada. Cada vez que se descarte una alternativa, dejarla escrita: el descarte
razonado vale más ante un tribunal que la opción elegida sin contraste.

**Estado de las entradas:** `Firme` · `Provisional` · `Pendiente`

---

## 1. Decisiones de arquitectura

### D-01 · Motor analítico: DuckDB

**Fecha:** 2026-08-26 · **Estado:** Firme

**Contexto.** Tres documentos previos proponían tres motores distintos para la
capa de servicio: Polars escribiendo Parquet (propuesta inicial), DuckDB
(`Arquitectura.md`) y PostgreSQL (`Prompt_Cursor.md`).

**Decisión.** DuckDB como motor analítico y de servicio.

**Justificación.** Es un motor OLAP columnar embebido: no consume un contenedor
adicional en un presupuesto de memoria ajustado, lee Parquet y Delta de forma
nativa —lo que mantiene la coherencia del lakehouse— y su integración con dbt
está madura. A la escala de Olist, cualquiera de los tres funcionaría; el
criterio decisivo es el coste de infraestructura y la coherencia del relato
arquitectónico.

**Alternativas descartadas.** PostgreSQL: válido técnicamente y con un control
de permisos por roles más limpio, pero añade un servidor donde DuckDB ya cubre
la función y rompe la narrativa de lakehouse. Polars: no es un motor SQL, lo que
lo descarta para una arquitectura NL-to-SQL.

---

### D-02 · Transformación Silver → Gold: dbt

**Fecha:** 2026-08-26 · **Estado:** Firme · **Divergencia con la propuesta aprobada**

**Contexto.** La propuesta presentada a los tutores asignaba la construcción de
la capa Gold a scripts de Polars, y simultáneamente declaraba el linaje
extremo a extremo en OpenMetadata como el activo central del proyecto.

**Decisión.** dbt sobre DuckDB sustituye a Polars en la transformación
Silver → Gold.

**Justificación.** Ambos planteamientos de la propuesta son incompatibles entre
sí: unos scripts de Polars no emiten metadatos de linaje, por lo que ese linaje
habría que declararlo manualmente y dejaría de ser trazable. dbt lo genera de
forma nativa y dispone de integración directa con OpenMetadata. La decisión no
nace de una preferencia técnica sino de la necesidad de cumplir un objetivo
declarado en la propia propuesta. Adicionalmente aporta tests de datos, tests
unitarios sobre datos fijados y documentación generada.

**Alternativas descartadas.** Mantener Polars y declarar el linaje a mano:
frágil, no reproducible y contrario al objetivo de gobierno.

---

### D-03 · Orquestador: Dagster

**Fecha:** 2026-08-26 · **Estado:** Firme · **Divergencia con la propuesta aprobada**

**Contexto.** La propuesta aprobada especificaba Apache Airflow.

**Decisión.** Dagster.

**Justificación.** Tres motivos, en orden de peso. Consume del orden de 1 GB
menos que Airflow con su base de datos de metadatos, y el presupuesto de memoria
del host es la restricción dominante del proyecto. Su modelo de Software-Defined
Assets mapea directamente las capas de la arquitectura Medallion, mientras que
el modelo de tareas de Airflow modela el proceso y no el dato. Y su integración
con dbt es nativa, lo que importa a raíz de D-02.

**Alternativas descartadas.** Airflow: estándar de industria y sin fricción
frente a los tutores, pero peor encaje con dbt y mayor huella de memoria.

**Acción pendiente.** Comunicar el cambio a los tutores (ver P-04).

---

### D-04 · Eliminación de Polars del stack

**Fecha:** 2026-08-26 · **Estado:** Firme · **Divergencia con la propuesta aprobada**

**Decisión.** Polars sale de la arquitectura.

**Justificación.** Tras D-02, Polars quedaba relegado a la ingesta batch, donde
su uso contradice la definición de la capa Bronze: en cuanto un motor de
dataframes lee un CSV ha inferido tipos y ha descartado la representación
original, de modo que el dato deja de ser crudo. La ingesta debe aterrizar el
payload tal como se recibe. Mantener tres motores de datos (Polars, Spark,
DuckDB) donde dos cubren todas las responsabilidades es difícil de defender y
consume presupuesto de páginas de la memoria, limitada a 20 caras.

**Resultado.** Dos motores con frontera nítida: Spark para procesamiento
distribuido, DuckDB para analítica de nodo único.

---

### D-05 · Sin frameworks que encapsulen el núcleo NL-to-SQL

**Fecha:** 2026-08-27 · **Estado:** Firme

**Contexto.** El borrador `Prompt_Cursor.md` planteaba usar
`NLSQLTableQueryEngine` de LlamaIndex.

**Decisión.** El núcleo NL-to-SQL —construcción del contexto, montaje del
prompt, validación y ejecución— se implementa como código propio.

**Justificación.** Ese objeto encapsula exactamente las cuatro piezas que
constituyen la aportación del trabajo, y además ejecuta el SQL por su cuenta,
lo que anula el validador de seguridad. Usarlo reduciría el TFM a una llamada
a una función de librería y lo dejaría indefendible. Son del orden de 300 líneas
de Python.

---

### D-06 · OpenMetadata fuera del tiempo de ejecución

**Fecha:** 2026-08-26 · **Estado:** Firme

**Contexto.** El diseño previo consultaba la API de OpenMetadata en cada
pregunta del usuario para construir el prompt.

**Decisión.** OpenMetadata opera únicamente en tiempo de construcción. Un asset
de Dagster compila desde su API un artefacto versionado —el contrato
semántico— que es lo que consume el runtime.

**Justificación.** Cuatro beneficios de un solo cambio. Elimina un servicio
pesado del camino crítico de la inferencia, liberando memoria durante la parte
del sistema que más consume. Hace el contexto del prompt reproducible,
versionable y diffable, lo que es condición para que la evaluación tenga
validez. Elimina un punto único de fallo y su latencia. Y, de forma no obvia,
al ser el prefijo del prompt idéntico entre consultas, habilita la caché de
prefijo del modelo, que es lo que hace el sistema usable en CPU (ver C-04).

---

### D-07 · Almacenamiento: ruta configurable, local primero

**Fecha:** 2026-08-26 · **Estado:** Firme

**Decisión.** Las rutas de Landing, Bronze y Silver son una variable de
configuración. Desarrollo contra sistema de ficheros local; conmutación a
ADLS Gen2 (`abfss://`) como paso posterior. La capa Gold reside **siempre** en
local, como fichero de base de datos DuckDB.

**Justificación.** La integración de Spark con ADLS mediante `hadoop-azure` es
una fuente conocida de tiempo perdido, y el calendario no admite descubrirlo
tarde. Abstraer la ruta convierte una dependencia de calendario en una variable
de entorno: si la integración falla, se entrega en local y se documenta.

Gold en local por dos motivos: la demo debe ser instantánea, y materializar las
tablas dentro de un fichero `.duckdb` es lo que permite abrir la conexión en
solo lectura con el acceso al sistema de ficheros desactivado. Si Gold fueran
ficheros Parquet leídos con `read_parquet()`, ese control de seguridad sería
imposible.

---

### D-08 · Recuperación de la Landing / Quarantine Zone

**Fecha:** 2026-08-26 · **Estado:** Firme

**Contexto.** La propuesta aprobada incluía una zona de aterrizaje con una
partición de cuarentena (Dead Letter Queue). `Arquitectura.md` la había
perdido.

**Decisión.** Se recupera. Landing almacena el payload original tal como se
recibe; los registros que no cumplen el esquema estricto se desvían a
cuarentena mediante el modo `PERMISSIVE` de Spark y la columna
`_corrupt_record`.

**Justificación.** Resuelve la contradicción de inmutabilidad de Bronze —los
bytes originales viven en Landing, de modo que Bronze puede ser Delta con
metadatos de trazabilidad sin dejar de ser reprocesable desde el origen— y
garantiza que un registro corrupto no bloquee el pipeline.

---

### D-09 · Ingesta de eventos: Spark Structured Streaming en micro-lote

**Fecha:** 2026-08-26 · **Estado:** Firme

**Decisión.** El drenaje de Kafka hacia Landing/Bronze se realiza con Spark
Structured Streaming con disparador de tipo *available-now*, en lugar de un
consumidor Python propio.

**Justificación.** El checkpointing resuelve gestión de offsets y semántica de
entrega sin escribir esa lógica; el micro-lote agrupa eventos y elimina por
construcción el problema de ficheros pequeños; y el disparador *available-now*
procesa lo pendiente y termina, evitando mantener una JVM viva de forma
permanente, que era incompatible con el presupuesto de memoria. Elimina además
un componente del stack.

**Alternativa descartada.** Kafka Connect con conector de sink: es la respuesta
canónica de industria, descartada por coste de memoria y de configuración.

---

### D-10 · Formato de la capa Silver: Delta Lake

**Fecha:** 2026-08-26 · **Estado:** Firme

**Decisión.** Silver en Delta Lake, escrito por Spark y leído por DuckDB.

**Justificación.** Aporta transacciones ACID, evolución de esquema controlada,
`MERGE` para escritura idempotente y *time travel*. Este último tiene un uso
funcional concreto y no decorativo: permite fijar la versión de datos contra la
que se ejecuta la evaluación, lo que hace los resultados reproducibles.

**Riesgo.** El soporte de lectura de Delta desde DuckDB debe verificarse sobre
la versión concreta empleada. Plan B: que Spark publique además una copia de
Silver en Parquet plano.

**Nota operativa.** Delta retiene versiones antiguas hasta que se ejecuta
`VACUUM`. Hay que declarar una política de retención, dado que el espacio en
disco es una restricción real (ver C-07).

---

## 2. Decisiones sobre la capa analítica

### D-11 · Capa Gold: cuatro OBT con grano declarado

**Fecha:** 2026-08-30 · **Estado:** Firme · **Divergencia con la propuesta aprobada**

**Contexto.** La propuesta especificaba "una única tabla desnormalizada".

**Decisión.** Cuatro tablas, cada una con un grano único y declarado:

| Tabla | Grano | Un registro por |
|---|---|---|
| `obt_pedidos` | Pedido | `id_pedido` |
| `obt_lineas_pedido` | Línea de pedido | `id_pedido` + `num_linea` |
| `obt_vendedores` | Vendedor | `id_vendedor` |
| `obt_embudo_web` | Día × producto | `fecha` + `id_producto` |

*Nomenclatura actualizada por D-36.*

**Justificación.** Ver C-01. Una OBT única no es implementable con estas
fuentes.

**Reglas de construcción.** En `obt_pedidos`, pagos y reseñas se agregan a nivel
de pedido **antes** de unirse. En `obt_lineas_pedido`, los atributos de pedido
se denormalizan repetidos y quedan marcados como no aditivos. Así el fan-out de
Olist no puede producir importes inflados, porque el modelo nunca ve las tres
tablas simultáneamente.

**Criterio de diseño derivado.** No toda fuente nueva genera una tabla nueva. El
transportista y el tipo de incidencia logística son atributos del pedido; los
tipos de cambio son una columna de importe adicional; el dataset de captación
enriquece `obt_vendedores`. Enriquecer una tabla existente es preferible a
añadir otra.

---

### D-12 · Facturación canónica: `importe_articulos`

**Fecha:** 2026-09-01 · **Estado:** Firme

**Contexto.** "¿Cuánto facturamos?" admite cuatro respuestas distintas en Olist,
y esa ambigüedad es una fuente estructural de error para el modelo.

**Decisión.** Coexisten cuatro medidas con nombre propio: `importe_articulos`
(suma de `price`), `importe_flete` (suma de `freight_value`), `importe_total`
(suma de ambos) e `importe_pagado` (suma de `payment_value`). El contrato
semántico declara que **facturación y GMV significan `importe_articulos`**.

**Justificación.** GMV es una métrica estándar de comercio electrónico definida
como el valor de la mercancía transaccionada, excluyendo portes. El flete no es
ingreso del marketplace, es un traspaso a la logística: incluirlo infla las
ventas. `payment_value` incorpora recargos de financiación y uso de vales, por
lo que mide caja cobrada y no mercancía vendida: responde a una pregunta de
tesorería, no comercial.

**Regla de negocio asociada.** La facturación canónica excluye los pedidos en
estado `canceled` y `unavailable`.

**Criterio general aplicable.** Ante una métrica ambigua, preguntarse a qué
pregunta de negocio responde y quién la formularía. Dirección comercial → GMV.
Finanzas → caja cobrada. Logística → flete. La ambigüedad desaparece cuando
cada métrica tiene un dueño.

---

### D-13 · Banderas booleanas precalculadas

**Fecha:** 2026-08-30 · **Estado:** Firme

**Decisión.** Las condiciones de negocio recurrentes se materializan como
columnas booleanas en las OBT: `es_venta_valida`, `fue_entregado_a_tiempo`,
`tiene_resena_negativa`, `es_cliente_recurrente`, `fue_pagado_a_plazos`
(nomenclatura fijada en D-36).

**Justificación.** Cada condición que el modelo debe reconstruir es una
oportunidad de equivocarse. Con la bandera precalculada, el modelo pasa de tener
que recordar qué estados excluir a escribir `WHERE es_venta_valida`. Junto con
el grano declarado, es la técnica anti-alucinación con mejor relación entre
coste y efecto: son columnas de dbt.

---

### D-14 · Test de reconciliación entre OBT

**Fecha:** 2026-08-30 · **Estado:** Firme

**Decisión.** Un test de dbt verifica que los agregados equivalentes calculados
por distintos caminos coincidan.

**Justificación.** Con cuatro tablas denormalizadas, la misma pregunta admite
varias rutas. Si `obt_pedidos.importe_articulos` y la suma de
`obt_lineas_pedido.importe_articulos` no cuadran, el sistema es incoherente y
devolverá respuestas distintas a la misma pregunta según el camino que elija el
modelo.

**Nota de nomenclatura (D-36).** La medida conserva el mismo nombre en ambos
granos porque designa el mismo concepto de negocio; el grano lo declara la
tabla, no el nombre de la columna. Evitar pares del tipo singular/plural que se
distingan por una letra es deliberado: son una fuente de confusión tanto para el
modelo como para quien lea el SQL.

---

### D-15 · Fecha de referencia fija, sin desplazar los datos

**Fecha:** 2026-08-28 · **Estado:** Firme

**Contexto.** Olist termina el 2018-10-17. Expresiones como "esta semana",
"el año pasado" o "los últimos seis meses" no tienen sentido contra el reloj del
sistema.

**Decisión.** Se define una fecha de referencia igual al máximo del dataset.
Todas las expresiones temporales relativas se resuelven contra ella, declarada
en el contrato semántico y visible en la interfaz.

**Alternativa descartada.** Desplazar las fechas al presente: falsearía la
estacionalidad real del negocio y comprometería cualquier análisis temporal.

---

### D-16 · Alcance del catálogo de preguntas

**Fecha:** 2026-09-01 · **Estado:** Firme

**Decisión.** Se descartan las preguntas 49 (concentración de incidencias
logísticas) y 52 (visitas previas a la compra), que exigirían grano de evento y
grano de sesión respectivamente.

**Justificación.** Dos modelos adicionales que mantener, testear y justificar en
una memoria de 20 caras, a cambio de dos preguntas de 63.

---

### D-36 · Idioma y convención de nombres del modelo analítico

**Fecha:** 2026-09-03 · **Estado:** Firme

**Contexto.** La convención se estaba fijando por inercia y de forma
contradictoria: D-11 declaraba los granos en inglés (`order_id`, `seller_id`),
D-12 definía las medidas en castellano (`importe_articulos`) y D-14 citaba
`obt_lineas_pedido.precio`. Tres decisiones firmes con dos convenciones y
ninguna deliberación.

**Decisión.** La capa Gold se nombra **íntegramente en castellano**, claves
incluidas. Bronze y Silver conservan los nombres de origen sin alterar.

**Convención.**

| Elemento | Regla | Ejemplo |
|---|---|---|
| Formato | `snake_case`, sin tildes ni eñes | `tiene_resena_negativa` |
| Tablas | `obt_<entidad>` | `obt_lineas_pedido` |
| Claves | `id_<entidad>` | `id_pedido`, `id_vendedor` |
| Importes | `importe_<concepto>` | `importe_flete` |
| Recuentos | `num_<concepto>` | `num_articulos` |
| Duraciones en días | `dias_<concepto>` | `dias_entrega` |
| Proporciones | `pct_<concepto>` | `pct_retraso` |
| Fechas y marcas de tiempo | `fecha_<concepto>`, tipo declarado en el contrato | `fecha_compra` |
| Booleanos | `es_`, `tiene_` o `fue_` | `fue_entregado_a_tiempo` |

**Justificación.** El modelo no solo consume descripciones, también emite SQL
que referencia nombres físicos. Con la pregunta en castellano y la columna en
castellano, la distancia léxica entre enunciado y esquema se reduce al mínimo y
el modelo se aproxima a copiar en lugar de traducir. Esa distancia pesa más
cuanto menor es el modelo, porque el alineamiento entre idiomas es de las
primeras capacidades que se degradan al bajar de 7B a 3B (D-29).

**Sobre la trazabilidad.** La objeción legítima es que renombrar rompe el
vínculo con el dataset de origen. Se resuelve situando el renombrado en la
frontera correcta: Bronze y Silver preservan los nombres originales por
inmutabilidad y linaje (D-10), y Gold es donde el modelo deja de ser técnico
para ser de negocio. Renombrar en esa frontera no es un apaño sino la práctica
propia del modelado dimensional: **el renombrado es la capa semántica**. El
mapeo queda versionado en dbt, que además aporta linaje columna a columna. La
trazabilidad no se pierde, se explicita.

**Beneficio adicional.** Permite corregir nombres de origen deficientes. El caso
de C-05, donde `customer_id` es único por pedido y `customer_unique_id`
identifica a la persona, se convierte en `id_cliente_pedido` e
`id_cliente_persona`: la distinción pasa de ser un matiz tipográfico a resultar
evidente.

**Alternativas descartadas.** Inglés en todas las capas, fiel al origen:
maximiza la trazabilidad literal a costa de imponer un salto entre idiomas en
cada consulta. Convención híbrida con claves en inglés y medidas en castellano:
obliga al modelo a sostener dos convenciones simultáneas y es precisamente el
estado incoherente del que parte esta decisión.

**Correcciones que introduce.** Se actualizan D-11 (claves de grano), D-13
(prefijo en `entregado_a_tiempo` y `pagado_a_plazos`) y D-14 (referencia a
`precio`).

**Línea de trabajo futuro.** El idioma del esquema es una hipótesis medible:
cabría añadirlo como cuarto eje de ablación en D-21 exponiendo la Gold con
alias en inglés y repitiendo el conjunto de evaluación. Se descarta ejecutarlo
por calendario y se deja formulado en la memoria como trabajo futuro.

---

### D-37 · Estructura y formato del contrato semántico

**Fecha:** 2026-09-03 · **Estado:** Firme

**Contexto.** El presupuesto de 2.500 tokens medido en P-07 no lo consume el
número de columnas sino el formato con que se declaran. La misma columna cuesta
unos 40 tokens en prosa, 18 en fila de tabla y 15 en DDL con comentario. Sobre
unas 110 columnas, la diferencia va de 4.400 a 1.650 tokens: el formato no
ajusta el contrato al presupuesto, decide si el presupuesto existe.

**Decisión.** El catálogo de columnas se declara como sentencias `CREATE TABLE`
con comentarios en línea. Los aspectos que el DDL no puede expresar se recogen
en bloques de prosa separados y breves.

**Justificación del DDL.** No se elige por ser el más compacto, sino por ser la
representación de esquema predominante en el preentrenamiento de un modelo de
código como Qwen2.5-Coder. Leer un esquema en DDL no obliga al modelo a
interpretar una convención propia del proyecto. Que además sea el formato más
corto de los tres evaluados es una coincidencia favorable, no el criterio.

**Reparto del presupuesto.**

| Bloque | Contenido | Tokens |
|---|---|---|
| Rol y formato de salida | Dialecto DuckDB, solo SQL sin explicaciones (D-35) | ~120 |
| Esquema en DDL | Cuatro `CREATE TABLE` con grano declarado y comentarios | ~1.500 |
| Métricas canónicas y sinónimos | D-12 y glosario de negocio | ~200 |
| Reglas de negocio | Venta válida y fecha de referencia (D-15) | ~120 |
| Política de abstención | Cuándo declarar que el dato no existe | ~60 |
| Ejemplos resueltos | Tres casos: simple, función de ventana y abstención | ~400 |

Total aproximado 2.400 sobre los 2.500 medidos, con holgura para crecer.

**Ausencia deliberada de reglas de JOIN.** Con cuatro OBT desnormalizadas y
grano declarado (D-11), toda pregunta se responde desde una sola tabla. Basta
una línea afirmándolo en lugar de un mapa de claves foráneas. Ese ahorro es
exactamente lo que compra la desnormalización, y conviene señalarlo así en la
memoria.

**Prioridad de recorte.** Si el contrato excede el presupuesto, el primer bloque
a reducir es el de ejemplos resueltos, que es el más caro por unidad. El
esquema y las reglas de negocio no se recortan.

**Corrección.** El 2.500 no era un techo de fichas. El criterio de dimensionado
queda en D-46.

---

### D-38 · Definiciones canónicas surgidas del diseño de `obt_pedidos`

**Fecha:** 2026-09-03 · **Estado:** Firme

Tres ambigüedades que el catálogo de preguntas no resuelve y que, sin una regla
declarada, producirían una columna que a veces miente. Aplican el criterio de
D-12: ante una métrica ambigua, fijar una definición y publicarla.

**Plazo de entrega.** `dias_entrega` se cuenta desde `fecha_compra` hasta
`fecha_entrega_cliente`. Se descarta contarlo desde la aprobación del pago:
mediría con más pureza la operación logística, pero no es lo que un cliente
entiende al preguntar cuánto tarda en llegarle un pedido, y el catálogo está
redactado en lenguaje de stakeholder. El tramo de pago queda igualmente
disponible como diferencia entre `fecha_compra` y `fecha_aprobacion_pago`.

**Pedidos con varias reseñas.** Alrededor del 1% de los pedidos de Olist tiene
más de una. `nota_resena` recoge la **media** de las notas. En consecuencia la
columna se declara `DECIMAL` y no `INTEGER`: declarar mal el tipo es una de las
formas más directas de romper una consulta generada.

**Conversión a euros.** `importe_articulos_eur` aplica un **tipo único de
referencia**, declarado en el contrato y en la memoria. Se descarta el tipo
histórico diario porque exige series de 2016 a 2018 que las APIs gratuitas
limitan o cobran, y el riesgo de calendario no compensa el realismo añadido. La
pérdida del efecto cambiario se documenta explícitamente.

---

## 3. Decisiones sobre el sistema NL-to-SQL

### D-17 · LLM local como sistema, modelo cloud como referencia

**Fecha:** 2026-08-26 · **Estado:** Firme

**Decisión.** El sistema opera con un modelo local cuantizado. Un modelo
frontera de API se emplea exclusivamente como término de comparación sobre el
mismo conjunto de evaluación, enviando esquema y preguntas, nunca datos.

**Justificación.** Preserva el argumento de soberanía del dato y, al mismo
tiempo, produce una de las comparativas que exige la Sección 7 de la normativa:
cuantifica en puntos de precisión lo que cuesta la privacidad. Convierte una
limitación de hardware en un resultado medido.

---

### D-18 · Soberanía del dato como principio, no como excusa

**Fecha:** 2026-08-26 · **Estado:** Firme

**Decisión.** La ejecución local del modelo se justifica como decisión de diseño
—ni los datos de negocio ni las preguntas de los usuarios abandonan la
infraestructura, sin transferencias a terceros ni internacionales— y no
únicamente como consecuencia de la falta de hardware.

**Justificación.** Cubre el requisito de consideraciones éticas y legales de la
Sección 6 de la normativa y aporta el ángulo de innovación. La misma decisión
técnica, formulada de otro modo, pasa de ser una limitación a ser un principio.

---

### D-19 · Seguridad en código, no en el prompt

**Fecha:** 2026-08-26 · **Estado:** Firme

**Decisión.** Cuatro capas independientes:

1. Validador de política con `sqlglot` en dialecto DuckDB: solo `SELECT` y
   `WITH`, rechazo de sentencias múltiples, lista blanca de tablas **y de
   funciones de tabla**, lista blanca de columnas contra el contrato semántico,
   inyección forzada de `LIMIT`.
2. `EXPLAIN` como validación semántica por *binding* (ver C-06).
3. Conexión DuckDB en `read_only=True` con `enable_external_access=false`.
4. Límites de recursos: `memory_limit`, número de hilos y timeout por
   cancelación desde el cliente.

**Justificación.** Una lista blanca que solo verifique "es un SELECT y toca
tablas permitidas" deja pasar la lectura arbitraria del sistema de ficheros
mediante funciones de tabla de DuckDB (`read_csv_auto`, `glob`, `read_parquet`),
además de `ATTACH`, `INSTALL`, `LOAD` y `COPY ... TO`. La capa 3 es la única
infalsificable por el modelo.

**Nota de implementación.** Debe validarse exactamente la cadena que se va a
ejecutar; reescribir el SQL después de validarlo abre una ventana de
*time-of-check / time-of-use*.

---

### D-20 · Bucle de autocorrección acotado y con revalidación

**Fecha:** 2026-08-26 · **Estado:** Firme

**Decisión.** Máximo tres intentos. El SQL corregido vuelve a pasar
obligatoriamente por el validador. El orquestador de aplicación media siempre:
el validador nunca dialoga directamente con el modelo.

**Justificación.** El diagrama de secuencia de `Arquitectura.md` ejecutaba el SQL
corregido sin revalidar, lo que constituía un bypass del control de seguridad.
El error del *binder* de DuckDB es la señal de mayor calidad para la corrección,
porque suele incluir la sugerencia de la columna correcta.

**Cuándo no aporta.** Ante una pregunta ambigua o no respondible, reintentar
solo produce una segunda alucinación. La respuesta correcta es la abstención o
la petición de aclaración.

---

### D-21 · Evaluación estratificada con estudio de ablación

**Fecha:** 2026-08-28 · **Estado:** Firme

**Decisión.** Conjunto de 63 preguntas estratificado en cuatro bloques
—básicas, intermedias, avanzadas y trampas/abstención—, métrica de *execution
accuracy* por comparación de conjuntos de resultados, y ablación por capas de
contexto: solo esquema, +descripciones, +grano y aditividad, +sinónimos y
valores, +few-shot, +autocorrección.

**Justificación.** La Sección 7 de la normativa exige métricas y comparativas.
Sin esto, la tesis del trabajo —que el grounding con metadatos reduce las
alucinaciones— no es falsable. La estratificación produce una curva de
degradación por complejidad, mucho más informativa y defendible que un
porcentaje agregado.

**Requisito metodológico.** El SQL de referencia debe escribirse **antes** de
observar el comportamiento del sistema. Redactarlo después sesga el conjunto
hacia lo que ya se sabe que funciona.

---

### D-22 · Traza de consultas persistida

**Fecha:** 2026-08-26 · **Estado:** Firme

**Decisión.** Se registra por consulta: pregunta, versión del contrato
semántico, prompt, SQL crudo, veredicto del validador, cada reintento con su
error, SQL final, latencia desglosada, tokens y filas devueltas.

**Justificación.** Cubre la observabilidad LLMOps del temario, alimenta el
capítulo de resultados y proporciona el material del vídeo. Coste: una tabla.

---

### D-33 · Contrato semántico completo y estático, sin recuperación dinámica

**Fecha:** 2026-09-01 · **Estado:** Firme

**Decisión.** El prompt se compone de un prefijo invariante que contiene el
contrato semántico íntegro, seguido de la pregunta del usuario al final. Se
descarta seleccionar por pregunta un subconjunto de tablas o columnas mediante
recuperación semántica.

**Justificación.** No es una preferencia de diseño sino una consecuencia
medida. La medición P-07 sobre el hardware objetivo arroja un prefill en frío
de 17.541 ms para 2.540 tokens de contrato, frente a entre 72 y 1.253 ms con la
caché de prefijo caliente. La caché solo se reutiliza si el prefijo es idéntico
byte a byte, de modo que cualquier esquema que varíe el encabezado del prompt
en función de la pregunta lo invalida y devuelve la latencia a los 17,5
segundos por consulta.

**Alternativa descartada.** Recuperación dinámica de metadatos, habitual en la
literatura de Text-to-SQL sobre esquemas de cientos de tablas. Aportaría valor
si el contrato no cupiese en la ventana de contexto; con cuatro OBT y unos
2.500 tokens sí cabe, y el coste de latencia que introduce supera con creces
cualquier ganancia en precisión.

**Observación para la defensa.** Permite justificar con evidencia empírica por
qué el sistema no implementa el mecanismo que un tribunal podría esperar por
defecto, y delimita con precisión bajo qué condiciones sí sería la opción
correcta.

---

### D-34 · Precalentamiento de la caché al arrancar el servicio

**Fecha:** 2026-09-01 · **Estado:** Firme

**Decisión.** Al iniciarse, el runtime NL-to-SQL emite una petición de
descarte contra el modelo con el prefijo completo del contrato semántico, antes
de aceptar tráfico de usuario.

**Justificación.** Traslada los 17,5 segundos de prefill en frío al arranque
del contenedor, donde nadie los percibe, en lugar de cargárselos a la primera
consulta real. Coste de implementación: una llamada en el arranque. Debe
repetirse cuando se publique una versión nueva del contrato semántico.

---

### D-35 · Presupuesto de tokens de salida

**Fecha:** 2026-09-01 · **Estado:** Firme

**Decisión.** El modelo emite exclusivamente SQL, sin explicaciones,
comentarios ni razonamiento intermedio. Se fijan secuencias de parada y un
máximo de tokens de respuesta.

**Justificación.** Con la caché caliente el prefill se vuelve despreciable y el
tiempo de respuesta pasa a estar dominado por la generación, medida en 15,1
tokens por segundo de forma muy estable. Cada token de salida cuesta unos 66
ms, de modo que 120 tokens son casi 8 segundos. Reducir la verbosidad de la
respuesta es la única palanca de latencia que queda una vez resuelto el
prefill.

**Consecuencia sobre D-20.** El bucle de autocorrección se acota a un único
reintento: cada reintento añade una generación completa, llevando el peor caso
a unos 16 segundos.

---

## 4. Decisiones de proceso e infraestructura

### D-23 · Construcción por núcleo y anillos

**Fecha:** 2026-08-26 · **Estado:** Firme

**Decisión.** Se construye primero una rebanada vertical completa con la
tecnología más simple posible, y después se añaden anillos en este orden: dbt,
Spark con Landing y DLQ, streaming con Kafka, Dagster y CI, OpenMetadata, ADLS.

**Justificación.** Cada anillo es prescindible por separado sin romper el
núcleo. Construir en orden inverso —empezando por la infraestructura— produce
un sistema de contenedores sin capacidad de responder ninguna pregunta.

---

### D-24 · Empaquetado como paquete Python

**Fecha:** 2026-08-26 · **Estado:** Firme

**Decisión.** El proyecto se estructura como paquete instalable, con submódulos
alineados con las capas de la arquitectura, construido y publicado desde CI.

**Justificación.** La normativa recomienda generar un artefacto y valora la
calidad del código con peso en la calificación. Empaquetar obliga a que la
estructura de módulos refleje las fronteras de la arquitectura: el paquete es el
diagrama hecho código.

---

### D-25 · Alcance realista de la integración continua

**Fecha:** 2026-08-26 · **Estado:** Firme

**Decisión.** CI ejecuta linting, tests unitarios, la batería de casos dorados
del validador SQL, `dbt build` contra un DuckDB efímero poblado con seeds,
validación del esquema del contrato semántico, y construcción de imagen y wheel.
La evaluación NL-to-SQL se ejecuta en local y se versiona el informe.

**Justificación.** CI no puede levantar Spark, OpenMetadata ni un modelo de
5 GB. Declarar el alcance y el motivo es más defendible que prometer una
automatización que no existe.

---

### D-26 · Fuentes de datos

**Fecha:** 2026-08-28 · **Estado:** Firme

| Fuente | Tipo | Naturaleza |
|---|---|---|
| Olist Brazilian E-Commerce | CSV, JSON, Parquet | Real |
| Marketing Funnel by Olist | CSV | Real |
| API de tipos de cambio | REST | Real |
| Eventos logísticos | Kafka | Simulada |
| Clickstream | Kafka | Simulada |

**Justificación de las fuentes simuladas.** Las preguntas de negocio exigen
telemetría operativa —transportista, incidencias, comportamiento web— que el
núcleo transaccional de Olist no registra. La ingesta híbrida responde a un
requisito funcional, no a una demostración tecnológica. Ver C-02.

**Restricciones.** Todo evento simulado debe referenciar identificadores y
fechas reales de Olist y ser coherente con ellas; en caso contrario los cruces
devuelven vacío sin error visible. La memoria debe identificar con claridad qué
dato es real y cuál simulado.

**Descartada.** Simulación de devoluciones y logística inversa: cuarta fuente
sintética, sin encaje en el calendario. La pregunta asociada se retira.

---

### D-27 · Amplitud de orígenes y formatos como requisito

**Fecha:** 2026-09-01 · **Estado:** Firme · **Origen: indicación de los tutores**

**Contexto.** Los tutores indicaron expresamente que se amplíen los orígenes de
datos, cubriendo ingesta batch y streaming y diversidad de formatos, con el
criterio de que "cuanto más completo, complejo y polivalente sea el trabajo,
mejor".

**Decisión.** Se asume como requisito. La cobertura se articula en tres ejes,
que se documentan explícitamente en la memoria:

- **Paradigmas:** batch programado y streaming en micro-lote.
- **Protocolos:** sistema de ficheros, API REST, API GraphQL y Kafka.
- **Formatos:** CSV, JSON y Parquet en origen; Delta Lake en Silver; base de
  datos DuckDB en Gold; YAML para el contrato semántico.

**Interpretación aplicada.** El criterio se satisface con amplitud de
*paradigmas, protocolos y formatos*, no con acumulación de tecnologías
redundantes. Añadir un motor que duplique la función de otro no aporta
polivalencia; añadir un protocolo de ingesta distinto, sí.

**Consecuencia.** Se recupera la fuente GraphQL de la propuesta original,
implementada como servicio simulado de proveedores que expone el mismo dominio
por REST y por GraphQL. Cubre además el contenido "REST vs GraphQL" del módulo
de Aplicaciones Basadas en Contenedores.

---

### D-28 · Suscripción Azure for Students

**Fecha:** 2026-09-01 · **Estado:** Firme

**Decisión.** Activar Azure for Students en lugar de la prueba gratuita de
200 USD.

**Justificación.** El crédito de la prueba gratuita caduca a los 30 días y, al
expirar, los recursos quedan deshabilitados salvo conversión a pago por uso. El
crédito de Azure for Students tiene vigencia de 12 meses, lo que cubre el
desarrollo, la entrega y una eventual defensa posterior. El importe es menor
pero muy superior a lo necesario.

**Alcance del consumo.** Una única cuenta de almacenamiento con espacio de
nombres jerárquico habilitado (ADLS Gen2), redundancia local y nivel de acceso
frecuente. Unos pocos GB suponen céntimos al mes. No se despliegan servicios
gestionados de cómputo.

**Uso adicional.** El portal y la calculadora de precios proporcionan las
tarifas reales de los equivalentes gestionados (Event Hubs, Databricks,
Synapse o Fabric, y un endpoint de modelo gestionado) para el modelo de costes
que exige la Sección 5 de la normativa.

**Seguridad.** Credenciales en `.env` fuera de control de versiones y en
secretos de GitHub Actions. Se documenta la identidad administrada como patrón
correcto en un despliegue productivo.

---

### D-29 · Modelo: 3B primero, 7B como eje de ablación

**Fecha:** 2026-09-01 · **Estado:** Firme

**Decisión.** El desarrollo se realiza con un modelo de código de 3B cuantizado
a 4 bits. El modelo de 7B se incorpora al final, como punto adicional de la
curva de resultados y no como sustitución.

**Justificación.** El modelo de 3B ocupa del orden de 2 GB frente a los 4,7 GB
del de 7B y genera entre dos y tres veces más rápido, lo que reduce el tiempo de
cada iteración de desarrollo y hace que las pasadas de evaluación quepan en el
calendario.

**Consecuencia metodológica.** El tamaño de modelo pasa a ser un eje de la
ablación: 3B local, 7B local y modelo frontera en la nube constituyen tres
puntos de una misma curva que relaciona capacidad del modelo, coste y
privacidad.

**Expectativa a documentar.** Se anticipa una degradación acusada del modelo de
3B en las preguntas de Nivel 3 (funciones de ventana, percentiles, cohortes).
No es un fallo del sistema sino el resultado esperado, y su medición es parte
del capítulo de resultados.

**Matiz.** Aunque se elija 3B sin ensayo previo, la medición de latencia con y
sin caché de prefijo sigue siendo necesaria antes de fijar el tamaño del
contexto: determina cuántos tokens puede permitirse el contrato semántico.

**Corrección 2026-09-09.** D-52 midió la ablación. D-53 fija el 7B como
modelo del sistema. El 3B no se descarta: queda como brazo de ablación y
como opción de iteración rápida si el 7B no cabe junto a otra carga.

---

### D-30 · Macro-categorías como regla de negocio versionada

**Fecha:** 2026-09-01 · **Estado:** Firme

**Contexto.** Olist distribuye 71 categorías de producto planas, en portugués y
sin jerarquía. Varias preguntas de negocio operan a un nivel de agregación
superior.

**Decisión.** Se define un mapeo a 12 macro-categorías, materializado como
*seed* de dbt (`seed_macro_categorias.csv`) con las columnas
`product_category_name` y `macro_categoria`.

| Macro-categoría | Criterio de agrupación |
|---|---|
| Electrónica e Informática | `eletronicos`, `informatica_acessorios`, `pcs`, `pc_gamer`, `audio`, `cine_foto`, `consoles_games`, `tablets_impressao_imagem`, `telefonia*` |
| Electrodomésticos | `eletrodomesticos*`, `eletroportateis`, `climatizacao` |
| Hogar y Muebles | `moveis_*`, `cama_mesa_banho`, `casa_conforto*`, `utilidades_domesticas`, `portateis_*`, `la_cuisine` |
| Moda y Accesorios | `fashion_*`, `malas_acessorios`, `relogios_presentes` |
| Belleza y Salud | `beleza_saude`, `perfumaria`, `fraldas_higiene` |
| Deporte, Juguetes y Ocio | `esporte_lazer`, `brinquedos`, `artigos_de_festas`, `artigos_de_natal`, `cool_stuff` |
| Bricolaje, Jardín y Construcción | `casa_construcao`, `construcao_ferramentas_*`, `ferramentas_jardim`, `sinalizacao_e_seguranca`, `flores` |
| Cultura, Libros y Papelería | `livros_*`, `cds_dvds_musicais`, `dvds_blu_ray`, `musica`, `instrumentos_musicais`, `artes*`, `papelaria` |
| Alimentación y Bebidas | `alimentos*`, `bebidas` |
| Bebé y Mascotas | `bebes`, `pet_shop` |
| Automoción | `automotivo` |
| Otros y B2B | `agro_industria_e_comercio`, `industria_comercio_e_negocios`, `market_place`, `seguros_e_servicos`, categoría nula |

**Justificación.** Es una regla de negocio, no un detalle de implementación: por
eso se versiona en el repositorio, es editable sin tocar código y se declara en
el contrato semántico. Constituye además el ejemplo más tangible de capa
semántica del proyecto, ya que introduce una jerarquía que no existe en el dato
de origen.

**Control obligatorio.** Un test de dbt debe verificar que toda categoría
presente en la tabla de productos tenga exactamente una macro-categoría
asignada y que no existan entradas huérfanas en el *seed*. Sin ese test, un
error tipográfico o una categoría no contemplada desaparecen silenciosamente de
los agregados.

**Nota.** Los productos con categoría nula (del orden de 600 en Olist) se
asignan a "Otros y B2B" con la etiqueta explícita "Sin clasificar" en el
contrato semántico.

---

### D-31 · Política de retención en Delta y control del volumen

**Fecha:** 2026-09-01 · **Estado:** Firme

**Contexto.** Delta conserva las versiones anteriores de los ficheros hasta que
se ejecuta `VACUUM`, y el espacio en disco es una restricción real (C-07).

**Decisión.**

- Retención de ficheros eliminados: 7 días (valor por defecto, sin sobrescribir).
- Retención del log de transacciones: 30 días. Su tamaño es despreciable y
  preserva la trazabilidad de operaciones.
- `VACUUM` se ejecuta como asset de Dagster tras cada ejecución completa y
  correcta del pipeline, con cadencia semanal.

**Sobre la reproducibilidad de la evaluación.** No se confía el archivado a la
combinación de *time travel* y retención: `VACUUM` la invalida. La versión de
Delta empleada en cada pasada de evaluación se **registra explícitamente** en el
informe de resultados y, si debe preservarse más allá de la ventana de
retención, se materializa una copia independiente de esa versión.

**Control del volumen generado.** El generador de eventos es parametrizable por
volumen. Se persiste de forma habitual únicamente el nivel más pequeño; los
niveles mayores se generan bajo demanda para el benchmark comparativo entre
motores y se eliminan al terminar.

---

### D-32 · Base documental como quinto origen de datos

**Fecha:** 2026-09-01 · **Estado:** Firme · **Anillo exterior**

**Contexto.** Resolución de P-08, a raíz de la indicación de amplitud de los
tutores (D-27). Previamente se había descartado toda base NoSQL por coste de
recursos; la indicación modifica el balance.

**Decisión.** Se incorpora MongoDB como origen documental. Las reseñas de
clientes, en formato JSON, residen en una colección de MongoDB y se ingieren
desde allí mediante consulta, no mediante volcado de fichero.

**Justificación.** Añade un quinto protocolo de origen —sistema de ficheros,
REST, GraphQL, Kafka y base documental— y cubre el módulo de Bases de Datos
NoSQL, sin representación hasta ahora. Es además la topología realista: las
reseñas son datos semiestructurados de longitud variable, que en un sistema
real residen habitualmente en un almacén documental y no en una tabla.

**Coste.** Del orden de 500 MB en el perfil de plataforma, que no coexiste con
el perfil de inferencia. Aproximadamente media jornada de implementación.

**Condición.** Anillo exterior. Solo se aborda con el núcleo y los tres
primeros anillos cerrados.

**Requisito de honestidad.** Las reseñas se distribuyen en Olist como CSV. Su
conversión a JSON y su carga en MongoDB constituyen una simulación deliberada
de una topología de orígenes realista, y debe declararse como tal en la
memoria.

**Requisito de implementación.** Un script de carga puebla la colección
—representa el sistema origen— y el pipeline de ingesta lee de MongoDB con una
consulta real. Si la ingesta se limitase a leer el mismo fichero JSON, la pieza
sería decorativa.

---

### D-39 · Interfaz: Streamlit

**Fecha:** 2026-09-03 · **Estado:** Firme

**Decisión.** La interfaz es una aplicación Streamlit. Muestra de forma visible
la fecha de referencia de D-15, el SQL generado y los supuestos que el sistema
haya declarado.

**Justificación.** Figuraba ya en la propuesta y nunca se elevó a decisión, pese
a que D-22 daba por supuesta su existencia al mencionar el material del vídeo.
Es Python nativo, no introduce una pila de frontend independiente y su consumo
de memoria es marginal frente al del modelo. Mostrar el SQL generado no es
adorno: es lo que permite a un tribunal auditar la respuesta y lo que hace
demostrable el trabajo.

**Alternativas descartadas.** Gradio, equivalente en coste y sin ventaja clara.
FastAPI con frontend propio, que multiplicaría el trabajo sin aportar nada
evaluable.

---

### D-40 · Herramientas de desarrollo en Python

**Fecha:** 2026-09-03 · **Estado:** Firme

**Decisión.** `pyproject.toml` como declaración única, `uv` para entorno y
dependencias, `pytest` para pruebas y `ruff` para linter y formato.

**Justificación.** D-24 fijaba el empaquetado como paquete Python pero no la
herramienta, y un hueco así lo resuelve el primer agente que toque el
repositorio, de forma irreversible en la práctica. `uv` produce un fichero de
bloqueo, que es lo que convierte la reproducibilidad en verificable en lugar de
declarativa. `ruff` cubre linter y formato con una sola herramienta y una sola
entrada en CI.

---

### D-41 · Estructura del repositorio

**Fecha:** 2026-09-03 · **Estado:** Firme

**Decisión.** Estructura fijada en la sección 6 de `ARQUITECTURA.md`. Los
módulos de `src/tfm_nlsql/` reflejan las fronteras de la arquitectura:
`ingesta`, `plataforma`, `runtime` e `interfaz`.

**Justificación.** Cumple el criterio de D-24 de que la estructura de módulos
exprese la arquitectura. La separación entre `plataforma` y `runtime` es la
misma que impone la ejecución secuencial de C-03: si el árbol de directorios la
respeta, la frontera es visible en el código y no solo en la memoria.

**Nota.** `datos/` queda fuera de control de versiones. Es donde aterrizan
Landing, Bronze, Silver y Gold en la configuración local de D-07.

---

### D-42 · Instrucciones para agentes: una sola fuente por capa

**Fecha:** 2026-09-04 · **Estado:** Firme

**Contexto.** Antes del primer commit convivían en el repositorio tres ficheros
de instrucciones para agentes: `.cursorrules` de agosto, `AGENTS.md` y
`.cursor/rules/ponytail.mdc`. El primero contradecía frontalmente ocho
decisiones ya firmes y los otros dos duplicaban el mismo texto de estilo.

**Decisión.** Estilo de desarrollo en `.cursor/rules/ponytail.mdc`, que se carga
de forma automática. Contexto del proyecto en `AGENTS.md`, sin repetir el
estilo. `.cursorrules` se elimina.

**Por qué `.cursorrules` era peligroso y no solo obsoleto.** Ordenaba usar
Polars, eliminado en D-04. Prohibía toda herramienta de nube, en contra de D-07
y D-28. Fijaba el presupuesto de memoria en 16 GB, corregido a 6–7 en C-03.
Exigía un prompt minimalista, lo contrario de D-33. Describía el sistema como
RAG, terminología descartada. Y, sobre todo, mandaba implementar la seguridad
**buscando palabras clave en la cadena SQL, incluida `JOIN`**: un control falso
que D-19 sustituye por análisis del AST, y que además habría bloqueado las
subconsultas y autoagregaciones que exige el nivel 3 del catálogo.

**Lección para la memoria.** Un fichero de instrucciones desactualizado es más
dañino que su ausencia: el agente lo obedece sin señalar el conflicto. La
gobernanza de los artefactos que dirigen a un agente merece el mismo rigor que
la del código.

---

### D-43 · Alcance Gold del Hito 1: tres OBT, no una

**Fecha:** 2026-09-07 · **Estado:** Firme

**Contexto.** D-23 manda una rebanada vertical con la tecnología más simple
posible. El primer recorte contemplaba materializar solo `obt_pedidos`. Cuatro
preguntas del Nivel 1 —la 4, la 5, la 12 y la 18— no son respondibles desde
esa tabla: el contrato no tiene vendedor, categoría ni producto a grano
pedido, y D-11 sitúa esas columnas en las otras OBT. Recortar el contrato
rompería D-33. Inventar columnas en `obt_pedidos` contradiría D-11 y la nota
que descarta `num_vendedores`.

**Decisión.** El Hito 1 materializa `obt_pedidos`, `obt_lineas_pedido` y
`obt_vendedores`. `obt_embudo_web` queda fuera: ninguna pregunta del Nivel 1
la exige y su fuente es clickstream simulado, anillo posterior.

Las columnas que dependen de fuentes aún no implementadas se materializan
como `NULL` y **permanecen en el esquema**:

| Tabla | Columnas a NULL | Fuente pendiente |
|---|---|---|
| `obt_pedidos` | `importe_articulos_eur`, `id_transportista`, `tipo_incidencia` | tipos de cambio; eventos logísticos |
| `obt_vendedores` | `fecha_captacion`, `canal_captacion`, `segmento_negocio` | Marketing Funnel by Olist |

`dias_hasta_primera_venta` se deriva de `fecha_captacion`; al ser esta `NULL`,
también lo es. No se inventa un sustituto.

**Validador.** El contrato (prefijo) sigue declarando las cuatro tablas y no
se toca. La lista blanca del validador AST contiene solo las tres tablas
existentes: una consulta contra `obt_embudo_web` se rechaza con motivo
explícito y no llega a DuckDB. Es deuda del hito: cuando exista la cuarta
tabla, entra en la lista blanca. El prefijo y la lista blanca no coinciden
hasta entonces.

**Valores de `macro_categoria`.** Los doce nombres persistidos coinciden con
el bloque 4 del contrato —sin comas internas—, no con la prosa de la tabla de
D-30. El modelo filtra por lo que ve en el prefijo; un valor con coma
devolvería vacío sin error.

**Justificación.** El criterio de hecho del hito es responder las 18 preguntas
del Nivel 1. Tres tablas son el mínimo que lo hace posible sin falsear el
contrato ni el censo de vendedores (D-44).

**Alternativas descartadas.** Evaluar solo las 14 respondibles desde
`obt_pedidos`: dejaría el suelo de funcionamiento incompleto a sabiendas.
Tablas vacías con el esquema del contrato: el `EXPLAIN` pasaría y el
resultado mentiría. Recortar el prefijo: invalida la caché y contradice D-33.

---

### D-44 · Censo de vendedores: contar personas, no vendedores con ventas

**Fecha:** 2026-09-07 · **Estado:** Firme

**Contexto.** La pregunta 4 —«¿Cuántos vendedores distintos tenemos?»— admite
dos lecturas: el censo de `olist_sellers_dataset` o el recuento distinto de
`id_vendedor` en las líneas de pedido. La segunda pierde a quien se dio de
alta y no llegó a vender, y devolvería un número incorrecto sin fallar.

**Decisión.** «Vendedores distintos» significa el censo completo.
`obt_vendedores` se construye desde `olist_sellers_dataset` y los agregados
de actividad se unen por la izquierda. No se deriva de `obt_lineas_pedido`.
La pregunta 4 se responde con `COUNT(*)` sobre `obt_vendedores`.

**Justificación.** Mismo criterio que D-12 y C-05: ante una métrica ambigua,
fijar la definición por la pregunta de negocio y publicarla. Un director
comercial que pregunta cuántos vendedores *tenemos* pregunta por el censo, no
por el subconjunto con facturación.

**Alternativa descartada.** Derivar la tabla de las líneas de pedido: más
simple de construir y sistemáticamente corta.

---

### D-45 · Agregación de pagos a grano pedido

**Fecha:** 2026-09-07 · **Estado:** Firme

**Contexto.** D-11 obliga a agregar los pagos a nivel de pedido antes de
unirlos a `obt_pedidos`. Olist admite varios registros de pago por pedido
(tarjeta más vale, pagos fraccionados). Sin regla, `tipo_pago_principal` y
`num_plazos` dependen del orden de llegada y a veces mienten.

**Decisión.**

- `tipo_pago_principal` es el `payment_type` del registro con mayor
  `payment_value`. Empate: el de menor `payment_sequential`.
- `num_plazos` es el `payment_installments` de ese mismo registro.
- `importe_pagado` es la suma de `payment_value` de todos los registros del
  pedido.
- `fue_pagado_a_plazos` es `num_plazos > 1`. Si no hay pagos, las cuatro
  quedan a `NULL`.

**Justificación.** El «método de pago más usado» (pregunta 10) y «pagado a
plazos» (pregunta 17) necesitan un único valor por pedido. Elegir el de mayor
importe identifica el medio con el que se liquidó la mayor parte de la
compra; el sequential desempatador es determinista y coincide con el orden
en que Olist registró los medios.

**Alternativa descartada.** `num_plazos = MAX(payment_installments)` de todos
los pagos del pedido: atribuiría plazos al pedido aunque el pago principal
fuese un boleto a un único vencimiento.

---

### D-46 · Corrección al dimensionado de D-37: la ventana, no las 2.500 fichas

**Fecha:** 2026-09-07 · **Estado:** Firme

**Contexto.** D-37 tomó las 2.500 fichas de P-07 como techo del contrato. Esa
cifra era el tamaño del prefijo sintético con el que se comparó el prefill
en frío contra la caché caliente, no un límite medido. El recuento real del
prefijo, con el tokenizador del modelo, es 2.890. La tabla de control de
`CONTRATO_SEMANTICO.md` lo había etiquetado como «límite medido», redacción
engañosa.

**Decisión.** El criterio de dimensionado del contrato es el ajuste a la
ventana de contexto (4.096), no un número fijo de fichas.

2.890 (prefijo) + ~30 (pregunta) + 120 (respuesta) ≈ 3.040 de 4.096. Cabe.

El orden de recorte de D-37 —primero los ejemplos resueltos; el esquema y
las reglas de negocio no se tocan— aplica solo si se rebasa la ventana. El
umbral de alerta son ~3.200 fichas de prefijo: a partir de ahí hay que
decidir entre recortar o subir la ventana a 6.144, con su coste en KV cache.

**Justificación.** El coste del prefill extra en frío, del orden de 2,5 s a
~145 fichas/s, lo absorbe el precalentamiento de D-34. Con la caché caliente
el tamaño del prefijo es irrelevante: solo se procesa el delta.

**Alternativa descartada.** Recortar los ejemplos para volver a las 2.500
fichas: resolvería un techo que no existe y degradaría el few-shot.

---

### D-47 · Plantilla ChatML en el borde de generación

**Fecha:** 2026-09-08 · **Estado:** Firme

**Contexto.** El Hito 1 evaluó el Nivel 1 con precisión 0. El SQL generado era
en varios casos correcto, pero el modelo no paraba: continuaba el few-shot del
contrato, emitía vallas y una segunda pregunta. Una llamada suelta a
`llama-server` lo reprodujo. El prompt se enviaba como completación cruda
a Qwen2.5-Coder-Instruct; el servidor estaba en `chat_format: Content-only`;
el texto terminaba en `Pregunta: …` sin turno de asistente; las secuencias
de parada eran `<|im_end|>` y `<|endoftext|>`, que ese modo no emite.

**Decisión.** El runtime aplica ChatML en el cliente, sobre `/completion`,
sin delegar la plantilla al servidor:

- mensaje de sistema = contrato semántico íntegro;
- mensaje de usuario = la pregunta (y, si hay reintento, el error), siempre
  al final;
- el turno de asistente queda abierto para que el modelo escriba el SQL.

La cabeza `<|im_start|>system` + contrato + `<|im_end|>` + arranque de
usuario es idéntica byte a byte entre consultas (D-33). Las paradas son
`<|im_end|>` y `<|im_start|>`. Extraer la primera sentencia si llega ruido
es defensa en profundidad, no el control.

**Justificación.** Un modelo de instrucciones genera un turno, no un
documento que continúa. Sin señal de inicio de respuesta, el few-shot del
bloque 7 es el patrón que más se parece a lo ya escrito, y lo prosigue.
Aplicar la plantilla en el cliente es lo que permite conservar D-33 cuando
el servidor no inyecta ChatML.

**Alternativas descartadas.** `/v1/chat/completions` apoyándose en el
servidor: el despliegue está en Content-only y no aplicaría la plantilla.
Meter el contrato en el mensaje de usuario junto con la pregunta: mezclaría
la parte invariante con la variable y pondría en riesgo la caché.

---

### D-48 · El censo no filtra por venta válida

**Fecha:** 2026-09-09 · **Estado:** Firme

**Contexto.** D-44 ya fijó que «vendedores distintos» es el censo de
`obt_vendedores`, no el subconjunto con facturación. La primera pasada del
Nivel 1 mostró el mismo error en otras preguntas de recuento: el modelo
añadía `es_venta_valida` al censo de clientes por estado (pregunta 6), a la
media de reseñas (7), al método de pago más usado (10) y a los pedidos
pagados a plazos (17). Los SQL de referencia ya omitían la bandera. El
few-shot del bloque 7, donde los dos ejemplos con SQL la llevan, es la vía
más plausible de esa generalización (ver D-49).

**Decisión.** Contar clientes, reseñas, métodos de pago o pedidos es un
censo sobre el total, sin filtrar por `es_venta_valida`. La bandera solo
entra cuando la pregunta trata de ventas, importes o facturación. La regla
se declara en el bloque 4 del contrato, junto al párrafo de venta válida.

**Justificación.** Mismo criterio que D-12 y D-44: ante una métrica ambigua,
fijar la definición por la pregunta de negocio y publicarla. Un director
que pregunta cuántos clientes *tenemos* o cuál es el método de pago más
*usado* pregunta por el censo, no por el subconjunto con GMV. Aplicar la
bandera a esos recuentos cambia el número sin fallar, que es el peor tipo
de error. Las preguntas 6, 7, 10 y 17 quedan resueltas con esta regla; sus
SQL de referencia no se tocan porque ya la cumplían.

**Alternativa descartada.** Dejar que cada pregunta decida en silencio.
Reproduce la ambigüedad que D-44 cerró para vendedores y obliga al modelo
de 3B a inferir una frontera que el contrato no nombra.

---

### D-49 · Contraste en el few-shot: un censo sin bandera ni año

**Fecha:** 2026-09-09 · **Estado:** Firme

**Contexto.** Los dos ejemplos con SQL del bloque 7 llevan `es_venta_valida`
y un filtro de año. En la primera pasada el modelo copió ambos a preguntas
que no los pedían: censo con bandera (6, 7, 10, 17) y año 2018 inventado
(11, 15). Borrar los ejemplos no vale: el primero enseña métrica canónica
más bandera más grano; el segundo, ventana, «año pasado» = 2017 y
`obt_lineas_pedido` frente a `obt_vendedores`.

**Decisión.** Se añade un tercer ejemplo con SQL, de tipo censo y sin
expresión temporal, que no lleva ni la bandera ni el año:

```
Pregunta: ¿Cuántos pedidos están en estado shipped?
SELECT COUNT(*) AS num_enviados
FROM obt_pedidos
WHERE estado_pedido = 'shipped';
```

No es ninguna de las 63 preguntas de `Preguntas.md` ni una variante
reconocible de ellas. Ninguna pregunta del catálogo usa el estado
`shipped`; la 8 cuenta `canceled` en 2017. Usar un ítem de evaluación como
ejemplo entrenaría sobre el test.

Los dos ejemplos previos y el de abstención se conservan. El de abstención
pasa a ser el cuarto.

**Justificación.** El contraste tiene que ser visible en el few-shot, no
solo en la prosa del bloque 4. La omisión de la bandera cuenta más si la
tabla *tiene* `es_venta_valida` y el ejemplo no la usa. De ahí
`obt_pedidos` y no `obt_vendedores`.

**Alternativa descartada.** Sustituir uno de los dos ejemplos existentes:
perdería una lección que el otro no cubre. Recortar el few-shot a un solo
ejemplo con SQL: ahorraría fichas y reabriría la contaminación.

---

### D-50 · Execution accuracy es igualdad exacta del conjunto

**Fecha:** 2026-09-09 · **Estado:** Firme

**Contexto.** D-21 fijó *execution accuracy* por comparación de conjuntos
de resultados. En la primera pasada, la pregunta 5 acertó el sentido del
ranking pero no la métrica ni la cardinalidad, y la 10 acertó el método
ganador (`credit_card`) con un recuento distinto. Relajar la métrica a
«acierto del ganador» subiría la cifra sin cambiar lo que el sistema
devuelve. Esa relajación, decidida *después* de ver los fallos, sesgaría
el conjunto hacia lo que ya se sabe que casi funciona, el mismo vicio que
D-21 prohibió al exigir que el SQL de referencia se escriba antes de
observar el sistema.

**Decisión.** La métrica no se relaja: dos consultas aciertan solo si los
conjuntos de filas, tras la canonización del arnés, son iguales. La
pregunta 5 y la 10 siguen contando como fallo aunque acierten el ganador,
y así se reporta. Esta decisión se registra el 2026-09-09, **antes** de
conocer la precisión de la pasada con el contrato 1.1.

Como la 5 fallaba también porque el enunciado no fija cuántas filas
devuelve un ranking sin top-N, el bloque 4 declara: un ranking sin número
explícito devuelve todos los grupos ordenados de mayor a menor, y solo se
limita cuando la pregunta pide los N primeros. Eso precisa el contrato; no
cambia la métrica.

**Justificación.** Un porcentaje que perdona la cardinalidad o las columnas
extra deja de ser falsable. El capítulo de resultados debe poder decir qué
falla y por qué, no inflar el acierto con una métrica más permisiva
elegida a posteriori.

**Alternativa descartada.** Comparar solo la primera columna, o ignorar el
`LIMIT` inyectado. Convertiría en acierto respuestas que no son las que
pide la pregunta y haría incomparable cualquier pasada futura.

---

### D-51 · La pregunta 16 se reformula al grano de pedido

**Fecha:** 2026-09-09 · **Estado:** Firme

**Contexto.** La pregunta 16 pedía «¿Cuántas reseñas de una estrella hemos
recibido?». El SQL de referencia era `COUNT(*) FROM obt_pedidos WHERE
nota_resena = 1`, con alias `num_resenas`. Por D-38, `nota_resena` es la
**media** de las reseñas del pedido. Esa consulta cuenta pedidos cuya
media vale exactamente 1 (11.316) y los etiqueta como reseñas. En el CSV
de origen hay 11.424 reseñas reales de una estrella; 547 pedidos tienen
más de una reseña y 123 tienen media no entera, que quedan fuera de
cualquier comparación con un entero. El modelo, además, generó
`nota_resena = 5`. Familia (a) de la clasificación de fallos del Nivel 1:
la referencia no era válida, con independencia del error del modelo.

**Decisión.** Se reformula al grano real de `obt_pedidos`: «¿Cuántos
pedidos recibieron una valoración media de una estrella?». El alias de la
referencia pasa de `num_resenas` a `num_pedidos`. El bloque 5 del contrato
declara que las reseñas individuales no son contables a grano de pedido.

Esta reformulación **surgió de la evaluación**, no del diseño previo del
catálogo. Se hace porque la pregunta original es irresoluble con el grano
declarado: no existe una fila por reseña, y fingir que `nota_resena = 1`
cuenta reseñas mentiría en el resultado y en el nombre de la columna.
Cambiar un ítem después de ver resultados es el sesgo que D-21 prohíbe
cuando se hace para que el sistema acierte; aquí se hace para que el ítem
deje de preguntar algo que Gold no puede responder. El error del modelo
(`= 5`) queda como dato de la primera pasada; la pregunta nueva se evalúa
en la pasada del contrato 1.1.

**Justificación.** D-38 ya había elegido la media y el tipo `DECIMAL`.
Mantener el enunciado original habría obligado o bien a inventar grano de
reseña —una quinta OBT, descartada por D-11 y por calendario— o bien a
seguir evaluando una mentira. Declarar la limitación en el bloque 5 es
coherente con las demás ausencias: lo que no existe se nombra, no se
disimula.

**Alternativa descartada.** Dejar el enunciado y cambiar solo el alias.
El texto seguiría pidiendo reseñas y el SQL seguiría contando pedidos.

---

### D-52 · Ablación 3B frente a 7B: adherencia a D-48

**Fecha:** 2026-09-09 · **Estado:** Firme

**Contexto.** Tras D-48 el contrato 1.1 declara que el censo no filtra por
`es_venta_valida`. El modelo de 3B no aplicó la regla: 8 de 18 consultas
del Nivel 1 llevaban la bandera en preguntas que no tratan de ventas ni
importes. Quedaba abierta la hipótesis de que el fallo era de capacidad
de seguimiento de instrucciones, no del contrato. D-21 y D-29 ya
preveían el tamaño de modelo como eje de ablación.

**Diseño.** Una sola variable: el peso del modelo. Contrato 1.1, catálogo
de Nivel 1, SQL de referencia y arnés de comparación permanecen fijos.
Ambos GGUF son Qwen2.5-Coder-Instruct Q4_K_M, `n_ctx` 4096, 6 hilos,
`llama-server` en `127.0.0.1:8080`. El 3B y el 7B no coexisten (C-03).

El arnés registra metadatos de servidor y, como indicador de D-48, el
recuento de SQL generados que contienen `es_venta_valida` cuando la
pregunta no trata de ventas, importes o facturación. La detección es
léxica sobre el enunciado (`venta|vend|factur|importe|ingreso|ticket|gmv|gasto|envío|flete|precio|caro`).
La métrica de acierto no se relaja (D-50).

Cada pasada se etiqueta (`nivel1_3b.json`, `nivel1_7b.json`). La pasada
3B se repitió con metadatos; el `nivel1.json` previo no es comparable.

**Resultados.**

| | 3B Q4_K_M | 7B Q4_K_M |
|---|---|---|
| Precisión Nivel 1 | 7/18 = 0,3888888888888889 | 13/18 = 0,7222222222222222 |
| `es_venta_valida` espurio | 8 (1, 6, 7, 8, 9, 10, 14, 17) | 2 (9, 10) |
| Prefill medio (fichas/s) | 27,88 | 12,77 |
| Generación media (fichas/s) | 9,63 | 4,78 |
| Latencia media por pregunta (ms) | 4.171 | 8.804 |

Preguntas que el 7B acierta y el 3B no: 1, 6, 7, 8, 14, 17. Las seis
eran censo con bandera espuria en el 3B; el 7B omite la bandera y el
conjunto coincide con la referencia.

**Regresiones:** ninguna. Las siete que el 3B acertaba (2, 3, 4, 11,
12, 16, 18) las acierta el 7B.

Siguen en fallo ambos: 5 (el 7B agrupa por `macro_categoria` en lugar
de `categoria_producto`), 9 y 10 (siguen con bandera espuria), 13
(`importe_pagado` en lugar de `importe_articulos`), 15 (el 7B acierta
el mes con `DATE_TRUNC` pero añade `RANK()`, y D-50 compara el conjunto
completo).

**Interpretación.** La hipótesis se sostiene en lo sustancial: pasar de
3B a 7B reduce el incumplimiento de D-48 de 8 a 2 y sube la precisión
en 6 aciertos, todos ellos de censo. No desaparece del todo: el 7B
sigue aplicando la bandera a la media de entrega (9) y al método de
pago más usado (10). El seguimiento de instrucciones mejora con el
tamaño; no es perfecto. El coste es el previsto en D-29: generación
unas dos veces más lenta y latencia media que se duplica.

**Alternativa descartada en el momento de la medición.** Dar el 7B por
cerrado el Hito 1 y abandonar el 3B. Esa frase queda superada el mismo día
por D-53: el 7B pasa a ser el modelo del sistema; el 3B permanece como
brazo de la ablación. No se borra esta pasada: es el punto 3B de la curva.

---

### D-53 · El 7B es el modelo del sistema; el 3B, el brazo de ablación

**Fecha:** 2026-09-09 · **Estado:** Firme

**Contexto.** D-29 eligió 3B para desarrollar y 7B solo como punto de la
curva. D-52 midió Nivel 1 con contrato 1.1, mismas preguntas y mismo arnés:
7/18 frente a 13/18, `es_venta_valida` espurio de 8 a 2, latencia media de
4,2 s a 8,8 s, ninguna regresión. WSL2 tiene 7,8 GB; el GGUF del 7B ocupa
unos 4,7 GB.

**Decisión.** Qwen2.5-Coder-7B-Instruct Q4_K_M es el modelo del runtime, de
la evaluación de los hitos siguientes y de la demostración. El 3B se
conserva en `~/modelos/` y en `evaluacion/resultados/nivel1_3b.json` como
brazo de D-21. Los dos servidores no coexisten: hay que apagar uno antes
de levantar el otro. Durante los Hitos 3 a 5 el orden es construir la
plataforma con el modelo parado y consultar con la plataforma parada.

**Justificación.** El incumplimiento de D-48 era sobre todo capacidad de
seguimiento de instrucciones. Quedarse en 3B haría del contrato un texto
que el sistema no cumple. 8,8 s por pregunta son usables en una interfaz
analítica. El 3B no se tira: sin él no hay ablación.

**Alternativa descartada.** Seguir desarrollando en 3B y cambiar a 7B solo
en el Hito 7. Mediría mal los niveles 2 y 3, porque el cuello de botella
del 3B ya está cuantificado.

---

### D-54 · Alcance del Hito 2: qué preguntas tienen referencia ahora

**Fecha:** 2026-09-09 · **Estado:** Firme

**Contexto.** El Hito 2 exige SQL de referencia para Niveles 2 y 3 y para
el bloque de abstención. Gold del Hito 1 materializa tres OBT. Cuatro
preguntas del catálogo piden fuentes del Hito 4; dos están descartadas
por D-16; `importe_articulos_eur`, `id_transportista`, `tipo_incidencia` y
las columnas de captación siguen a NULL (D-43).

**Decisión.** El conjunto de evaluación del Hito 2, hasta que existan las
fuentes del Hito 4, es el grupo (a) más 56–63. No se escribe referencia
para (b) ni para las descartadas. La 43 no recibe SQL: el contrato no
define «cancelación antes de facturar».

**(a) Respondibles con las tres OBT.** 19–42 y 44–46.

**(b) Hito 4.** 47 y 48 (eventos logísticos), 50 y 51 (`obt_embudo_web`),
53 y 54 (Marketing Funnel; columnas a NULL), 55 (tipo de cambio;
`importe_articulos_eur` a NULL).

**(c) Sin SQL ahora.** 49 y 52 (D-16). 43 (definición ausente).

**56–63.** 56–59 se abstienen. 60 y 61 son SELECT con una línea de
supuesto. 62 resuelve el grano en `obt_pedidos`. 63 es un `DELETE` que
rechaza el validador, no el modelo.

**Definiciones que no están en el contrato y se anotan, no se cierran.**
24: cerrada en D-56. 33 y 37: cerradas en D-55. 27: crecimiento relativo, no delta. 40: solo clientes con primera compra hasta 2018-01-17 (nueve meses de
observación). 61: semana natural de DuckDB (lunes 2018-10-15); esa
semana no tiene venta válida, el resultado es 0. 62: columna
`importe_total`, no GMV. 30, 42 y 46 superan las 1.000 filas del
validador: el arnés verá un recorte, no el censo.

**Justificación.** Escribir referencia contra columnas NULL o contra
`obt_embudo_web` haría pasar el `EXPLAIN` y mentiría el resultado (D-43).
Inventar la 43 para tener cobertura inflaría el Nivel 3.

**Alternativa descartada.** Incluir 47–55 con SQL que lee NULL y devuelve
vacío. El vacío no es abstención y contaminaría la precisión.

---

### D-55 · «Informática» no es la macro Electrónica e Informática

**Fecha:** 2026-09-09 · **Estado:** Firme

**Contexto.** Las preguntas 33 y 37 piden informática. El SQL de 75875af
filtró `macro_categoria = 'Electrónica e Informática'`, el conjunto que el
bloque 4 reserva a «electrónica» (pregunta 60). En Gold, últimos 6 meses,
la macro suma 475.821 €; `informatica_acessorios` + `pcs` + `pc_gamer`
suman 246.874 €.

**Decisión.** Informática = `categoria_producto IN ('informatica_acessorios',
'pcs', 'pc_gamer')`. La macro queda para la pregunta 60. Se reescriben
`33.sql` y `37.sql`. No se toca el prefijo del contrato.

**Justificación.** El bloque 4 resuelve con macro un término castellano que
cubre varias categorías de origen; el ejemplo canónico es «electrónica».
Informática es un subconjunto (accesorios y PCs), no telefonía, audio ni
consolas. Dejar la macro haría fallar D-50 a un modelo que sigue el contrato.

**Alternativa descartada.** Conservar la macro y declararla en un comentario.
Colapsaría 33 y 60 al mismo mapeo y mediría solo la ventana temporal.

---

### D-56 · São Paulo en la pregunta 24 es la UF, no la ciudad

**Fecha:** 2026-09-09 · **Estado:** Firme

**Contexto.** La pregunta 24 pide comparar las ventas de São Paulo con las
del resto del país. El SQL de 75875af ya filtra `estado_cliente = 'SP'`.
En Gold, venta válida, la UF suma 5,16 M frente a 8,33 M del resto; la
ciudad `sao paulo` suma 1,90 M frente a 11,60 M. La pregunta 13 («qué
ciudad nos genera más ingresos») ya responde por `ciudad_cliente`.

**Decisión.** São Paulo en la 24 es la UF `SP`. `24.sql` no se toca. No se
toca el prefijo del contrato.

**Justificación.** «El resto del país» parte el territorio en dos, y en
Brasil esa partición es el estado de São Paulo frente al resto de las UF,
no una ciudad frente a todo el país. La 13 ya cubre el grano ciudad; usar
ciudad otra vez en la 24 duplicaría el ítem y cambiaría el resultado
(1,90 M / 11,60 M en lugar de 5,16 M / 8,33 M).

**Alternativa descartada.** Reescribir la 24 a `ciudad_cliente`. Haría de
la 13 y la 24 la misma pregunta con distinto recorte geográfico, y Joan
cerró UF.

---

## 5. Conclusiones técnicas

Hallazgos derivados del diseño, con valor para el capítulo de resultados.

### C-01 · Una OBT única no es viable con granos heterogéneos

El agrupamiento de las 63 preguntas por columnas requeridas produce cuatro
granos distintos: pedido, línea de detalle, entidad maestra y telemetría. Los
pedidos y el clickstream difieren en varios órdenes de magnitud en volumen, y
forzarlos en una tabla única o explota en filas o obliga a preagregar perdiendo
detalle.

**Formulación defendible.** El patrón correcto no es el esquema en estrella ni
la OBT universal, sino un conjunto acotado de OBT por proceso de negocio, con el
grano declarado y el enrutado explícito en el contrato semántico.

---

### C-02 · Los huecos del dataset justifican la arquitectura de ingesta

Cuatro de las dieciséis preguntas de negocio iniciales resultaron no
respondibles con Olist: coste del transportista, identidad del operador
logístico, incidencias de extravío y daño, y devoluciones. Todas son telemetría
operativa ausente de un núcleo transaccional.

**Valor.** Convierte la justificación de la capa de streaming de "el máster
enseña Kafka" a "los requisitos funcionales exigen eventos operativos que el
core no registra". Es diseño dirigido por requisitos.

---

### C-03 · El presupuesto real de memoria es de 6 a 7 GB, no de 16

El equipo declara 16 GB instalados y **12,7 GB usables**; la diferencia
corresponde en su mayor parte al frame buffer de la gráfica integrada. Descontando
el sistema operativo, el IDE y la sobrecarga de Docker Desktop con WSL2, el
presupuesto disponible para contenedores es de unos 6 GB con el entorno de
desarrollo abierto y unos 7,5 GB cerrándolo.

**Consecuencias.** El presupuesto de recursos debe expresarse como pico
concurrente por perfil de ejecución, no como suma de límites de contenedor. Y
OpenMetadata, cuyo despliegue mínimo requiere del orden de 4 a 6 GB, no puede
coexistir con ningún otro perfil.

**Acción posible.** Reducir el *UMA Frame Buffer Size* en BIOS a 512 MB podría
recuperar entre 1 y 2 GB, dado que la gráfica integrada no se emplea para
cómputo.

---

### C-04 · La caché de prefijo de prompt es un requisito, no una optimización

**Confirmada empíricamente el 2026-09-01** con un prefijo sintético de 2.540
fichas (prefill en frío 17.541 ms; con caché, 72–1.253 ms) y **replicada el
2026-09-07** con el prefijo real del contrato, 2.890 fichas. Ver anexo de P-07.

En inferencia por CPU, el coste dominante no es la generación sino el
procesamiento del prompt. Con un contexto semántico de unos 2.000 tokens, el
retardo hasta el primer carácter se mide en decenas de segundos.

Como el contrato semántico es un artefacto estático (D-06), el prefijo del
prompt es idéntico entre consultas y su KV cache es reutilizable: el
procesamiento por consulta se reduce a la pregunta del usuario.

**Consecuencia doble.** Es lo que hace el sistema usable en demo, y lo que hace
que la evaluación completa —del orden de 500 generaciones entre ablaciones y
reintentos— quepa en el calendario.

**Observación arquitectónica.** Una decisión tomada por reproducibilidad y
gobierno resulta ser también la que resuelve el rendimiento. Merece un párrafo
en la memoria.

---

### C-05 · Olist describe un marketplace transaccional, no recurrente

Aproximadamente un 3 % de los clientes realiza más de una compra. Los análisis
de cohortes y de valor de vida del cliente resultarán casi planos.

**Tratamiento.** No es un defecto del sistema sino una característica del
negocio, y como tal debe reportarse. Adicionalmente, `customer_id` es único por
pedido mientras que `customer_unique_id` identifica a la persona: usar el
primero hace que todos los clientes parezcan nuevos. Es un error frecuente con
este dataset y está incluido deliberadamente en el conjunto de evaluación.

---

### C-06 · `EXPLAIN` no es un control de coste

DuckDB no expone mediante `EXPLAIN` una métrica de coste sobre la que fijar un
umbral. Sí fuerza el *binding* del plan sin ejecutar la consulta, lo que
constituye una validación semántica autoritativa de la existencia de tablas y
columnas.

**Corrección.** El componente se conserva, reetiquetado como validación
semántica sin ejecución. El control de recursos se traslada a mecanismos duros
(D-19, capa 4).

---

### C-07 · El espacio en disco es tan restrictivo como la memoria

El equipo dispone de unos 51 GB libres sobre 477. Entre la base de WSL2 y
Docker, las imágenes del stack y los modelos GGUF, el margen para datos es
estrecho, y el disco virtual de WSL2 no se reduce automáticamente al borrar
ficheros.

**Consecuencia favorable.** Es un argumento sólido y honesto para el
almacenamiento remoto de Bronze y Silver: no es un adorno arquitectónico, es lo
que hace viable el proyecto en este equipo.

**Consecuencia metodológica.** El benchmark comparativo entre motores debe
ejecutarse sobre disco local. Ejecutado contra almacenamiento remoto mediría el
ancho de banda de la conexión, no los motores.

---

### C-08 · En 3B, los ejemplos mandan más que las reglas en prosa

Tras escribir D-48 en el bloque 4, el 3B siguió aplicando `es_venta_valida`
a censos. El few-shot del bloque 7 tenía dos SQL con la bandera y el año;
añadir un tercero sin ellos (D-49) no invirtió el patrón: la precisión
pasó de 6/18 a 7/18 y la pregunta 1 **regresó**. El 7B sí aplica D-48 en
lo sustancial (espurios de 8 a 2).

**Formulación defendible.** Un contrato semántico no se cumple solo porque
esté escrito. A 3.000 millones de parámetros, el few-shot pesa más que un
párrafo normativo. El tamaño del modelo es una variable de gobernanza, no
solo de calidad de SQL.

---

### C-09 · Las latencias no se comparan entre Windows, WSL2 ni cupos de CPU

El `.wslconfig` limitaba WSL2 a 4 procesadores sobre un Ryzen 5 6600H de 6
núcleos físicos. Con 4 CPU, generación ~5,5 fichas/s (2026-09-07). Con 6
CPU, ~9,6 fichas/s en el 3B de D-52. El prefill en frío de Windows nativo
(144,8 fichas/s, 2026-09-01) no es comparable al de WSL2.

**Consecuencia.** En la memoria, cada cifra de latencia lleva entorno,
hilos y fecha. Lo replicable entre fechas es *si la caché opera*, no el
milisegundo.

---

### C-10 · El 0/18 del primer arnés fue fontanería, no el modelo

Las 18 preguntas del Nivel 1 generaron SQL a menudo correcto envuelto en
vallas markdown y en una segunda consulta. Causa: completación cruda a un
modelo Instruct, sin ChatML, con paradas que ese modo no emite (D-47).
Tras ChatML, las 18 pasan el validador. La precisión 0 no se reporta como
fracaso del enfoque NL-to-SQL.

---

### C-11 · Un saldo neto oculta regresiones

El contrato 1.1 se reportó como 6/18 → 7/18. En esa pasada la pregunta 1
pasó de acierto a fallo (`COUNT` con `es_venta_valida`). D-50 y el arnés
con `--etiqueta` existen para que el capítulo de resultados nombre qué
cambia de veredicto, en los dos sentidos.

---

## 6. Riesgos identificados

| Id | Riesgo | Mitigación |
|---|---|---|
| R-01 | OpenMetadata no cabe en el presupuesto de memoria junto a otros perfiles | D-06 lo saca del runtime; se ejecuta en un perfil aislado y puntual |
| R-02 | Latencia de inferencia en CPU incompatible con la demo y la evaluación | C-04; medición previa antes de fijar el diseño del prompt |
| R-03 | Divergencias no comunicadas respecto a la propuesta aprobada | P-04 |
| R-04 | Agotamiento de espacio en disco | C-07; política de `VACUUM` en Delta y control del tamaño del generador |
| R-05 | Confusión entre dato real y simulado ante el tribunal | Identificación explícita en la memoria; los resultados de negocio se apoyan en dato real |
| R-06 | Integración de Spark con ADLS consume calendario | D-07; ruta configurable y plan B local |
| R-07 | Soporte de lectura Delta desde DuckDB según versión | D-10; plan B con copia en Parquet plano |
| R-08 | El 7B (~4,7 GB) y la plataforma no caben a la vez en 7,8 GB de WSL | D-53; perfiles secuenciales: construir o consultar, no ambos |
| R-09 | Crédito del chat de arquitectura agotado antes de la entrega | `memoria/FUENTE.md` + `HANDOFF.md`; el usuario lidera con `ROADMAP.md` |

---

## 7. Decisiones pendientes

| Id   | Cuestión                                                                                           | Estado                                                 |
| ---- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| P-01 | Amplitud de orígenes y formatos                                                                    | **Resuelta** → D-27. Indicación expresa de los tutores |
| P-02 | Tipo de acceso a Azure                                                                             | **Resuelta** → D-28. Azure for Students                |
| P-03 | Elección de modelo y medición de latencia                                                          | **Resuelta** → D-29. 3B primero, 7B como ablación      |
| P-04 | Comunicación a los tutores de las divergencias D-02, D-03, D-04 y D-11                             | **Resuelta** — enviada el 2026-09-01                   |
| P-05 | Mapeo de macro-categorías                                                                          | **Resuelta** → D-30                                    |
| P-06 | Política de retención en Delta                                                                     | **Resuelta** → D-31                                    |
| P-07 | Medición de latencia de prefill con y sin caché de prefijo, para dimensionar el contrato semántico | **Resuelta** — 2026-09-01 (sintético) y 2026-09-07 (prefijo real); ver anexo |
| P-08 | Base documental como quinto origen de datos                                                        | **Resuelta** → D-32. Se incorpora                      |
| P-09 | Triaje de alcance del Hito 2 (preguntas 19–55 y abstención)                                        | **Pendiente** — primer paso del Hito 2                 |
| P-10 | El 7B como modelo del sistema tras la ablación                                                     | **Resuelta** → D-53                                    |

---

## Anexo · Protocolo de medición de latencia de inferencia (P-07)

**Objetivo.** Determinar cuántos tokens puede permitirse el contrato semántico
sin que la latencia haga inviables la demostración y las pasadas de evaluación.

**Magnitudes a medir.** El coste de la inferencia en CPU se descompone en dos
fases con comportamientos distintos:

- **Prefill** (procesamiento del prompt): tiempo hasta el primer token
  generado. Escala con el tamaño del prompt y está limitado por cómputo.
- **Generación**: tokens por segundo una vez iniciada la respuesta. Está
  limitada por el ancho de banda de memoria y es prácticamente independiente
  del tamaño del prompt.

**Hipótesis a validar.** Al ser el contrato semántico un artefacto estático
(D-06), el prefijo del prompt es idéntico entre consultas y su caché de KV es
reutilizable, por lo que el prefill por consulta debería reducirse al número de
tokens de la pregunta.

**Protocolo.**

1. Servir el modelo con `llama-server`, un único slot, hilos igualados a los
   núcleos físicos.
2. Construir un prefijo sintético de aproximadamente 2.000 tokens que emule el
   volumen previsto del contrato semántico. La réplica del 2026-09-07 sustituye
   ese sintético por el prefijo real del contrato (2.890 fichas).
3. Ejecutar tres peticiones al endpoint `/completion`, con `temperature = 0`:
   - **A** — prefijo + pregunta 1, con `cache_prompt = false` (referencia en
     frío).
   - **B** — prefijo + pregunta 1, con `cache_prompt = true` (primera carga).
   - **C** — prefijo + pregunta 2, con `cache_prompt = true` (caché caliente).
4. Registrar de la respuesta JSON: `prompt_n`, `prompt_ms`, `predicted_n` y
   `predicted_ms`.

**Criterio de decisión.**

| Observación | Consecuencia sobre el diseño |
|---|---|
| El prefill de C cae respecto al de B en al menos un orden de magnitud | La caché opera. El contrato semántico puede alcanzar entre 2.000 y 3.000 tokens |
| El prefill de C no cae | La caché no opera: revisar que el prefijo sea idéntico byte a byte y que solo haya un slot activo |
| Generación por debajo de 10 tokens/s | Recortar la longitud máxima de respuesta y definir secuencias de parada |

**Restricción de diseño derivada.** La caché solo se reutiliza si el prefijo es
idéntico byte a byte. Por tanto, **toda porción variable del prompt debe
situarse al final**: la pregunta del usuario, la marca de tiempo y el
historial. Interpolar cualquier valor variable dentro del contrato semántico
invalida la caché en cada consulta. Es una restricción arquitectónica sobre el
diseño del prompt, no un detalle de implementación.

**Los resultados de esta medición son material del capítulo de resultados de la
memoria.**

---

### Resultados obtenidos · 2026-09-01

**Entorno.** AMD Ryzen 5 6600H, 6 núcleos físicos, 16 GB de RAM instalada y
12,7 GB visibles. Windows 11. Inferencia exclusivamente por CPU.
`llama-server` build 10730 (commit 09412af38), compilado con Clang 20.1.8.
Modelo Qwen2.5-Coder-3B-Instruct en cuantización Q4_K_M. Ventana de contexto
4.096, seis hilos, un único slot. Prefijo sintético de 2.540 tokens, 120 tokens
de generación por petición, temperatura 0.

| Escenario | Tokens de prompt procesados | Prefill (ms) | Prefill (tok/s) | Generación (tok/s) | Total (ms) |
|---|---|---|---|---|---|
| A — en frío, sin caché | 2.540 | 17.541 | 144,8 | 15,1 | 25.578 |
| B — misma pregunta, caché poblada | 1 | 72 | — | 15,2 | 7.925 |
| C — caché caliente, pregunta distinta | 10 | 1.253 | — | 15,1 | 9.131 |
| D — caché caliente, tercera pregunta | 13 | 266 | — | 15,2 | 8.096 |

**Huella de memoria.** El proceso `llama-server` sostiene 2.539 MB de memoria
privada con el modelo cargado y el contexto en uso, dejando 6,4 GB libres en el
sistema. Es coherente con el presupuesto de C-03 y deja margen suficiente para
DuckDB y la interfaz, siempre que la plataforma de datos no se ejecute
simultáneamente.

**Interpretación.**

1. *La caché de prefijo opera y su efecto es de un orden de magnitud.* Se
   cumple el criterio de decisión previsto: el prefill cae de 17,5 segundos a
   una fracción de segundo. El contrato semántico puede por tanto dimensionarse
   con holgura en el entorno de los 2.500 tokens sin penalizar la latencia en
   régimen permanente. Queda formalizado en D-33.

2. *El cuello de botella se desplaza del prefill a la generación.* Los 15,1
   tokens por segundo se mantienen prácticamente constantes en las cuatro
   tiradas, con una dispersión inferior al 1 %, y son independientes del tamaño
   del prompt, tal como predecía la hipótesis. En régimen permanente, más del
   85 % del tiempo de respuesta es generación. De ahí D-35.

3. *El coste en frío no desaparece, se reubica.* Los 17,5 segundos siguen
   existiendo y los paga quien inicie la primera consulta tras arrancar el
   servicio. De ahí el precalentamiento de D-34.

4. *Margen de contexto.* Con 2.540 tokens de contrato, la pregunta y 120 de
   respuesta, se ocupan unos 2.700 de los 4.096 disponibles. El margen es
   suficiente pero no amplio: si el contrato creciera por encima de los 3.000
   tokens habría que ampliar la ventana, con el consiguiente coste en KV cache.

**Nota de reproducibilidad.** Los binarios de `llama.cpp` distribuidos vía
`winget` fallaron inicialmente con violación de acceso en `MSVCP140.dll`
14.36.32532.0. La causa era un Visual C++ Redistributable desactualizado en el
host, ajeno al proyecto. Es un ejemplo concreto de dependencia implícita del
sistema operativo y constituye una justificación empírica del uso de
contenedores para el runtime de inferencia.

---

### Resultados obtenidos · 2026-09-07 · prefijo real

Misma prueba, sustituyendo el prefijo sintético de 2.540 fichas por el
prefijo real del contrato (2.890 fichas, 2.904 al concatenar la primera
pregunta). Protocolo A–D idéntico: `temperature = 0`, `n_predict = 120`,
`cache_prompt` según el escenario.

**Entorno.** WSL2 sobre el mismo anfitrión (AMD Ryzen 5 6600H, 6 núcleos
físicos). Inferencia por CPU. `llama-server` en `127.0.0.1:8080`, ventana
4.096, un único slot. Qwen2.5-Coder-3B-Instruct Q4_K_M. No es el mismo
binario ni el mismo sistema operativo que el 2026-09-01 (entonces Windows
nativo): las magnitudes absolutas no son comparables entre fechas; sí lo es
si la caché opera.

| Escenario | Tokens de prompt procesados | Prefill (ms) | Prefill (tok/s) | Generación (tok/s) | Total (ms) |
|---|---|---|---|---|---|
| A — en frío, sin caché | 2.904 | 62.022 | 46,8 | 5,5 | 83.979 |
| B — misma pregunta, caché poblada | 1 | 181 | 5,5 | 5,5 | 21.998 |
| C — caché caliente, pregunta distinta | 9 | 444 | 20,3 | 5,5 | 22.262 |
| D — caché caliente, tercera pregunta | 8 | 404 | 19,8 | 5,5 | 22.287 |

**Interpretación.**

1. *La caché opera también con el prefijo real.* El prefill cae de 62 s a
   0,18–0,44 s (reducción del 99 % o más). D-33 y D-34 siguen en pie: el
   usuario no paga el prefijo, y el arranque sí.

2. *El tamaño extra no se lee en esta tabla.* A 145 fichas/s del 2026-09-01,
   pasar de 2.540 a 2.904 habría costado unos 2,5 s más en frío. Aquí el
   prefill en frío es 3,5 veces más lento que en Windows nativo (46,8
   frente a 144,8 fichas/s), de modo que esa diferencia de 364 fichas queda
   ahogada por el peaje de WSL2. La generación también: 5,5 fichas/s frente
   a 15,1; 120 fichas de respuesta son ~22 s en WSL y ~8 s en el anfitrión.

3. *Cabe en la ventana.* 2.904 de prompt más 120 de respuesta son ~3.024 de
   4.096. El umbral de alerta de D-46 (~3.200 de prefijo) no se alcanza.

4. *El techo no era 2.500.* Las 2.500 fichas de P-07 eran el sintético de la
   prueba, no un límite. Queda formalizado en D-46.

---

### Resultados obtenidos · 2026-09-09 · prefijo 1.1 (D-48 a D-51)

Misma prueba A–D sobre el prefijo tras D-48, D-49, D-50 y D-51. Protocolo
idéntico: `temperature = 0`, `n_predict = 120`, `cache_prompt` según el
escenario. La caché del prefijo 1.0 queda invalidada.

**Entorno.** WSL2, `llama-server` en `127.0.0.1:8080`, ventana 4.096, un
único slot. Qwen2.5-Coder-3B-Instruct Q4_K_M. Recuento del prefijo:
3.067 fichas (2.890 el 2026-09-07). El primer prompt, con ChatML y la
pregunta 1, ocupa 3.094.

| Escenario | Tokens de prompt procesados | Prefill (ms) | Prefill (tok/s) | Generación (tok/s) | Total (ms) |
|---|---|---|---|---|---|
| A — en frío, sin caché | 3.094 | 98.268 | 31,5 | 10,2 | 100.231 |
| B — misma pregunta, caché poblada | 1 | 92 | 10,9 | 10,9 | 1.933 |
| C — caché caliente, pregunta distinta | 14 | 468 | 29,9 | 10,9 | 2.669 |
| D — caché caliente, tercera pregunta | 13 | 441 | 29,5 | 10,3 | 3.729 |

**Interpretación.**

1. *La caché opera con el prefijo 1.1.* El prefill cae de 98 s a
   0,09–0,47 s. D-33 y D-34 siguen en pie tras invalidar la caché.

2. *El umbral de D-46 no se alcanza.* 3.067 de prefijo quedan por debajo
   de ~3.200. 3.094 de prompt más 120 de respuesta son ~3.214 de 4.096.

3. *Las magnitudes absolutas no se comparan con el 2026-09-07.* La
   generación salió a ~10 fichas/s frente a 5,5; el prefill en frío, a
   31,5 frente a 46,8. Lo que se replica es si la caché opera, no el
   milisegundo.

Afirmaciones de los documentos previos que deben reescribirse por ser
técnicamente demasiado absolutas o imprecisas.

| Formulación actual | Problema | Reformulación propuesta |
|---|---|---|
| "Los LLM tienen rendimiento deficiente generando JOINs" | Absoluta y sin respaldo | "Se reduce la complejidad de generación mediante una capa analítica denormalizada, disminuyendo la necesidad de que el modelo resuelva relaciones entre entidades durante la generación" |
| "Elimina por completo la costosa computación de JOIN" | El coste se traslada al tiempo de construcción, no desaparece | "Traslada el coste de la resolución de relaciones del tiempo de consulta al tiempo de construcción" |
| "Kafka asegura la tolerancia a fallos" | Con un único broker y factor de replicación 1, no la hay | "Kafka aporta desacoplamiento, gestión de offsets y capacidad de replay; la tolerancia a fallos queda fuera del alcance por la topología de nodo único" |
| "Capa Semántica" | Una capa semántica es un artefacto ejecutable que compila métricas a SQL | "Contrato semántico declarativo" |
| "Arquitectura RAG" | Con una superficie que cabe en contexto no hay recuperación | "Metadata-Grounded NL-to-SQL: inyección estática de contexto semántico compilado" |
| "Agregaciones en milisegundos" | Superlativo no medido | Sustituir por la latencia medida |
| "Hiper-optimizado genéticamente" | Sin significado técnico | Eliminar |
| "Migración a Kubernetes si hay sobrecarga" | Inviable con el presupuesto de memoria real | Retirar; mencionar como línea futura de escalabilidad si procede |
