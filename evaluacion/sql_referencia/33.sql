-- supuesto: informatica = macro_categoria Electrónica e Informática
SELECT SUM(importe_articulos) AS facturacion
FROM obt_lineas_pedido
WHERE es_venta_valida
  AND macro_categoria = 'Electrónica e Informática'
  AND fecha_compra >= DATE '2018-10-17' - INTERVAL 6 MONTH
  AND fecha_compra < DATE '2018-10-18';
