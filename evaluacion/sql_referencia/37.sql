-- supuesto: informatica = informatica_acessorios, pcs, pc_gamer
SELECT STDDEV_SAMP(importe_articulos) AS desviacion_precio
FROM obt_lineas_pedido
WHERE es_venta_valida
  AND categoria_producto IN ('informatica_acessorios', 'pcs', 'pc_gamer')
  AND fecha_compra >= DATE '2018-10-17' - INTERVAL 6 MONTH
  AND fecha_compra < DATE '2018-10-18';
