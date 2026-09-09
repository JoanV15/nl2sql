SELECT estado_cliente, COUNT(DISTINCT id_cliente_persona) AS num_clientes
FROM obt_pedidos
GROUP BY estado_cliente;
