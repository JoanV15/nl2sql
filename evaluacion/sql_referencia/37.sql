-- supuesto: informatica = macro_categoria Electrónica e Informática
SELECT STDDEV_SAMP(importe_articulos) AS desviacion_precio
FROM obt_lineas_pedido
WHERE es_venta_valida
  AND macro_categoria = 'Electrónica e Informática'
  AND fecha_compra >= DATE '2018-10-17' - INTERVAL 6 MONTH
  AND fecha_compra < DATE '2018-10-18';
