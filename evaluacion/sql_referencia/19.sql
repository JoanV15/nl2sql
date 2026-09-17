SELECT DATE_TRUNC('month', fecha_compra) AS mes,
       SUM(importe_articulos) AS facturacion
FROM obt_pedidos
WHERE es_venta_valida AND YEAR(fecha_compra) = 2018
GROUP BY mes
ORDER BY mes;
