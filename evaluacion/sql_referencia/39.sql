SELECT categoria_producto,
       AVG(dias_desviacion_expedicion) AS desviacion_media
FROM obt_lineas_pedido
WHERE dias_desviacion_expedicion IS NOT NULL
GROUP BY categoria_producto
ORDER BY desviacion_media DESC, categoria_producto;
