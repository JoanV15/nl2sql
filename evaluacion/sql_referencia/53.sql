SELECT AVG(dias_hasta_primera_venta) AS dias_medio
FROM obt_vendedores
WHERE fecha_captacion IS NOT NULL AND fecha_primera_venta IS NOT NULL;
