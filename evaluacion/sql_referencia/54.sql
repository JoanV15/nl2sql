SELECT canal_captacion, SUM(importe_articulos) AS facturacion
FROM obt_vendedores
WHERE canal_captacion IS NOT NULL
GROUP BY canal_captacion
ORDER BY facturacion DESC, canal_captacion;
