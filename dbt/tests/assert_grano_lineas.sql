-- Grano declarado de obt_lineas_pedido.
SELECT id_pedido, num_linea, COUNT(*) AS n
FROM {{ ref('obt_lineas_pedido') }}
GROUP BY id_pedido, num_linea
HAVING COUNT(*) > 1
