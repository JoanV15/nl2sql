SELECT
  order_id,
  order_item_id,
  product_id,
  seller_id,
  shipping_limit_date,
  CAST(price AS DOUBLE) AS price,
  CAST(freight_value AS DOUBLE) AS freight_value
FROM {{ from_olist('olist_order_items_dataset') }}
