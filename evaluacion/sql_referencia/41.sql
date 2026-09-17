SELECT dias_desviacion_entrega > 0 AS primer_pedido_tarde,
       AVG(CAST(es_cliente_recurrente AS DOUBLE)) AS pct_recompra
FROM obt_pedidos
WHERE num_pedido_cliente = 1
  AND dias_desviacion_entrega IS NOT NULL
GROUP BY 1
ORDER BY primer_pedido_tarde;
