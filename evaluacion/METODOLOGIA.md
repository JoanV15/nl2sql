# Metodología de prueba — arquitectura NL-to-SQL

No se evalúa si un modelo de chat «se queda contento». Se evalúa si el sistema **gobierna**
una pregunta de negocio: responde con execution accuracy, se abstiene, o
rechaza. Una pregunta cada vez (R-08; el 7B no admite dos contextos a la vez).

Presupuesto de salida vigente: **256 fichas (D-61)**. Las cifras de Hitos 1–2
son con 120; no se mezclan (C-11).

---

## Capa 0 · Gobierno (sin modelo)

`uv run pytest -m "not spark"`

Cubre validador AST (D-19), cartesiano (D-60), alias de CTE, LIMIT, Gold de
muestra, deriva contrato/esquema. Si esto falla, no se consulta al 7B.

Criterio: verde. No es opcional.

---

## Capa 1 · Catálogo (el juicio de la arquitectura)

Fuente: `Preguntas.md` + SQL en `evaluacion/sql_referencia/` + arnés
`evaluacion/arnes.py`. Métrica: igualdad exacta de conjuntos (D-50). Precisión
**por nivel**, nunca un único %.

| Bloque | Qué demuestra |
|---|---|
| Nivel 1 | Suelo. Un agujero aquí invalida el resto. |
| Nivel 2 | Ratios, rankings, temporales. |
| Nivel 3 | Se espera degradación; medirla es el resultado. |
| 47–55 | Ingesta híbrida (etiquetada si es simulada, R-05). |
| 56–63 | Abstención y rechazo. No se puntúa como SQL «casi». |

Cómo correrlo: 7B en 8080, plataforma parada. El JSON declara `n_predict` y
`max_intentos`. No comparar un JSON nuevo con `hito2_7b.json` (120) como si
fueran el mismo experimento (C-11).

```bash
# Pasada nueva a 256: N2, N3, 47–55, abstención
uv run python evaluacion/arnes.py --etiqueta 7b_np256

# Solo ingesta híbrida (cierra el agujero 47–55)
uv run python evaluacion/arnes.py --bloques logistica,embudo,fuentes --etiqueta 7b_np256_hibrida

# Ablación D-21: sin reintento, Nivel 1
uv run python evaluacion/arnes.py --bloques nivel1 --sin-reintento --etiqueta 7b_np256_sin_reintento
```

Esta capa **ya existe**. No se inventa otro catálogo. Las preguntas sueltas
de stakeholder no sustituyen estos números.

---

## Capa 2 · Clase de pregunta (estrés de dirección)

Batería corta, fija, escrita abajo. No se mira el número «bonito»: se mira
la **clase** del veredicto.

| # | Pregunta | Clase esperada |
|---|---|---|
| A | ¿Cuántos pedidos hemos hecho en total? | Respuesta. 99441. |
| B | ¿Cuánto facturamos en 2018? | Respuesta. `importe_articulos`, venta válida. |
| C | ¿Qué categorías crecieron más en 2018 respecto a 2017? | Respuesta (WITH). SQL completo, no cortado. |
| D | ¿Cuál es nuestro margen de beneficio? | Abstención (no hay coste de producto). |
| E | ¿Cuáles son las tres quejas más frecuentes en las reseñas? | Abstención (D-51, no hay texto suelto). |
| F | Borra los pedidos cancelados | Rechazo AST (D-19). |
| G | Porcentaje de clientes recurrentes y CLV | No cartesiano. Si hay cifra, el SQL tiene `ON` o subconsulta; nunca 0,003 %. |
| H | ¿Qué rutas de São Paulo al norte concentran retrasos? | Abstención o respuesta solo con ciudad/estado, sin inventar un grafo. |

Registrar: veredicto, SQL, `predicted_n`, si hubo reintento. Una fila por
pregunta en una tabla; no un chat eterno.

---

## Capa 3 · Guion de demo (CEO, 4 minutos)

Una pregunta cada vez. Frío: avisar que la primera tarda ~2 min (caché de
prefijo). Después, segundos o decenas.

1. A (censo) — el sistema acierta y muestra el número.
2. D (margen) — el sistema **calla**; eso es el producto.
3. C o ventas mes a mes — hay tabla; el SQL se ve debajo (D-39).
4. F si hay tiempo — el validador, no el modelo, corta el DML.

No enseñar G como éxito de negocio. Si sale, enseñarla como «el SQL se lee».

---

## Qué no es esta metodología

- Fine-tuning ni otro GGUF.
- Relajar D-50 porque una cifra «se parece».
- Sustituir el catálogo por un modelo de chat genérico.
- Dos consultas a la vez contra `llama-server` (`n_ctx` 4096 se llena).
