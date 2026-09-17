{{ config(materialized='table') }}

WITH resenas AS (
  SELECT * FROM {{ ref('int_resenas_pedido') }}
)

SELECT
  i.order_id AS id_pedido,
  CAST(i.order_item_id AS INTEGER) AS num_linea,
  i.product_id AS id_producto,
  i.seller_id AS id_vendedor,
  pr.product_category_name AS categoria_producto,
  COALESCE(m.macro_categoria, 'Otros y B2B') AS macro_categoria,
  i.price AS importe_articulos,
  i.freight_value AS importe_flete,
  s.seller_state AS estado_vendedor,
  CAST(i.shipping_limit_date AS TIMESTAMP) AS fecha_limite_expedicion,
  CAST(
    date_diff(
      'day',
      CAST(i.shipping_limit_date AS TIMESTAMP),
      CAST(o.order_delivered_carrier_date AS TIMESTAMP)
    ) AS INTEGER
  ) AS dias_desviacion_expedicion,
  CAST(o.order_purchase_timestamp AS TIMESTAMP) AS fecha_compra,
  CAST(o.order_delivered_carrier_date AS TIMESTAMP) AS fecha_envio_transportista,
  o.order_status AS estado_pedido,
  CAST(
    date_diff(
      'day',
      CAST(o.order_purchase_timestamp AS TIMESTAMP),
      CAST(o.order_delivered_customer_date AS TIMESTAMP)
    ) AS INTEGER
  ) AS dias_entrega,
  r.nota_resena,
  o.order_status NOT IN ('canceled', 'unavailable') AS es_venta_valida,
  r.nota_resena <= 2 AS tiene_resena_negativa
FROM {{ ref('stg_order_items') }} AS i
INNER JOIN {{ ref('stg_orders') }} AS o ON i.order_id = o.order_id
LEFT JOIN {{ ref('stg_products') }} AS pr ON i.product_id = pr.product_id
LEFT JOIN {{ ref('stg_sellers') }} AS s ON i.seller_id = s.seller_id
LEFT JOIN {{ ref('seed_macro_categorias') }} AS m
  ON pr.product_category_name = m.product_category_name
LEFT JOIN resenas AS r ON i.order_id = r.order_id
