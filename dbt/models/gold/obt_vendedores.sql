{{ config(materialized='table') }}

-- Censo de vendedores con actividad por la izquierda (D-44). No deriva de las líneas.

WITH pedido_vendedor AS (
  SELECT
    i.seller_id AS id_vendedor,
    i.order_id AS id_pedido,
    MIN(CAST(o.order_purchase_timestamp AS TIMESTAMP)) AS fecha_compra,
    SUM(i.price) AS importe_articulos,
    COUNT(*) AS num_articulos,
    MAX(o.order_status) AS estado_pedido,
    MAX(CAST(o.order_delivered_customer_date AS TIMESTAMP)) AS fecha_entrega_cliente,
    MAX(CAST(o.order_estimated_delivery_date AS TIMESTAMP)) AS fecha_entrega_estimada,
    MAX(r.nota_resena) AS nota_resena
  FROM {{ ref('stg_order_items') }} AS i
  INNER JOIN {{ ref('stg_orders') }} AS o ON i.order_id = o.order_id
  LEFT JOIN {{ ref('int_resenas_pedido') }} AS r ON i.order_id = r.order_id
  GROUP BY i.seller_id, i.order_id
),

actividad AS (
  SELECT
    id_vendedor,
    MIN(fecha_compra) FILTER (
      WHERE estado_pedido NOT IN ('canceled', 'unavailable')
    ) AS fecha_primera_venta,
    COUNT(DISTINCT id_pedido) FILTER (
      WHERE estado_pedido NOT IN ('canceled', 'unavailable')
    ) AS num_pedidos,
    SUM(num_articulos) FILTER (
      WHERE estado_pedido NOT IN ('canceled', 'unavailable')
    ) AS num_articulos_vendidos,
    SUM(importe_articulos) FILTER (
      WHERE estado_pedido NOT IN ('canceled', 'unavailable')
    ) AS importe_articulos,
    AVG(nota_resena) FILTER (
      WHERE estado_pedido NOT IN ('canceled', 'unavailable')
      AND nota_resena IS NOT NULL
    ) AS nota_resena_media,
    AVG(CASE WHEN nota_resena <= 2 THEN 1.0 ELSE 0.0 END) FILTER (
      WHERE estado_pedido NOT IN ('canceled', 'unavailable')
      AND nota_resena IS NOT NULL
    ) AS pct_resenas_negativas,
    AVG(date_diff('day', fecha_compra, fecha_entrega_cliente)) FILTER (
      WHERE estado_pedido NOT IN ('canceled', 'unavailable')
      AND fecha_entrega_cliente IS NOT NULL
    ) AS dias_entrega_medio,
    AVG(
      CASE
        WHEN date_diff('day', fecha_entrega_estimada, fecha_entrega_cliente) > 0
          THEN 1.0
        ELSE 0.0
      END
    ) FILTER (
      WHERE estado_pedido NOT IN ('canceled', 'unavailable')
      AND fecha_entrega_cliente IS NOT NULL
    ) AS pct_pedidos_con_retraso
  FROM pedido_vendedor
  GROUP BY id_vendedor
)

SELECT
  s.seller_id AS id_vendedor,
  s.seller_city AS ciudad_vendedor,
  s.seller_state AS estado_vendedor,
  CAST(NULL AS TIMESTAMP) AS fecha_captacion,
  CAST(NULL AS VARCHAR) AS canal_captacion,
  CAST(NULL AS VARCHAR) AS segmento_negocio,
  a.fecha_primera_venta,
  CAST(NULL AS INTEGER) AS dias_hasta_primera_venta,
  CAST(COALESCE(a.num_pedidos, 0) AS INTEGER) AS num_pedidos,
  CAST(COALESCE(a.num_articulos_vendidos, 0) AS INTEGER) AS num_articulos_vendidos,
  COALESCE(a.importe_articulos, 0) AS importe_articulos,
  a.nota_resena_media,
  a.pct_resenas_negativas,
  a.dias_entrega_medio,
  a.pct_pedidos_con_retraso
FROM {{ ref('stg_sellers') }} AS s
LEFT JOIN actividad AS a ON s.seller_id = a.id_vendedor
