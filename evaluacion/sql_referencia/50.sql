SELECT categoria_producto, SUM(num_carritos_abandonados) AS num_carritos_abandonados
FROM obt_embudo_web
GROUP BY categoria_producto
ORDER BY num_carritos_abandonados DESC, categoria_producto;
