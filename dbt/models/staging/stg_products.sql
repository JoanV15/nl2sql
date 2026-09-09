SELECT *
FROM read_csv_auto(
  '{{ env_var("TFM_LANDING_PATH") }}/olist_products_dataset.csv',
  header = true
)
