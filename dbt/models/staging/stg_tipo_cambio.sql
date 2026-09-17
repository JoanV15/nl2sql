{% if env_var('TFM_TIENE_FX', '0') == '1' %}
SELECT CAST(eur_por_brl AS DECIMAL(18, 8)) AS eur_por_brl
FROM delta_scan('{{ env_var("TFM_SILVER_PATH", "../datos/silver") }}/tipo_cambio')
{% else %}
SELECT CAST(NULL AS DECIMAL) AS eur_por_brl
WHERE FALSE
{% endif %}
