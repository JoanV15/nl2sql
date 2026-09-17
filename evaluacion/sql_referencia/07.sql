SELECT AVG(nota_resena) AS nota_media
FROM obt_pedidos
WHERE nota_resena IS NOT NULL;
