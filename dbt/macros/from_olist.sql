{% macro from_olist(tabla) -%}
{%- if target.name == 'ci' -%}
{{ ref('seed_' ~ tabla) }}
{%- else -%}
delta_scan('{{ env_var("TFM_SILVER_PATH", "../datos/silver") }}/{{ tabla }}')
{%- endif -%}
{%- endmacro %}
