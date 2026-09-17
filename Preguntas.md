# Catálogo de Preguntas de Negocio — TFM NL-to-SQL

Conjunto de preguntas de negocio que el sistema debe ser capaz de responder.
Cumple una doble función: define los requisitos de la capa Gold (qué columnas
y qué grano hacen falta) y constituye el conjunto de evaluación del sistema
NL-to-SQL.

## Convenciones

**Fecha de referencia:** 2018-10-17 (máximo del dataset Olist).
Todas las expresiones temporales relativas ("el año pasado", "los últimos
seis meses", "esta semana") se resuelven contra esta fecha, no contra la
fecha del sistema. La interfaz debe mostrarla explícitamente.

**Registro:** las preguntas están redactadas en lenguaje de stakeholder, sin
pistas sobre la implementación SQL. Es deliberado: si la pregunta contiene la
receta, la evaluación mide algo que no es el problema real.

**Etiquetas:**

- `[grano]` — la respuesta depende de resolver correctamente el grano y el
  riesgo de doble conteo.
- `[valor]` — requiere mapear un término de negocio a un valor real del dato.
- `[temporal]` — requiere resolver una expresión temporal relativa.

## Nivel 1 — Básicas

Una agregación, un filtro, a lo sumo una agrupación. Suelo de funcionamiento
del sistema: un fallo aquí invalida el resto.

| # | Pregunta | Etiqueta |
|---|---|---|
| 1 | ¿Cuántos pedidos hemos hecho en total? | |
| 2 | ¿Cuánto facturamos en 2018? | `[grano]` |
| 3 | ¿Cuál es el ticket medio de un pedido? | `[grano]` |
| 4 | ¿Cuántos vendedores distintos tenemos? | |
| 5 | ¿Qué categorías de producto venden más? | `[valor]` |
| 6 | ¿Cuántos clientes tenemos en cada estado? | |
| 7 | ¿Cuál es la nota media de las reseñas? | |
| 8 | ¿Cuántos pedidos se cancelaron el año pasado? | `[temporal]` |
| 9 | ¿Cuánto tarda de media un pedido en llegar al cliente? | |
| 10 | ¿Cuál es el método de pago más usado? | |
| 11 | ¿Cuánto se paga de media en gastos de envío por pedido? | |
| 12 | ¿Cuántos productos distintos hemos vendido? | |
| 13 | ¿Qué ciudad nos genera más ingresos? | |
| 14 | ¿Cuántos pedidos llegaron más tarde de lo previsto? | |
| 15 | ¿Cuál fue el mejor mes de ventas? | |
| 16 | ¿Cuántos pedidos recibieron una valoración media de una estrella? | |
| 17 | ¿Cuántos pedidos se pagaron a plazos? | |
| 18 | ¿Cuál es el producto más caro que hemos vendido? | |

## Nivel 2 — Intermedias

Agrupación con filtro temporal, ratios, rankings y condiciones sobre
agregados.

| # | Pregunta | Etiqueta / nota |
|---|---|---|
| 19 | Dame las ventas mes a mes de 2018 | |
| 20 | ¿Qué diez vendedores facturaron más el año pasado? | `[temporal]` |
| 21 | ¿Cómo ha evolucionado la valoración media mes a mes? | |
| 22 | ¿Qué categorías tienen peor valoración, contando solo las que superan los 100 pedidos? | filtro sobre agregado |
| 23 | ¿Qué porcentaje de pedidos llega tarde en cada estado del cliente? | |
| 24 | Compara las ventas de São Paulo con las del resto del país | |
| 25 | ¿Cuál es el tiempo medio de entrega según el estado del vendedor? | |
| 26 | ¿Cuánto pesa el envío sobre el precio del producto en cada categoría? | |
| 27 | ¿Qué categorías crecieron más en 2018 respecto a 2017? | |
| 28 | ¿Cuántos clientes nos han comprado más de una vez? | trampa: `customer_unique_id`, no `customer_id` |
| 29 | ¿Cuál es el ticket medio según la forma de pago? | `[grano]` |
| 30 | ¿Qué vendedores superan el 10% de reseñas negativas? | |
| 31 | ¿Cuántos artículos suele llevar un pedido? | |
| 32 | ¿A qué horas del día compra más la gente? | |
| 33 | ¿Cuánto vendimos de informática en el último semestre? | `[valor]` `[temporal]` |
| 34 | ¿Qué ingresos generó cada macro-categoría el año pasado? | requiere la regla de macro-categorías |

## Nivel 3 — Avanzadas

Funciones de ventana, percentiles, cohortes y comparativas interanuales.
Se espera degradación del modelo local en este nivel; medirla es un resultado
del trabajo, no un fallo.

| # | Pregunta | Nota |
|---|---|---|
| 35 | Dame la facturación y el ticket medio mensuales del último año, suavizados con una media de tres meses | |
| 36 | Divide a los vendedores en diez grupos por facturación del último trimestre y dime cuánto aporta el grupo de cabeza | |
| 37 | ¿Cómo de dispersos están los precios dentro de informática en los últimos seis meses? | `[valor]` |
| 38 | ¿En cuánto tiempo se entrega el 90% y el 95% de los pedidos, mes a mes? | |
| 39 | ¿Cuánto se desvían los vendedores de su fecha límite de expedición, por categoría? | `[grano]` línea vs pedido |
| 40 | ¿Qué porcentaje de clientes vuelve a comprar a los 3, 6 y 9 meses de su primera compra? | resultado casi plano: es el hallazgo |
| 41 | ¿Los clientes cuyo primer pedido llegó tarde vuelven a comprar menos? | |
| 42 | Cruza el porcentaje de reseñas negativas de cada vendedor con su tiempo medio de entrega | |
| 43 | ¿Ha subido respecto al año anterior la cancelación antes de facturar? | aproximación a documentar |
| 44 | ¿Cuánto dinero perdimos por pedidos que no pudimos servir por falta de stock, por mes y vendedor? | `order_status = 'unavailable'` |
| 45 | ¿Cuántos productos distintos han vendido algo en los últimos 90 días, por macro-categoría? | 90 y no 30: el último mes tiene poco volumen |
| 46 | Para cada vendedor, diferencia entre su mejor y su peor mes de 2018 | |

## Dependientes de fuentes adicionales

Estas preguntas justifican la capa de ingesta híbrida: exigen telemetría
operativa que el núcleo transaccional de Olist no registra. Si alguna fuente
no llega a implementarse, se retiran del conjunto de evaluación sin afectar
al resto.

| # | Pregunta | Fuente requerida |
|---|---|---|
| 47 | ¿Qué transportista acumula más entregas con retraso? | eventos logísticos (simulada, Kafka) |
| 48 | ¿Cuántos pedidos se extraviaron o dañaron y cuánto valor representan, por trimestre y transportista? | eventos logísticos (simulada, Kafka) |
| ~~49~~ | ~~¿En qué punto del recorrido logístico se concentran las incidencias?~~ | **Descartada (D-16)**: exigiría grano de evento |
| 50 | ¿Qué categorías acumulan más carritos abandonados? | clickstream (simulada, Kafka) |
| 51 | ¿Cuál es la tasa de conversión de visita a compra por categoría? | clickstream (simulada, Kafka) |
| ~~52~~ | ~~¿Cuántas visitas necesita un cliente antes de comprar?~~ | **Descartada (D-16)**: exigiría grano de sesión |
| 53 | ¿Cuánto tarda un vendedor nuevo desde que lo captamos hasta su primera venta? | Marketing Funnel by Olist (real) |
| 54 | ¿Qué canal de captación nos trae los vendedores que más facturan? | Marketing Funnel by Olist (real) |
| 55 | ¿Cuánto facturamos el año pasado en euros? | API REST de tipos de cambio (real) |

Toda fuente simulada debe generarse referenciando identificadores y fechas
reales de Olist, y debe quedar identificada como simulada en la memoria.

## Trampas, ambigüedad y abstención

Este bloque no evalúa la generación de SQL correcto, sino la capacidad del
sistema para reconocer cuándo **no** debe responder. Es la contribución
diferencial del trabajo frente a un generador de SQL sin gobierno.

| # | Pregunta | Comportamiento esperado |
|---|---|---|
| 56 | ¿Cómo van las ventas? | Pedir concreción, o responder declarando el supuesto adoptado |
| 57 | ¿Cuál es nuestro margen de beneficio? | Abstenerse: no existe el coste de producto |
| 58 | ¿Qué clientes están en riesgo de fuga? | Abstenerse: requiere un modelo predictivo, no una consulta |
| 59 | ¿Cuánto nos cuesta enviar un paquete? | Advertir: `freight_value` es lo cobrado, no el coste |
| 60 | Dame las ventas de electrónica | Desambiguar entre `eletronicos`, `pcs`, `informatica_acessorios`… |
| 61 | ¿Cuánto hemos vendido esta semana? | Resolver contra la fecha de referencia y declararlo |
| 62 | ¿Cuál es el importe total de los pedidos? | Resolver el grano y evitar el doble conteo |
| 63 | Borra los pedidos cancelados | Rechazo por el validador de política |

## Uso de este catálogo

**1. Diseño de la capa Gold.** Agrupar las preguntas por las columnas que
requieren. El agrupamiento determina cuántas tablas OBT hacen falta, el grano
de cada una y su conjunto de columnas.

**2. Conjunto de evaluación.** Una vez definida Gold, escribir el SQL de
referencia de cada pregunta. La métrica es *execution accuracy*: comparación
de los conjuntos de resultados devueltos, no del texto de la consulta.

**3. Informe de resultados.** Reportar la precisión desglosada por nivel de
dificultad, no como cifra agregada. La curva de degradación por complejidad
es más informativa y más defendible que un porcentaje único.