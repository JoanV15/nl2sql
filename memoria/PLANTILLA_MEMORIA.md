# Plantilla de la memoria

Esqueleto de redacción según el índice obligatorio de la normativa. Cada
sección indica qué debe contener, de qué fichero del repositorio sale el
material y cuánto espacio le corresponde.

## Restricciones de la normativa

- **Máximo 20 caras**, sin contar portada, índice, bibliografía y anexos.
- Índice obligatorio: todas las secciones que apliquen.
- El repositorio debe estar en GitHub con acceso para los tutores.
- La calidad del código puntúa: legibilidad, formato, comentarios, tests
  unitarios y, si es posible, un artefacto empaquetado.
- Entrega comprimida como `Joan_Apellido1_Apellido2_TFM.zip`, con la memoria,
  el enlace al repositorio y el enlace al vídeo.
- Vídeo de 3 a 5 minutos, nunca más de 5, subido a YouTube como oculto.

**Instrucción para el agente redactor.** Escribe en castellano, en prosa
continua y en primera persona del plural. No uses viñetas para lo que puede ir
en un párrafo. Toda cifra debe salir de `memoria/HALLAZGOS.md` con sus
condiciones de medida; si no está allí, no se escribe. Toda decisión de diseño
debe remitir a su identificador de `DECISIONES.md`.

---

## Reparto de espacio

| Sección | Caras |
|---|---|
| 1-2 · Resumen y palabras clave | 0,5 |
| 3 · Introducción | 2 |
| 4 · Metodología | 1,5 |
| 5 · Arquitectura | 4 |
| 6 · Solución tecnológica | 5 |
| 7 · Resultados y conclusiones | 6 |
| **Total** | **19** |

La sección 7 es la más extensa a propósito: es donde vive la aportación
diferencial del trabajo y el criterio de valoración con más peso.

---

## 1-2 · Resumen y palabras clave

Qué se ha construido, sobre qué datos, con qué resultado cuantificado y cuál es
el hallazgo principal. El resumen debe contener al menos una cifra.

Palabras clave sugeridas: NL-to-SQL, contrato semántico, lakehouse, LLM local,
gobierno del dato, evaluación de sistemas generativos.

## 3 · Introducción

Contextualización, objetivos y justificación técnica y de negocio.

El problema: los datos de negocio están fuera del alcance de quien toma las
decisiones porque interrogarlos exige SQL. La respuesta habitual, conectar un
modelo de lenguaje a la base de datos, traslada el problema en lugar de
resolverlo, porque un sistema que responde con seguridad a lo que no sabe es
peor que uno que no responde.

Objetivo: un sistema que traduce lenguaje natural a SQL sobre una plataforma de
datos gobernada, que se ejecuta íntegramente en local y que **se abstiene
cuando no puede responder**. La abstención gobernada es la tesis del trabajo.

**Fuentes:** `ARQUITECTURA.md` (objetivos y principios), `Preguntas.md`.

## 4 · Metodología

Diseño general y proceso de trabajo por fases.

Cubrir: el desarrollo por rebanadas verticales y anillos incrementales (D-23) y
los siete hitos de `ROADMAP.md`; el catálogo de 63 preguntas estratificadas
como requisito funcional **y** conjunto de evaluación, definido antes de
construir; y el criterio de evaluación por *execution accuracy* con igualdad
exacta de conjuntos, fijado antes de conocer los resultados (D-50, H-07).

Incluir aquí la lección metodológica sobre desarrollo asistido por agentes
(H-08) y sobre la fragilidad del conjunto de referencia (H-04). Son parte
honesta del proceso y demuestran criterio.

**Fuentes:** `ROADMAP.md`, `DECISIONES.md`, `memoria/HALLAZGOS.md`.

## 5 · Arquitectura

Exige diagrama de alto nivel, descripción técnica, justificación de
herramientas, **estimación de costes de infraestructura** y estrategia DevOps.

El diagrama de Mermaid está en `ARQUITECTURA.md`. La justificación de cada
herramienta sale de su decisión correspondiente; conviene citar también alguna
alternativa descartada, porque descartar con motivo demuestra más criterio que
elegir.

Dedicar un apartado a las restricciones de recursos como motor de diseño: 16 GB
de RAM, inferencia solo en CPU y ejecución secuencial de los componentes
pesados. Casi todas las decisiones difíciles del proyecto derivan de ahí, y
H-05 demuestra que la asignación de recursos del virtualizador afecta
directamente al rendimiento medido.

**Hueco por cubrir:** la estimación de costes no existe todavía. Debe comparar
el despliegue local con su equivalente gestionado en nube.

**Fuentes:** `ARQUITECTURA.md`, `DECISIONES.md`, H-05.

## 6 · Solución tecnológica

Fuentes, preparación, flujos, procesamiento batch y streaming, orquestación,
almacenamiento, modelo de explotación y **consideraciones éticas y legales**.

El núcleo diferencial es el contrato semántico y el camino de una consulta:
prefijo invariante, generación, extracción, validación sobre el árbol
sintáctico, ejecución aislada y traza. Merece explicarse con detalle, sobre
todo por qué la validación es sobre el AST y no por palabras clave, y por qué
el `LIMIT` se inyecta reescribiendo antes de validar, de modo que lo validado
sea exactamente lo ejecutado.

Explicar también que el catálogo de columnas del validador se deriva del mismo
contrato que ve el modelo, lo que hace imposible por construcción que una
columna alucinada llegue a ejecutarse.

**Hueco por cubrir:** las consideraciones éticas y legales. Cubrir la licencia
del dataset de Olist, el etiquetado explícito de los orígenes simulados, y el
riesgo de que una respuesta errónea se presente con apariencia de autoridad,
que es precisamente lo que mitiga la política de abstención.

**Fuentes:** `CONTRATO_SEMANTICO.md`, `ARQUITECTURA.md`, `src/tfm_nlsql/`.

## 7 · Resultados y conclusiones

Logros, métricas, comparativas, limitaciones y líneas futuras. La sección más
importante y la que más espacio recibe.

Estructura recomendada:

Primero, la métrica y por qué se eligió, con su coste declarado (H-07).
Después, la ablación de tamaño de modelo, que es el resultado central: la tabla
completa de H-03 con precisión, adherencia al contrato y latencia. Debe
presentarse como un compromiso medido, no como «el grande es mejor».

A continuación, el hallazgo de H-02: los ejemplos del contrato pesan más que
sus reglas en prosa. Es el resultado más interesante del trabajo porque
contradice la intuición de que basta con escribir la norma, y se sostiene sobre
dos evidencias independientes, la persistencia del filtro espurio y su caída al
aumentar la escala.

Luego, la curva de degradación por nivel de dificultad, cuando existan los
niveles 2 y 3, y el comportamiento del bloque de abstención.

Las limitaciones, sin adornos: inferencia en CPU, un único dominio, orígenes
simulados para parte de las preguntas, y el hecho de que cinco preguntas del
Nivel 1 siguen fallando y por qué, con la taxonomía de `HALLAZGOS.md`.

Líneas futuras: imposición de las reglas del contrato en el validador en lugar
de confiarlas al modelo, que es la conclusión natural de H-02; ajuste fino
frente a contrato en prompt; y el paso a un despliegue con GPU.

**Fuentes:** `memoria/HALLAZGOS.md` íntegro,
`evaluacion/resultados/nivel1_*.json`.

## 8 · Anexos

Fuera del límite de 20 caras. Aquí van el catálogo completo de las 63 preguntas,
el contrato semántico íntegro, el detalle de las decisiones, capturas de la
interfaz y las condiciones de reproducibilidad, incluidas las de H-05.

---

## Guion del vídeo, de 3 a 5 minutos

El jurado valora, por este orden, la aplicación de las técnicas del máster, los
resultados, la exposición y la innovación. Reparto sugerido: medio minuto para
el problema, uno para la arquitectura sobre el diagrama, minuto y medio de
demostración en vivo incluyendo **una pregunta que el sistema rechace**, un
minuto para la ablación, y medio minuto de conclusión.

La abstención en directo es el momento más valioso del vídeo: es lo que
distingue este trabajo de un generador de SQL cualquiera.

Plazo de la competición de becas: 24 de septiembre a las 23:59. Es posterior a
la entrega del TFM, así que el vídeo admite una segunda versión más cuidada si
se decide concursar.
