SELECT COUNT(DISTINCT id_cliente_persona) AS num_clientes_recurrentes
FROM obt_pedidos
WHERE es_cliente_recurrente;
