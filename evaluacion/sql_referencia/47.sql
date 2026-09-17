SELECT id_transportista, COUNT(*) AS num_retrasos
FROM obt_pedidos
WHERE dias_desviacion_entrega > 0 AND id_transportista IS NOT NULL
GROUP BY id_transportista
ORDER BY num_retrasos DESC
LIMIT 1;
