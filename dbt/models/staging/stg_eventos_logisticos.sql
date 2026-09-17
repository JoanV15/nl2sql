{% if env_var('TFM_TIENE_EVENTOS', '0') == '1' %}
SELECT
  order_id,
  id_transportista,
  tipo_incidencia
FROM delta_scan('{{ env_var("TFM_SILVER_PATH", "../datos/silver") }}/eventos_logisticos')
{% else %}
SELECT
  CAST(NULL AS VARCHAR) AS order_id,
  CAST(NULL AS VARCHAR) AS id_transportista,
  CAST(NULL AS VARCHAR) AS tipo_incidencia
WHERE FALSE
{% endif %}
