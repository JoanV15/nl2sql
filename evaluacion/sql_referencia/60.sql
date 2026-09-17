-- supuesto: electronica = macro_categoria Electrónica e Informática
SELECT SUM(importe_articulos) AS facturacion
FROM obt_lineas_pedido
WHERE es_venta_valida
  AND macro_categoria = 'Electrónica e Informática';
