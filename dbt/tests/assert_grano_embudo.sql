-- Grano declarado de obt_embudo_web: un registro por día y producto.
SELECT fecha, id_producto, COUNT(*) AS n
FROM {{ ref('obt_embudo_web') }}
GROUP BY fecha, id_producto
HAVING COUNT(*) > 1
