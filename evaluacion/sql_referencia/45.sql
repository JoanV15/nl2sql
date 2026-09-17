SELECT macro_categoria, COUNT(DISTINCT id_producto) AS num_productos
FROM obt_lineas_pedido
WHERE es_venta_valida
  AND fecha_compra >= DATE '2018-10-17' - INTERVAL 90 DAY
  AND fecha_compra < DATE '2018-10-18'
GROUP BY macro_categoria
ORDER BY num_productos DESC, macro_categoria;
