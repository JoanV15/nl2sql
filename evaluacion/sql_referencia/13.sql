SELECT ciudad_cliente, SUM(importe_articulos) AS ingresos
FROM obt_pedidos
WHERE es_venta_valida
GROUP BY ciudad_cliente
ORDER BY ingresos DESC, ciudad_cliente
LIMIT 1;
