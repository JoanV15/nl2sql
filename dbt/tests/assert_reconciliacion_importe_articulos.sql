-- D-14: el mismo importe_articulos por dos caminos.
SELECT
  ROUND(p.total, 2) AS pedidos,
  ROUND(l.total, 2) AS lineas
FROM
  (SELECT COALESCE(SUM(importe_articulos), 0) AS total FROM {{ ref('obt_pedidos') }}) AS p,
  (SELECT COALESCE(SUM(importe_articulos), 0) AS total FROM {{ ref('obt_lineas_pedido') }}) AS l
WHERE ROUND(p.total, 2) <> ROUND(l.total, 2)
