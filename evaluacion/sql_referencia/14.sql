SELECT COUNT(*) AS num_retrasados
FROM obt_pedidos
WHERE dias_desviacion_entrega > 0;
