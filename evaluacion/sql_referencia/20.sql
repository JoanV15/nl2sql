SELECT id_vendedor, SUM(importe_articulos) AS facturacion
FROM obt_lineas_pedido
WHERE es_venta_valida AND YEAR(fecha_compra) = 2017
GROUP BY id_vendedor
ORDER BY facturacion DESC, id_vendedor
LIMIT 10;
