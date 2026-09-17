SELECT id_producto, importe_articulos
FROM obt_lineas_pedido
WHERE es_venta_valida
ORDER BY importe_articulos DESC, id_producto
LIMIT 1;
