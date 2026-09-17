SELECT DATE_TRUNC('month', fecha_compra) AS mes, SUM(importe_articulos) AS facturacion
FROM obt_pedidos
WHERE es_venta_valida
GROUP BY mes
ORDER BY facturacion DESC, mes
LIMIT 1;
