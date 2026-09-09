-- D-30: toda categoría de producto tiene exactamente una macro-categoría.
SELECT DISTINCT p.product_category_name
FROM {{ ref('stg_products') }} AS p
LEFT JOIN {{ ref('seed_macro_categorias') }} AS s
  ON p.product_category_name = s.product_category_name
WHERE p.product_category_name IS NOT NULL
  AND s.product_category_name IS NULL
