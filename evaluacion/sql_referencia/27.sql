WITH y2017 AS (
  SELECT categoria_producto, SUM(importe_articulos) AS facturacion
  FROM obt_lineas_pedido
  WHERE es_venta_valida AND YEAR(fecha_compra) = 2017
  GROUP BY categoria_producto
),
y2018 AS (
  SELECT categoria_producto, SUM(importe_articulos) AS facturacion
  FROM obt_lineas_pedido
  WHERE es_venta_valida AND YEAR(fecha_compra) = 2018
  GROUP BY categoria_producto
)
SELECT y2018.categoria_producto,
       y2017.facturacion AS facturacion_2017,
       y2018.facturacion AS facturacion_2018,
       (y2018.facturacion - y2017.facturacion) / NULLIF(y2017.facturacion, 0) AS crecimiento
FROM y2018
JOIN y2017 USING (categoria_producto)
ORDER BY crecimiento DESC, categoria_producto;

