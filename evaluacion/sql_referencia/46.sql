WITH mensual AS (
  SELECT id_vendedor,
         DATE_TRUNC('month', fecha_compra) AS mes,
         SUM(importe_articulos) AS facturacion
  FROM obt_lineas_pedido
  WHERE es_venta_valida AND YEAR(fecha_compra) = 2018
  GROUP BY id_vendedor, mes
)
SELECT id_vendedor,
       MAX(facturacion) - MIN(facturacion) AS amplitud
FROM mensual
GROUP BY id_vendedor
ORDER BY amplitud DESC, id_vendedor;
