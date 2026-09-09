SELECT COUNT(*) AS num_cancelados
FROM obt_pedidos
WHERE estado_pedido = 'canceled' AND YEAR(fecha_compra) = 2017;
