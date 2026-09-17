SELECT
  DATE_TRUNC('quarter', fecha_compra) AS trimestre,
  id_transportista,
  COUNT(*) AS num_pedidos,
  SUM(importe_articulos) AS valor
FROM obt_pedidos
WHERE tipo_incidencia IN ('extraviado', 'dañado')
GROUP BY 1, 2
ORDER BY 1, 2;
