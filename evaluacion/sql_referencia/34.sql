SELECT macro_categoria, SUM(importe_articulos) AS ingresos
FROM obt_lineas_pedido
WHERE es_venta_valida AND YEAR(fecha_compra) = 2017
GROUP BY macro_categoria
ORDER BY ingresos DESC, macro_categoria;
