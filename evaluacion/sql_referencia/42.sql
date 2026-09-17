SELECT id_vendedor, pct_resenas_negativas, dias_entrega_medio
FROM obt_vendedores
WHERE pct_resenas_negativas IS NOT NULL
  AND dias_entrega_medio IS NOT NULL
ORDER BY id_vendedor;
