SELECT HOUR(fecha_compra) AS hora, COUNT(*) AS num_pedidos
FROM obt_pedidos
GROUP BY hora
ORDER BY num_pedidos DESC, hora;
