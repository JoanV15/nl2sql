SELECT *
FROM read_csv_auto(
  '{{ env_var("TFM_LANDING_PATH") }}/olist_order_payments_dataset.csv',
  header = true
)
