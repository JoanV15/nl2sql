SELECT AVG(dias_entrega) AS dias_entrega_medio
FROM obt_pedidos
WHERE dias_entrega IS NOT NULL;
