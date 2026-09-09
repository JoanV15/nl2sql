SELECT categoria_producto,
       SUM(importe_flete) / NULLIF(SUM(importe_articulos), 0) AS peso_envio
FROM obt_lineas_pedido
WHERE es_venta_valida
GROUP BY categoria_producto
ORDER BY peso_envio DESC, categoria_producto;
