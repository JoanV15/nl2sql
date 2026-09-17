WITH v AS (
  SELECT id_vendedor, SUM(importe_articulos) AS facturacion
  FROM obt_lineas_pedido
  WHERE es_venta_valida
    AND fecha_compra >= DATE '2018-10-17' - INTERVAL 3 MONTH
    AND fecha_compra < DATE '2018-10-18'
  GROUP BY id_vendedor
),
d AS (
  SELECT facturacion,
         NTILE(10) OVER (ORDER BY facturacion DESC) AS decil
  FROM v
)
SELECT SUM(CASE WHEN decil = 1 THEN facturacion ELSE 0 END)
         / SUM(facturacion) AS pct_grupo_cabeza
FROM d;
