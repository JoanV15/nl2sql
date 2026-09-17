-- Artículos y flete a grano pedido, antes del join (D-11).
SELECT
  order_id,
  SUM(price) AS importe_articulos,
  SUM(freight_value) AS importe_flete,
  COUNT(*) AS num_articulos
FROM {{ ref('stg_order_items') }}
GROUP BY order_id
