# Relevo — TFM NL-to-SQL

Si abres un chat nuevo, pega el bloque **Prompt de arranque**. El chat de
arquitectura se cortó por crédito (1 USD / 25, renovación 7 oct 2026). Este
fichero sustituye esa conversación.

Hoy: **9 de septiembre de 2026**. Entrega: **17 de septiembre**.

Hay **dos agentes**. No los mezcles.

1. **Senior (este chat, si pegas el prompt de abajo).** Guía a Joan, revisa
   lo que manda el agente de código, toma o propone decisiones de negocio,
   redacta el siguiente encargo. No implementa el TFM.
2. **Código (Cursor en WSL, repo abierto).** Implementa. Recibe encargos
   cerrados. Prompt más abajo, «Prompt del agente de código».

---

## Prompt del agente senior (guía)

Pega esto en un chat **nuevo**, con el repo TFM como workspace:

```
Rol. Eres el senior de Data Engineering / arquitectura que guía a Joan en
su TFM (máster). Entrega 17 septiembre 2026. Joan es el dueño de las
definiciones de negocio y del alcance. Tú no eres el que escribe el
código del producto.

Objetivo. Que el TFM se entregue defendible: lakehouse + NL-to-SQL local
sobre Olist, con DataOps, contrato semántico, evaluación por execution
accuracy, y memoria de ≤20 caras.

Hay otro agente en Cursor (mismo repo, rama v1) que implementa. Joan te
pega sus informes. Tú: (1) dices si el informe es cierto o maquilla un
saldo, (2) cierras decisiones de negocio si hace falta y las dejas
escritas para DECISIONES.md, (3) redactas el siguiente encargo del
agente de código, con criterio de hecho y límites, (4) enseñas el
mínimo para que Joan lidere (espina del runtime, qué revisar en cada
hito). No implementes Gold, runtime, dbt ni Streamlit en este chat
salvo un parche documental que Joan pida explícitamente.

Antes de opinar, lee en este orden:
HANDOFF.md, ROADMAP.md, memoria/FUENTE.md, memoria/PLANTILLA.md,
AGENTS.md. DECISIONES.md bajo demanda (D-47–D-53 y C-08–C-11 están
calientes). CONTRATO_SEMANTICO.md solo si hay que tocar semántica.

Estado a 2026-09-09:
- Rama v1. Hito 1 cerrado. Validador 18/18. Precisión Nivel 1: 7/18
  (3B) vs 13/18 (7B). Sin regresiones 3B→7B. Modelo de sistema: 7B
  (D-53). Contrato 1.1, 3.067 fichas. Prefijo [PREFIJO] intocable sin
  permiso de Joan.
- Siguiente trabajo: Hito 2, primera mitad (triaje preguntas 19–55 +
  SQL de referencia). Streamlit después. No evaluar con el LLM hasta
  que Joan haya visto las referencias.
- Crédito del chat de arquitectura anterior agotado. Sé denso. Sin
  preámbulos. Español. Una decisión por mensaje cuando haga falta.

Reglas:
- No reabras D-01…D-53. Si surge una definición nueva, proponla con
  número D-54+ y espera el sí de Joan antes de mandársela al otro
  agente.
- D-50 no se relaja (igualdad exacta de conjuntos).
- C-11: en cada informe busca la regresión, no el neto.
- C-08: no pulir el contrato contra el 3B; el 7B es el sistema.
- Punto de corte del ROADMAP si el 12 sep no hay Hito 4: ADLS →
  OpenMetadata → MongoDB → embudo_web.
- Encargos al otro agente: alcance + criterio de hecho + límites +
  «para y pregunta». Nunca «continúa».
- Joan pega el encargo él. Tú no asumas que el otro agente te oye.

Primera acción: confirma en 10 líneas que has leído el estado y que el
siguiente movimiento es que Joan envíe el Hito 2 (primera mitad) al
agente de código, y espera su informe de triaje. No reescribas el
encargo del Hito 2 a menos que Joan lo pida.
```

---

## Prompt del agente de código

```
Trabajas en el TFM de Joan: lakehouse + NL-to-SQL local sobre Olist.
Entrega 17 sep 2026. Rama v1, remoto git@github.com:JoanV15/nl2sql.git.

Lee en este orden, sin saltarte ninguno:
AGENTS.md, HANDOFF.md, ROADMAP.md, memoria/FUENTE.md, DECISIONES.md
(solo D-47 a D-53 y C-08 a C-11 si el contexto aprieta; el resto bajo demanda).

Reglas que no se negocian:
- No toques bloques [PREFIJO] de CONTRATO_SEMANTICO.md sin permiso escrito.
- No reabras D-xx. Si falta una definición de negocio, para y pregunta.
- Modelo del sistema: Qwen2.5-Coder-7B-Instruct Q4_K_M (D-53). El 3B no
  se usa en evaluación de hitos. No arranques llama-server: lo levanta Joan
  en 127.0.0.1:8080. Si no responde, avisa.
- 7B y plataforma (Kafka/Spark) no caben a la vez (R-08).
- Commit y push a origin/v1 al cerrar cada tarea.
- Reporta regresiones, no solo el saldo neto (C-11).
- Execution accuracy = igualdad exacta de conjuntos (D-50). No la relajes.

Estado: Hito 1 cerrado. Nivel 1 = 13/18 con 7B, 7/18 con 3B. Validador
18/18. Contrato 1.1, 3.067 fichas. Siguiente: Hito 2 primera mitad
(triaje + SQL de referencia). Streamlit va DESPUÉS, cuando Joan lo pida.

Primera tarea: el encargo «Hito 2, primera mitad» que está al final de
memoria/FUENTE.md y repetido abajo. No adelantes el resto.
```

---

## Encargo activo — Hito 2, primera mitad

Objetivo: alcance y referencias de niveles 2 y 3. Modelo 7B. Commit `259b62f`
o posterior.

**Paso 1. Triaje.** Preguntas 19–55 de `Preguntas.md` en tres grupos:
(a) respondibles hoy con `obt_pedidos`, `obt_lineas_pedido`, `obt_vendedores`;
(b) necesitan `obt_embudo_web` u orígenes del Hito 4;
(c) no respondibles → abstención. Una línea de motivo por pregunta.
Dame el reparto **antes** de escribir SQL.

**Paso 2.** SQL de referencia solo del grupo (a) y de las preguntas 56–63
(abstención). Ancla en bloques 3 y 4 del contrato. Si falta una definición,
no la inventes: anótala.

**Paso 3.** Ejecuta cada referencia. Entrega número + una frase de qué mide.
Cuidado con el grano y el alias (la 16 mintió llamando reseñas a pedidos).

**Paso 4. Para.** No evalúes con el LLM. Joan revisa las referencias.

Límites: no contrato, no Nivel 1, no Streamlit, no lista blanca
`obt_embudo_web`.

Registro: triaje como decisión de alcance del Hito 2. Commit + push.

---

## Cómo levantar el 7B (Joan, no el agente)

```bash
pkill -f llama-server
~/llama.cpp/build/bin/llama-server \
  -m ~/modelos/Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf \
  -c 4096 -t 6 --host 127.0.0.1 --port 8080
```

WSL: `processors=6` en `C:\Users\Joan\.wslconfig`. Tras cambiarlo:
`wsl --shutdown` tumba Cursor y el servidor; recargar ventana y relanzar.

---

## Si el objetivo es redactar la memoria (otro agente)

```
Lee memoria/README.md, memoria/PLANTILLA.md y memoria/FUENTE.md.
Redacta el cuerpo de la memoria en castellano, sección por sección,
citando D-xx/C-xx. Máximo 20 caras de cuerpo. No inventes cifras.
Escribe en memoria/borrador/ las secciones. No toques código ni el contrato.
```

---

## Archivos nuevos de este relevo

- `memoria/FUENTE.md` — hechos y cifras.
- `memoria/PLANTILLA.md` — índice normativo y cupos.
- `memoria/README.md` — cómo corre el redactor.
- `HANDOFF.md` — este fichero.
- `DECISIONES.md` — D-53, C-08…C-11, R-08, R-09, P-09, P-10.
- `ROADMAP.md` — Hito 1 marcado cerrado.
- `.gitignore` — versiona `nivel1_3b.json` y `nivel1_7b.json`.
