{% if target.name == 'ci' %}
SELECT
  fecha,
  product_id,
  CAST(num_visitas AS INTEGER) AS num_visitas,
  CAST(num_anadidos_carrito AS INTEGER) AS num_anadidos_carrito,
  CAST(num_carritos_abandonados AS INTEGER) AS num_carritos_abandonados,
  CAST(num_compras AS INTEGER) AS num_compras
FROM {{ ref('seed_eventos_clickstream') }}
{% elif env_var('TFM_TIENE_CLICKSTREAM', '0') == '1' %}
SELECT
  fecha,
  product_id,
  num_visitas,
  num_anadidos_carrito,
  num_carritos_abandonados,
  num_compras
FROM delta_scan('{{ env_var("TFM_SILVER_PATH", "../datos/silver") }}/eventos_clickstream')
{% else %}
SELECT
  CAST(NULL AS VARCHAR) AS fecha,
  CAST(NULL AS VARCHAR) AS product_id,
  CAST(NULL AS INTEGER) AS num_visitas,
  CAST(NULL AS INTEGER) AS num_anadidos_carrito,
  CAST(NULL AS INTEGER) AS num_carritos_abandonados,
  CAST(NULL AS INTEGER) AS num_compras
WHERE FALSE
{% endif %}
