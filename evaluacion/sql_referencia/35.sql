SELECT mes,
       facturacion,
       ticket_medio,
       AVG(facturacion) OVER (
         ORDER BY mes ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
       ) AS facturacion_mm3,
       AVG(ticket_medio) OVER (
         ORDER BY mes ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
       ) AS ticket_mm3
FROM (
  SELECT DATE_TRUNC('month', fecha_compra) AS mes,
         SUM(importe_articulos) AS facturacion,
         SUM(importe_articulos) / COUNT(*) AS ticket_medio
  FROM obt_pedidos
  WHERE es_venta_valida
    AND fecha_compra >= DATE '2018-10-17' - INTERVAL 1 YEAR
    AND fecha_compra < DATE '2018-10-18'
  GROUP BY mes
)
ORDER BY mes;
