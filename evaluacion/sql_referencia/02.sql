SELECT SUM(importe_articulos) AS facturacion
FROM obt_pedidos
WHERE es_venta_valida AND YEAR(fecha_compra) = 2018;
