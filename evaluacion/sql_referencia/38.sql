SELECT DATE_TRUNC('month', fecha_compra) AS mes,
       QUANTILE_CONT(dias_entrega, 0.90) AS p90_dias,
       QUANTILE_CONT(dias_entrega, 0.95) AS p95_dias
FROM obt_pedidos
WHERE dias_entrega IS NOT NULL
GROUP BY mes
ORDER BY mes;
