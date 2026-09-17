SELECT SUM(importe_articulos_eur) AS facturacion_eur
FROM obt_pedidos
WHERE es_venta_valida AND YEAR(fecha_compra) = 2017;
