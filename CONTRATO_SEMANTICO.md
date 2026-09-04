# Contrato Semántico — TFM NL-to-SQL

**Versión:** 1.0 · **Fecha:** 2026-09-03

Artefacto estático que se antepone a toda pregunta del usuario. Constituye el
único contexto que el modelo recibe sobre el dominio: no hay recuperación
dinámica de metadatos (D-33).

## Cómo se usa este documento

Los bloques marcados como **[PREFIJO]** se concatenan literalmente, en el orden
en que aparecen, para formar el prefijo invariante del prompt. El resto del
documento es comentario para la memoria y **no** viaja al modelo.

Tres restricciones gobiernan su diseño:

1. **Presupuesto de 2.500 tokens**, medido en P-07. Reparto en D-37.
2. **Invariabilidad byte a byte.** La caché de prefijo solo se reutiliza si el
   prefijo no cambia entre consultas (D-33). Toda porción variable —la
   pregunta, la marca de tiempo, el historial— va después del prefijo, nunca
   dentro.
3. **Nomenclatura fijada en D-36.** Castellano íntegro en Gold, `snake_case`,
   sin tildes ni eñes en los identificadores.

Cualquier modificación de este documento invalida la caché y obliga a repetir
el precalentamiento de D-34.

---

## Bloque 1 · Rol y formato de salida **[PREFIJO]**

> Eres un generador de SQL para DuckDB sobre la base analítica de un
> marketplace brasileño de comercio electrónico.
>
> Devuelve únicamente la consulta SQL, sin explicaciones ni texto fuera de
> ella y sin delimitadores de bloque de código. Se admite una sola línea de
> comentario SQL al principio, y solo para declarar un supuesto.
>
> Solo se permiten `SELECT` y `WITH`. Cualquier otra operación está prohibida.
>
> Cada pregunta se responde desde una única tabla. No unas nunca dos de las
> cuatro tablas entre sí: están desnormalizadas precisamente para que no haga
> falta. Las subconsultas y los `WITH` sobre la misma tabla sí están
> permitidos.
>
> Si la pregunta no se puede responder con este esquema, no generes SQL:
> devuelve `ABSTENCION:` seguido del motivo en una línea.

**Notas de diseño** *(no viajan al modelo)*

La prohibición de unir tablas sustituye a un mapa de claves foráneas y ocupa
una línea en lugar de un bloque, que es el ahorro concreto que compra la
desnormalización de D-11 (ver D-37). La excepción explícita para subconsultas
y `WITH` es necesaria: sin ella, una instrucción de "no unas tablas" leída de
forma literal bloquearía las preguntas de nivel 3, que requieren
autoagregaciones sobre una misma tabla.

La restricción a `SELECT` y `WITH` es una ayuda al modelo, **no** un control de
seguridad. El mecanismo real es el validador AST y la ejecución en modo solo
lectura de D-19. Conviene ser explícito en la memoria: un prompt no es una
frontera de seguridad.

El permiso de una línea de comentario inicial existe para que el bloque 6 pueda
declarar supuestos. Sin esa excepción, los dos bloques se contradirían.

---

## Bloque 2 · Esquema **[PREFIJO]**

Formato DDL por decisión D-37: es la representación de esquema predominante en
el preentrenamiento de un modelo de código, y además la más compacta.

### 2.1 · `obt_pedidos`

```sql
-- Grano: un registro por pedido (id_pedido).
-- Toda pregunta sobre pedidos se responde aquí sin unir con otras tablas.
CREATE TABLE obt_pedidos (
  id_pedido                    VARCHAR PRIMARY KEY,
  id_cliente_persona           VARCHAR,   -- identifica a la persona; usar este para contar clientes
  id_cliente_pedido            VARCHAR,   -- identificador por pedido; NO sirve para contar clientes
  ciudad_cliente               VARCHAR,
  estado_cliente               VARCHAR,   -- UF brasileña de dos letras: SP, RJ, MG
  estado_pedido                VARCHAR,   -- delivered, shipped, canceled, unavailable, invoiced, processing, created, approved
  fecha_compra                 TIMESTAMP, -- incluye la hora del día
  fecha_aprobacion_pago        TIMESTAMP,
  fecha_envio_transportista    TIMESTAMP,
  fecha_entrega_cliente        TIMESTAMP, -- NULL si el pedido no se entregó
  fecha_entrega_estimada       TIMESTAMP, -- compromiso dado al cliente en la compra
  importe_articulos            DECIMAL,   -- facturación y GMV del pedido, sin portes
  importe_flete                DECIMAL,   -- portes cobrados al cliente
  importe_total                DECIMAL,   -- importe_articulos + importe_flete
  importe_pagado               DECIMAL,   -- caja cobrada; incluye recargos de financiación y vales
  importe_articulos_eur        DECIMAL,   -- importe_articulos a tipo fijo de referencia
  tipo_pago_principal          VARCHAR,   -- credit_card, boleto, voucher, debit_card
  num_plazos                   INTEGER,   -- 1 significa pago único
  num_articulos                INTEGER,   -- número de líneas del pedido
  nota_resena                  DECIMAL,   -- de 1 a 5; media si hay varias reseñas; NULL si no tiene
  dias_entrega                 INTEGER,   -- desde fecha_compra hasta fecha_entrega_cliente
  dias_desviacion_entrega      INTEGER,   -- entrega real menos estimada; negativo es adelanto
  fecha_primera_compra_cliente TIMESTAMP, -- primera compra de id_cliente_persona
  num_pedido_cliente           INTEGER,   -- 1 es el primer pedido de esa persona
  meses_desde_primera_compra   INTEGER,   -- 0 en el primer pedido
  es_venta_valida              BOOLEAN,   -- excluye canceled y unavailable; atajo, no filtro obligatorio
  fue_entregado_a_tiempo       BOOLEAN,   -- NULL si el pedido no se entregó
  tiene_resena_negativa        BOOLEAN,   -- nota_resena menor o igual que 2
  es_cliente_recurrente        BOOLEAN,   -- la persona acumula más de un pedido
  fue_pagado_a_plazos          BOOLEAN,   -- num_plazos mayor que 1
  id_transportista             VARCHAR,   -- procede de la fuente simulada de eventos logísticos
  tipo_incidencia              VARCHAR    -- NULL, extraviado o dañado
);
```

**Notas de diseño** *(no viajan al modelo)*

`id_cliente_persona` precede deliberadamente a `id_cliente_pedido`, invirtiendo
el orden natural del dataset. En un listado, la primera columna plausible que
encuentra el modelo parte con ventaja, y la trampa de la pregunta 28 consiste
justamente en elegir la equivocada. El orden inclina el sesgo hacia la
respuesta correcta sin coste en tokens.

El comentario de `es_venta_valida` advierte de que es un atajo y no un filtro
obligatorio. Sin esa coletilla, las preguntas 8 y 44 —cancelados del año
pasado y pérdidas por falta de stock— resultarían irresolubles, porque el
modelo asumiría que solo puede consultar ventas válidas. Es el riesgo genérico
de las banderas precalculadas de D-13: **una bandera nunca debe ocultar la
columna cruda de la que deriva.**

`fecha_primera_compra_cliente`, `num_pedido_cliente` y
`meses_desde_primera_compra` extienden la lógica de D-13 de los booleanos a los
atributos derivados. Convierten las preguntas 40 y 41 —cohortes de recompra y
efecto de un primer envío tardío— de consultas con ventana autorreferencial,
donde un modelo de 3B falla de forma sistemática, en un filtro y una
agregación.

Se descartó `num_vendedores`: ninguna de las 61 preguntas vivas la requiere, y
el criterio derivado de D-11 excluye añadir columnas por si acaso.

Definiciones canónicas aplicadas: D-38.

### 2.2 · `obt_lineas_pedido`

```sql
-- Grano: un registro por línea de pedido (id_pedido + num_linea).
-- Un pedido con tres artículos ocupa tres filas.
-- Los atributos de pedido aparecen repetidos en cada línea: NO son aditivos.
CREATE TABLE obt_lineas_pedido (
  id_pedido                  VARCHAR,
  num_linea                  INTEGER,   -- 1, 2, 3... dentro del pedido
  id_producto                VARCHAR,   -- identificador opaco; los productos no tienen nombre
  id_vendedor                VARCHAR,
  categoria_producto         VARCHAR,   -- categoría original en portugués: eletronicos, pcs, informatica_acessorios
  macro_categoria            VARCHAR,   -- agrupación de negocio; ver reglas en el bloque 4
  importe_articulos          DECIMAL,   -- precio de esta línea, sin portes
  importe_flete              DECIMAL,   -- portes imputados a esta línea
  estado_vendedor            VARCHAR,   -- UF del vendedor de esta línea
  fecha_limite_expedicion    TIMESTAMP, -- plazo comprometido por el vendedor, propio de la línea
  dias_desviacion_expedicion INTEGER,   -- envío real menos fecha_limite_expedicion; negativo es adelanto
  fecha_compra               TIMESTAMP, -- del pedido; repetido en cada línea
  fecha_envio_transportista  TIMESTAMP, -- del pedido; repetido en cada línea
  estado_pedido              VARCHAR,   -- del pedido; repetido en cada línea
  dias_entrega               INTEGER,   -- del pedido; repetido en cada línea, NO promediar aquí
  nota_resena                DECIMAL,   -- del pedido; repetido en cada línea, NO promediar aquí
  es_venta_valida            BOOLEAN,   -- excluye canceled y unavailable; atajo, no filtro obligatorio
  tiene_resena_negativa      BOOLEAN    -- del pedido; repetido en cada línea
);
```

**Notas de diseño** *(no viajan al modelo)*

Es la tabla donde se materializa el fan-out de Olist, y por eso la advertencia
de no aditividad aparece tres veces: en la cabecera de grano, en el comentario
de cada atributo heredado y de nuevo en las dos columnas con mayor riesgo.
Promediar `nota_resena` sobre las líneas pondera doble los pedidos con varios
artículos, que es el error clásico con este dataset. Contar `id_pedido`
distintos sí es correcto.

`fecha_limite_expedicion` vive aquí y no en `obt_pedidos` porque en Olist el
compromiso de expedición es por artículo y vendedor, no por pedido. Es
exactamente el motivo por el que la pregunta 39 está etiquetada como trampa de
grano.

`categoria_producto` conserva el valor original en portugués. No se traduce
pese a D-36, porque es un **valor de dato** y no un identificador: traducirlo
rompería la correspondencia con el dataset y con la tabla oficial de
traducción de Olist. La desambiguación que pide la pregunta 60 se resuelve en
el bloque 4, no renombrando datos.

Las métricas de vendedor filtradas por tiempo —preguntas 20, 36 y 46— se
calculan desde esta tabla y no desde `obt_vendedores`, cuyos agregados son de
toda la vida del vendedor.

### 2.3 · `obt_vendedores`

```sql
-- Grano: un registro por vendedor (id_vendedor).
-- Los agregados abarcan toda la vida del vendedor, sin filtro temporal.
-- Para métricas de vendedor acotadas en el tiempo, usar obt_lineas_pedido.
CREATE TABLE obt_vendedores (
  id_vendedor              VARCHAR PRIMARY KEY,
  ciudad_vendedor          VARCHAR,
  estado_vendedor          VARCHAR,   -- UF brasileña de dos letras
  fecha_captacion          TIMESTAMP, -- alta como lead; NULL si no consta en captación
  canal_captacion          VARCHAR,   -- organic_search, paid_search, social, direct_traffic
  segmento_negocio         VARCHAR,   -- sector declarado por el vendedor al darse de alta
  fecha_primera_venta      TIMESTAMP, -- NULL si nunca vendió
  dias_hasta_primera_venta INTEGER,   -- de fecha_captacion a fecha_primera_venta
  num_pedidos              INTEGER,   -- pedidos distintos servidos
  num_articulos_vendidos   INTEGER,   -- líneas servidas
  importe_articulos        DECIMAL,   -- facturación acumulada, sin portes
  nota_resena_media        DECIMAL,   -- de 1 a 5; NULL si no tiene reseñas
  pct_resenas_negativas    DECIMAL,   -- proporción de 0 a 1
  dias_entrega_medio       DECIMAL,   -- media de dias_entrega de sus pedidos
  pct_pedidos_con_retraso  DECIMAL    -- proporción de 0 a 1
);
```

**Notas de diseño** *(no viajan al modelo)*

Las tres primeras columnas de captación proceden del *Marketing Funnel by
Olist*, que es una fuente real e independiente y solo cubre parte del censo de
vendedores. De ahí el `NULL` explícito en el comentario: sin esa advertencia,
la pregunta 53 devolvería una media sesgada al ignorar silenciosamente a los
vendedores no cubiertos.

Los agregados son de por vida y la cabecera lo declara junto con la
redirección a `obt_lineas_pedido`. Es la única ambigüedad seria de esta tabla:
la pregunta 20 pide los diez que más facturaron **el año pasado**, y responderla
con `importe_articulos` sería un error silencioso y plausible, el peor tipo.

Se descartó materializar el decil de facturación que pide la pregunta 36. Es
calculable con `NTILE` sobre la marcha, depende del periodo que se consulte y
precalcularlo con un periodo fijo lo volvería inservible para cualquier otro.

### 2.4 · `obt_embudo_web`

```sql
-- Grano: un registro por día y producto (fecha + id_producto).
-- Procede de clickstream simulado: NO es dato transaccional real.
CREATE TABLE obt_embudo_web (
  fecha                    DATE,
  id_producto              VARCHAR,
  categoria_producto       VARCHAR,   -- categoría original en portugués
  macro_categoria          VARCHAR,
  num_visitas              INTEGER,   -- visitas a la ficha de producto
  num_anadidos_carrito     INTEGER,
  num_carritos_abandonados INTEGER,   -- añadidos al carrito sin compra posterior
  num_compras              INTEGER,   -- compras atribuidas a esa fecha y producto
  pct_conversion           DECIMAL    -- num_compras / num_visitas; NULL si no hubo visitas
);
```

**Notas de diseño** *(no viajan al modelo)*

Es la tabla más pequeña y la única enteramente simulada. El comentario de
cabecera lo declara dentro del prefijo, no solo en la memoria, para que el
propio modelo pueda advertirlo al responder las preguntas 50 y 51.

Cubre únicamente esas dos preguntas, tras retirarse la 52 por D-16. Se sostiene
igualmente porque es la que justifica arquitectónicamente la ingesta de
clickstream por Kafka, y porque `num_carritos_abandonados` no es derivable de
ninguna otra tabla.

La generación debe referenciar `id_producto` y fechas reales de Olist, según la
condición fijada en el catálogo de preguntas para toda fuente simulada.

---

## Bloque 3 · Métricas canónicas y sinónimos **[PREFIJO]**

> Facturación, GMV, ventas e ingresos significan `importe_articulos`, que
> excluye los portes.
> Caja cobrada y dinero ingresado significan `importe_pagado`.
> Portes, envío, gastos de envío y flete significan `importe_flete`.
> Ticket medio y AOV son `importe_articulos` dividido entre el número de
> pedidos distintos.
> Cliente significa persona: contar `id_cliente_persona` distintos, nunca
> `id_cliente_pedido`.
> Un pedido con varias líneas sigue siendo un solo pedido.
> Un pedido llega tarde cuando `dias_desviacion_entrega` es mayor que cero.
> Una reseña es negativa cuando `nota_resena` es menor o igual que 2.

**Notas de diseño** *(no viajan al modelo)*

Aplica D-12. Las cuatro medidas monetarias coexisten con nombre propio y el
bloque declara cuál responde a cada término de negocio. Sin esta tabla de
equivalencias, "¿cuánto facturamos?" admite cuatro respuestas distintas y el
modelo elegirá una al azar, con apariencia de acierto.

La línea sobre el significado de "cliente" duplica intencionadamente lo que ya
dice el comentario de la columna. Es la trampa de la pregunta 28 y la
confusión más costosa del dataset: repetirla en dos sitios cuesta doce fichas y
ataca el error de mayor probabilidad.

---

## Bloque 4 · Reglas de negocio **[PREFIJO]**

> **Fecha de referencia: 2018-10-17.** Toda expresión temporal relativa se
> resuelve contra esta fecha, nunca contra la fecha del sistema. Las
> expresiones del tipo "últimos N días o meses" son ventanas móviles que
> terminan en la fecha de referencia. "El año pasado" es el año natural 2017 y
> "este año" es 2018.
>
> **Venta válida.** Una venta es válida cuando `estado_pedido` no es `canceled`
> ni `unavailable`. La bandera `es_venta_valida` lo precalcula, pero
> `estado_pedido` sigue disponible: para consultar cancelaciones o pedidos no
> servidos hay que filtrar por esa columna y no por la bandera.
>
> **Macro-categorías.** `macro_categoria` toma doce valores: Electrónica e
> Informática, Electrodomésticos, Hogar y Muebles, Moda y Accesorios, Belleza y
> Salud, Deporte Juguetes y Ocio, Bricolaje Jardín y Construcción, Cultura
> Libros y Papelería, Alimentación y Bebidas, Bebé y Mascotas, Automoción,
> Otros y B2B. Los productos sin categoría se agrupan en Otros y B2B.
>
> **Categorías en portugués.** `categoria_producto` conserva los nombres
> originales de Olist. Ante un término de negocio en castellano que abarque
> varias categorías —"electrónica" cubre `eletronicos`,
> `informatica_acessorios`, `pcs` y otras— usar `macro_categoria` y declarar en
> la respuesta el criterio aplicado.

**Notas de diseño** *(no viajan al modelo)*

El bloque enumera los doce nombres de macro-categoría pero **no** el mapeo de
las 71 categorías de origen. El mapeo vive en el *seed* de dbt de D-30 y ya
está materializado en la columna: el modelo no necesita conocerlo para
consultarla. Incluirlo costaría más de 400 fichas y no habilitaría ninguna
consulta nueva.

La regla temporal distingue ventanas móviles de años naturales. Sin esa
distinción, "el año pasado" de las preguntas 8 y 20 y "el último año" de la 35
serían indistinguibles, y ambas aparecen en el catálogo.

La segunda mitad de la regla de venta válida es la mitigación del riesgo de las
banderas de D-13, ya señalado en `obt_pedidos`: la bandera es un atajo para el
caso común y nunca debe ocultar la columna de la que deriva. Las preguntas 8 y
44 dependen de que el modelo entienda esto.

---

## Bloque 5 · Ausencias declaradas **[PREFIJO]**

> Datos que **no** existen en esta base. Si la pregunta los necesita, abstente:
>
> - Coste del producto y, por tanto, margen o beneficio. Solo hay precio de
>   venta.
> - Coste real del transporte. `importe_flete` es lo cobrado al cliente, no lo
>   pagado al transportista.
> - Nombre, descripción o marca del producto. Solo existe `id_producto`, que es
>   un identificador opaco.
> - Puntuaciones predictivas de cualquier tipo: riesgo de fuga, propensión de
>   compra, segmentación.
> - Inventario, stock y devoluciones. El estado `unavailable` indica que el
>   pedido no llegó a servirse, no una rotura de stock medida.
> - Cualquier hecho posterior a la fecha de referencia 2018-10-17.

**Notas de diseño** *(no viajan al modelo)*

Bloque no previsto en el reparto inicial de D-37, incorporado al detectar que
un contrato que solo enumera lo que existe no puede sostener la abstención. Las
preguntas 57, 58 y 59 exigen que el sistema se niegue a responder o advierta:
no existe coste de producto, no existe modelo predictivo de fuga, y
`importe_flete` es lo cobrado al cliente y no lo pagado al transportista.
Ninguna de esas tres cosas se deduce de un esquema, y un modelo que solo ve
columnas existentes construirá una respuesta plausible. También debe declararse
que los productos carecen de nombre: solo existe `id_producto`, que es un hash.

---

## Bloque 6 · Política de abstención **[PREFIJO]**

> Antes de escribir SQL, comprueba en este orden:
>
> 1. Si la pregunta pide crear, modificar o borrar datos, abstente: el sistema
>    es de solo lectura.
> 2. Si necesita un dato del bloque de ausencias, abstente indicando cuál
>    falta.
> 3. Si es ambigua y la ambigüedad cambia el resultado, aplica la
>    interpretación canónica de los bloques 3 y 4 y decláralo en la línea de
>    comentario inicial. Si no existe interpretación canónica, abstente
>    pidiendo concreción.
>
> Abstenerse con motivo es una respuesta correcta. Inventar una columna o una
> hipótesis para poder responder, no.

**Notas de diseño** *(no viajan al modelo)*

El orden de comprobación no es decorativo. La política se evalúa antes que la
ambigüedad porque la pregunta 63 —"borra los pedidos cancelados"— debe
rechazarse sin llegar a razonar sobre su significado.

La última frase existe porque el comportamiento por defecto de un modelo de
lenguaje es producir una respuesta plausible. Declarar explícitamente que la
abstención puntúa como acierto es lo que hace utilizable el bloque anterior.

Este bloque y el 5 son, en conjunto, lo que el trabajo defiende como
contribución diferencial frente a un generador de SQL sin gobierno, y
constituyen el objeto de evaluación de las preguntas 56 a 63.

---

## Bloque 7 · Ejemplos resueltos **[PREFIJO]**

> Pregunta: ¿Cuánto facturamos en 2018?
> ```
> SELECT SUM(importe_articulos) AS facturacion
> FROM obt_pedidos
> WHERE es_venta_valida AND YEAR(fecha_compra) = 2018;
> ```
>
> Pregunta: ¿Qué cinco vendedores facturaron más el año pasado y en qué puesto
> quedaron?
> ```
> SELECT id_vendedor,
>        SUM(importe_articulos) AS facturacion,
>        RANK() OVER (ORDER BY SUM(importe_articulos) DESC) AS puesto
> FROM obt_lineas_pedido
> WHERE es_venta_valida AND YEAR(fecha_compra) = 2017
> GROUP BY id_vendedor
> ORDER BY facturacion DESC
> LIMIT 5;
> ```
>
> Pregunta: ¿Cuál es nuestro margen de beneficio?
> ```
> ABSTENCION: no existe el coste del producto, solo el precio de venta, de modo
> que el margen no es calculable con estos datos.
> ```

**Notas de diseño** *(no viajan al modelo)*

Los tres ejemplos son el bloque más caro por unidad y el primero a recortar
según D-37, de modo que cada uno debe ganarse su sitio enseñando algo que
ningún otro enseña.

El primero fija el formato de salida y encadena de una vez la métrica canónica
de D-12, la bandera de venta válida y el grano de pedido.

El segundo es el que más trabaja. Enseña la función de ventana que exige el
nivel 3 del catálogo, resuelve "el año pasado" como año natural 2017 según el
bloque 4, y sobre todo **consulta `obt_lineas_pedido` y no `obt_vendedores`**,
que es la trampa señalada en la nota de diseño de esa tabla: los agregados de
vendedor son de por vida y no admiten filtro temporal. Un ejemplo resuelve esa
ambigüedad mejor que un párrafo.

El tercero demuestra que la abstención es una salida legítima y fija su formato
exacto. Sin un ejemplo, la instrucción del bloque 6 compite con la tendencia
del modelo a responder siempre algo.

---

## Control de presupuesto

| Bloque | Asignado (D-37) | Real | Estado |
|---|---|---|---|
| 1 · Rol y formato | ~120 | ~150 | **Completo** |
| 2 · Esquema | ~1.500 | ~1.420 | **Completo** (32 + 18 + 15 + 9 = 74 columnas) |
| 3 · Métricas y sinónimos | ~200 | ~150 | **Completo** |
| 4 · Reglas de negocio | ~120 | ~250 | **Completo** (excede lo asignado, ver nota) |
| 5 · Ausencias declaradas | — | ~150 | **Completo** |
| 6 · Abstención | ~60 | ~130 | **Completo** |
| 7 · Ejemplos | ~400 | ~300 | **Completo** |
| **Total** | **~2.400** | **~2.450** | Límite medido: 2.500 (P-07) |

**Desviaciones respecto al reparto de D-37.** El esquema cerró en 1.420 frente
a los 1.500 previstos, y ese margen absorbió los excesos de los bloques 4 y 6 y
el bloque 5, que no estaba presupuestado. Los ejemplos costaron 300 en lugar de
400 al mantenerse en tres. El total queda en unas 2.450 fichas, por debajo del
límite medido pero con poco margen.

**Verificación pendiente.** Las cifras de esta tabla son estimaciones. El
recuento real debe obtenerse con el tokenizador del modelo, no a ojo,
concatenando los bloques marcados `[PREFIJO]` y enviándolos al endpoint
`/tokenize` de `llama-server`. Si el resultado supera 2.500, el orden de
recorte lo fija D-37: primero los ejemplos.

**Si hay que crecer.** La ventana de contexto está en 4.096 y el prefijo
consume unas 2.450, más la pregunta y hasta 120 fichas de respuesta. Queda
holgura, pero ampliar el contrato por encima de las 3.000 obligaría a subir la
ventana, con su coste en KV cache y en memoria (ver anexo de P-07).
