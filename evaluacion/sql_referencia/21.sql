SELECT DATE_TRUNC('month', fecha_compra) AS mes,
       AVG(nota_resena) AS nota_media
FROM obt_pedidos
WHERE nota_resena IS NOT NULL
GROUP BY mes
ORDER BY mes;
