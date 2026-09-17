SELECT estado_vendedor, AVG(dias_entrega) AS dias_entrega_medio
FROM (
  SELECT DISTINCT id_pedido, estado_vendedor, dias_entrega
  FROM obt_lineas_pedido
  WHERE dias_entrega IS NOT NULL
)
GROUP BY estado_vendedor
ORDER BY dias_entrega_medio, estado_vendedor;
