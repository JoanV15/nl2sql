WITH pedidos_cat AS (
  SELECT categoria_producto, id_pedido, MAX(nota_resena) AS nota_resena
  FROM obt_lineas_pedido
  WHERE nota_resena IS NOT NULL
  GROUP BY categoria_producto, id_pedido
)
SELECT categoria_producto,
       AVG(nota_resena) AS nota_media,
       COUNT(*) AS num_pedidos
FROM pedidos_cat
GROUP BY categoria_producto
HAVING COUNT(*) > 100
ORDER BY nota_media, categoria_producto;
