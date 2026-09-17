SELECT
  categoria_producto,
  SUM(num_compras) * 1.0 / NULLIF(SUM(num_visitas), 0) AS tasa_conversion
FROM obt_embudo_web
GROUP BY categoria_producto
ORDER BY tasa_conversion DESC, categoria_producto;
