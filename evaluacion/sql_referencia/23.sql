SELECT estado_cliente,
       AVG(CASE WHEN dias_desviacion_entrega > 0 THEN 1.0 ELSE 0.0 END) AS pct_retraso
FROM obt_pedidos
WHERE dias_desviacion_entrega IS NOT NULL
GROUP BY estado_cliente
ORDER BY pct_retraso DESC, estado_cliente;
