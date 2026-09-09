SELECT COUNT(DISTINCT id_producto) AS num_productos
FROM obt_lineas_pedido
WHERE es_venta_valida;
