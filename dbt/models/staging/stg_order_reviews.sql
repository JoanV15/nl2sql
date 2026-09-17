-- Silver escrito por consulta a Mongo (D-32), no por el CSV de Landing.
-- En target ci la muestra sustituye a Delta (D-25).
SELECT *
FROM {{ from_olist('olist_order_reviews_dataset') }}
