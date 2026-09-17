SELECT tipo_pago_principal, COUNT(*) AS num_pedidos
FROM obt_pedidos
WHERE tipo_pago_principal IS NOT NULL
GROUP BY tipo_pago_principal
ORDER BY num_pedidos DESC, tipo_pago_principal
LIMIT 1;
