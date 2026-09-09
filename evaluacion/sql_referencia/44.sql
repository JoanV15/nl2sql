SELECT DATE_TRUNC('month', fecha_compra) AS mes,
       id_vendedor,
       SUM(importe_articulos) AS importe_perdido
FROM obt_lineas_pedido
WHERE estado_pedido = 'unavailable'
GROUP BY mes, id_vendedor
ORDER BY mes, id_vendedor;
