WITH recompra AS (
  SELECT id_cliente_persona,
         MIN(meses_desde_primera_compra) FILTER (
           WHERE num_pedido_cliente > 1
         ) AS meses_recompra
  FROM obt_pedidos
  WHERE fecha_primera_compra_cliente <= DATE '2018-01-17'
  GROUP BY id_cliente_persona
)
SELECT AVG(CASE WHEN meses_recompra <= 3 THEN 1.0 ELSE 0.0 END) AS pct_3m,
       AVG(CASE WHEN meses_recompra <= 6 THEN 1.0 ELSE 0.0 END) AS pct_6m,
       AVG(CASE WHEN meses_recompra <= 9 THEN 1.0 ELSE 0.0 END) AS pct_9m
FROM recompra;
