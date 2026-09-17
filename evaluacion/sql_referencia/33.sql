-- supuesto: informatica = informatica_acessorios, pcs, pc_gamer
SELECT SUM(importe_articulos) AS facturacion
FROM obt_lineas_pedido
WHERE es_venta_valida
  AND categoria_producto IN ('informatica_acessorios', 'pcs', 'pc_gamer')
  AND fecha_compra >= DATE '2018-10-17' - INTERVAL 6 MONTH
  AND fecha_compra < DATE '2018-10-18';
