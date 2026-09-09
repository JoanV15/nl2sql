-- D-30: el seed no tiene entradas huérfanas.
SELECT s.product_category_name
FROM {{ ref('seed_macro_categorias') }} AS s
LEFT JOIN {{ ref('stg_products') }} AS p
  ON s.product_category_name = p.product_category_name
WHERE p.product_category_name IS NULL
