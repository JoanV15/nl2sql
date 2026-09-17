{% if env_var('TFM_TIENE_FUNNEL', '0') == '1' %}
SELECT
  d.seller_id,
  CAST(m.first_contact_date AS TIMESTAMP) AS fecha_captacion,
  m.origin AS canal_captacion,
  d.business_segment AS segmento_negocio
FROM delta_scan('{{ env_var("TFM_SILVER_PATH", "../datos/silver") }}/olist_closed_deals_dataset') AS d
LEFT JOIN delta_scan('{{ env_var("TFM_SILVER_PATH", "../datos/silver") }}/olist_marketing_qualified_leads_dataset') AS m
  ON d.mql_id = m.mql_id
{% else %}
SELECT
  CAST(NULL AS VARCHAR) AS seller_id,
  CAST(NULL AS TIMESTAMP) AS fecha_captacion,
  CAST(NULL AS VARCHAR) AS canal_captacion,
  CAST(NULL AS VARCHAR) AS segmento_negocio
WHERE FALSE
{% endif %}
