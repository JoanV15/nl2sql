SELECT categoria_producto, SUM(importe_articulos) AS facturacion
FROM obt_lineas_pedido
WHERE es_venta_valida
GROUP BY categoria_producto
ORDER BY facturacion DESC;
