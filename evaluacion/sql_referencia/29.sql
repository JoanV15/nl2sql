SELECT tipo_pago_principal,
       SUM(importe_articulos) / COUNT(*) AS ticket_medio
FROM obt_pedidos
WHERE es_venta_valida AND tipo_pago_principal IS NOT NULL
GROUP BY tipo_pago_principal
ORDER BY ticket_medio DESC, tipo_pago_principal;
