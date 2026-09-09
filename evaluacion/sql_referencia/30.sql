SELECT id_vendedor, pct_resenas_negativas
FROM obt_vendedores
WHERE pct_resenas_negativas > 0.1
ORDER BY pct_resenas_negativas DESC, id_vendedor;
