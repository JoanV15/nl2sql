SELECT
  order_id,
  CAST(payment_sequential AS INTEGER) AS payment_sequential,
  payment_type,
  CAST(payment_installments AS INTEGER) AS payment_installments,
  CAST(payment_value AS DOUBLE) AS payment_value
FROM {{ from_olist('olist_order_payments_dataset') }}
