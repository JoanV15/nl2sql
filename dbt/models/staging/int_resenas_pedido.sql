-- Agregación de reseñas a grano pedido antes del join (D-11, D-38: media).
SELECT
  order_id,
  AVG(CAST(review_score AS DOUBLE)) AS nota_resena
FROM {{ ref('stg_order_reviews') }}
GROUP BY order_id
