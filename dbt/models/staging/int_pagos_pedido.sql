-- Agregación de pagos a grano pedido (D-11, D-45).
WITH principales AS (
  SELECT
    order_id,
    payment_type AS tipo_pago_principal,
    payment_installments AS num_plazos
  FROM {{ ref('stg_order_payments') }}
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY order_id
    ORDER BY payment_value DESC, payment_sequential ASC
  ) = 1
),
totales AS (
  SELECT
    order_id,
    SUM(payment_value) AS importe_pagado
  FROM {{ ref('stg_order_payments') }}
  GROUP BY order_id
)

SELECT
  t.order_id,
  t.importe_pagado,
  p.tipo_pago_principal,
  p.num_plazos
FROM totales AS t
INNER JOIN principales AS p USING (order_id)
