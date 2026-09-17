{{ config(materialized='table') }}

SELECT
  CAST(c.fecha AS DATE) AS fecha,
  c.product_id AS id_producto,
  pr.product_category_name AS categoria_producto,
  COALESCE(m.macro_categoria, 'Otros y B2B') AS macro_categoria,
  CAST(c.num_visitas AS INTEGER) AS num_visitas,
  CAST(c.num_anadidos_carrito AS INTEGER) AS num_anadidos_carrito,
  CAST(c.num_carritos_abandonados AS INTEGER) AS num_carritos_abandonados,
  CAST(c.num_compras AS INTEGER) AS num_compras,
  CASE
    WHEN c.num_visitas IS NULL OR c.num_visitas = 0 THEN CAST(NULL AS DECIMAL)
    ELSE CAST(c.num_compras AS DECIMAL) / CAST(c.num_visitas AS DECIMAL)
  END AS pct_conversion
FROM {{ ref('stg_clickstream') }} AS c
LEFT JOIN {{ ref('stg_products') }} AS pr ON c.product_id = pr.product_id
LEFT JOIN {{ ref('seed_macro_categorias') }} AS m
  ON pr.product_category_name = m.product_category_name
