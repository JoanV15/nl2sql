-- supuesto: esta semana = semana natural de 2018-10-17 (lunes a domingo)
SELECT COALESCE(SUM(importe_articulos), 0) AS facturacion
FROM obt_pedidos
WHERE es_venta_valida
  AND DATE_TRUNC('week', fecha_compra) = DATE_TRUNC('week', DATE '2018-10-17');
