"""Preguntas de evaluación, texto idéntico a Preguntas.md.

Sin 43 (definición ausente) ni 47–55 (Hito 4 / D-16). D-54.
"""

NIVEL1: list[tuple[int, str]] = [
    (1, "¿Cuántos pedidos hemos hecho en total?"),
    (2, "¿Cuánto facturamos en 2018?"),
    (3, "¿Cuál es el ticket medio de un pedido?"),
    (4, "¿Cuántos vendedores distintos tenemos?"),
    (5, "¿Qué categorías de producto venden más?"),
    (6, "¿Cuántos clientes tenemos en cada estado?"),
    (7, "¿Cuál es la nota media de las reseñas?"),
    (8, "¿Cuántos pedidos se cancelaron el año pasado?"),
    (9, "¿Cuánto tarda de media un pedido en llegar al cliente?"),
    (10, "¿Cuál es el método de pago más usado?"),
    (11, "¿Cuánto se paga de media en gastos de envío por pedido?"),
    (12, "¿Cuántos productos distintos hemos vendido?"),
    (13, "¿Qué ciudad nos genera más ingresos?"),
    (14, "¿Cuántos pedidos llegaron más tarde de lo previsto?"),
    (15, "¿Cuál fue el mejor mes de ventas?"),
    (16, "¿Cuántos pedidos recibieron una valoración media de una estrella?"),
    (17, "¿Cuántos pedidos se pagaron a plazos?"),
    (18, "¿Cuál es el producto más caro que hemos vendido?"),
]

NIVEL2: list[tuple[int, str]] = [
    (19, "Dame las ventas mes a mes de 2018"),
    (20, "¿Qué diez vendedores facturaron más el año pasado?"),
    (21, "¿Cómo ha evolucionado la valoración media mes a mes?"),
    (
        22,
        "¿Qué categorías tienen peor valoración, "
        "contando solo las que superan los 100 pedidos?",
    ),
    (23, "¿Qué porcentaje de pedidos llega tarde en cada estado del cliente?"),
    (24, "Compara las ventas de São Paulo con las del resto del país"),
    (25, "¿Cuál es el tiempo medio de entrega según el estado del vendedor?"),
    (26, "¿Cuánto pesa el envío sobre el precio del producto en cada categoría?"),
    (27, "¿Qué categorías crecieron más en 2018 respecto a 2017?"),
    (28, "¿Cuántos clientes nos han comprado más de una vez?"),
    (29, "¿Cuál es el ticket medio según la forma de pago?"),
    (30, "¿Qué vendedores superan el 10% de reseñas negativas?"),
    (31, "¿Cuántos artículos suele llevar un pedido?"),
    (32, "¿A qué horas del día compra más la gente?"),
    (33, "¿Cuánto vendimos de informática en el último semestre?"),
    (34, "¿Qué ingresos generó cada macro-categoría el año pasado?"),
]

NIVEL3: list[tuple[int, str]] = [
    (
        35,
        "Dame la facturación y el ticket medio mensuales del último año, "
        "suavizados con una media de tres meses",
    ),
    (
        36,
        "Divide a los vendedores en diez grupos por facturación del último "
        "trimestre y dime cuánto aporta el grupo de cabeza",
    ),
    (
        37,
        "¿Cómo de dispersos están los precios dentro de informática "
        "en los últimos seis meses?",
    ),
    (38, "¿En cuánto tiempo se entrega el 90% y el 95% de los pedidos, mes a mes?"),
    (
        39,
        "¿Cuánto se desvían los vendedores de su fecha límite de expedición, "
        "por categoría?",
    ),
    (
        40,
        "¿Qué porcentaje de clientes vuelve a comprar a los 3, 6 y 9 meses "
        "de su primera compra?",
    ),
    (41, "¿Los clientes cuyo primer pedido llegó tarde vuelven a comprar menos?"),
    (
        42,
        "Cruza el porcentaje de reseñas negativas de cada vendedor "
        "con su tiempo medio de entrega",
    ),
    (
        44,
        "¿Cuánto dinero perdimos por pedidos que no pudimos servir "
        "por falta de stock, por mes y vendedor?",
    ),
    (
        45,
        "¿Cuántos productos distintos han vendido algo en los últimos 90 días, "
        "por macro-categoría?",
    ),
    (46, "Para cada vendedor, diferencia entre su mejor y su peor mes de 2018"),
]

ABSTENCION: list[tuple[int, str]] = [
    (56, "¿Cómo van las ventas?"),
    (57, "¿Cuál es nuestro margen de beneficio?"),
    (58, "¿Qué clientes están en riesgo de fuga?"),
    (59, "¿Cuánto nos cuesta enviar un paquete?"),
    (60, "Dame las ventas de electrónica"),
    (61, "¿Cuánto hemos vendido esta semana?"),
    (62, "¿Cuál es el importe total de los pedidos?"),
    (63, "Borra los pedidos cancelados"),
]
