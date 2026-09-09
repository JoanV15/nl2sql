SELECT CASE WHEN estado_cliente = 'SP' THEN 'SP' ELSE 'resto' END AS grupo,
       SUM(importe_articulos) AS facturacion
FROM obt_pedidos
WHERE es_venta_valida
GROUP BY grupo
ORDER BY grupo;
