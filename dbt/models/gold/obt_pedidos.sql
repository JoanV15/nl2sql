{{ config(materialized='table') }}

WITH base AS (
  SELECT
    o.order_id AS id_pedido,
    c.customer_unique_id AS id_cliente_persona,
    c.customer_id AS id_cliente_pedido,
    c.customer_city AS ciudad_cliente,
    c.customer_state AS estado_cliente,
    o.order_status AS estado_pedido,
    CAST(o.order_purchase_timestamp AS TIMESTAMP) AS fecha_compra,
    CAST(o.order_approved_at AS TIMESTAMP) AS fecha_aprobacion_pago,
    CAST(o.order_delivered_carrier_date AS TIMESTAMP) AS fecha_envio_transportista,
    CAST(o.order_delivered_customer_date AS TIMESTAMP) AS fecha_entrega_cliente,
    CAST(o.order_estimated_delivery_date AS TIMESTAMP) AS fecha_entrega_estimada,
    i.importe_articulos,
    i.importe_flete,
    i.num_articulos,
    p.importe_pagado,
    p.tipo_pago_principal,
    CAST(p.num_plazos AS INTEGER) AS num_plazos,
    r.nota_resena
  FROM {{ ref('stg_orders') }} AS o
  LEFT JOIN {{ ref('stg_customers') }} AS c ON o.customer_id = c.customer_id
  LEFT JOIN {{ ref('int_items_pedido') }} AS i ON o.order_id = i.order_id
  LEFT JOIN {{ ref('int_pagos_pedido') }} AS p ON o.order_id = p.order_id
  LEFT JOIN {{ ref('int_resenas_pedido') }} AS r ON o.order_id = r.order_id
),

con_historia AS (
  SELECT
    *,
    MIN(fecha_compra) OVER (PARTITION BY id_cliente_persona) AS fecha_primera_compra_cliente,
    ROW_NUMBER() OVER (
      PARTITION BY id_cliente_persona
      ORDER BY fecha_compra, id_pedido
    ) AS num_pedido_cliente,
    COUNT(*) OVER (PARTITION BY id_cliente_persona) AS _pedidos_persona
  FROM base
)

SELECT
  id_pedido,
  id_cliente_persona,
  id_cliente_pedido,
  ciudad_cliente,
  estado_cliente,
  estado_pedido,
  fecha_compra,
  fecha_aprobacion_pago,
  fecha_envio_transportista,
  fecha_entrega_cliente,
  fecha_entrega_estimada,
  importe_articulos,
  importe_flete,
  importe_articulos + importe_flete AS importe_total,
  importe_pagado,
  CAST(NULL AS DECIMAL) AS importe_articulos_eur,
  tipo_pago_principal,
  num_plazos,
  CAST(num_articulos AS INTEGER) AS num_articulos,
  nota_resena,
  CAST(date_diff('day', fecha_compra, fecha_entrega_cliente) AS INTEGER) AS dias_entrega,
  CAST(
    date_diff('day', fecha_entrega_estimada, fecha_entrega_cliente) AS INTEGER
  ) AS dias_desviacion_entrega,
  fecha_primera_compra_cliente,
  CAST(num_pedido_cliente AS INTEGER) AS num_pedido_cliente,
  CAST(
    date_diff('month', fecha_primera_compra_cliente, fecha_compra) AS INTEGER
  ) AS meses_desde_primera_compra,
  estado_pedido NOT IN ('canceled', 'unavailable') AS es_venta_valida,
  CASE
    WHEN fecha_entrega_cliente IS NULL THEN NULL
    ELSE date_diff('day', fecha_entrega_estimada, fecha_entrega_cliente) <= 0
  END AS fue_entregado_a_tiempo,
  nota_resena <= 2 AS tiene_resena_negativa,
  _pedidos_persona > 1 AS es_cliente_recurrente,
  num_plazos > 1 AS fue_pagado_a_plazos,
  CAST(NULL AS VARCHAR) AS id_transportista,
  CAST(NULL AS VARCHAR) AS tipo_incidencia
FROM con_historia
