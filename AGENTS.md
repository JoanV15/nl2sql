# Contexto para agentes — TFM NL-to-SQL

El estilo de desarrollo lo fija `.cursor/rules/ponytail.mdc`, que se carga
automáticamente. Este documento aporta el contexto del proyecto y no lo repite.

## Qué es esto

Trabajo Fin de Máster. Plataforma de datos de extremo a extremo con un sistema
NL-to-SQL: un modelo de lenguaje local traduce preguntas de negocio en
castellano a SQL validado y ejecutado sobre una capa analítica gobernada.
Dataset base: Olist, comercio electrónico brasileño.

**Entrega: 17 de septiembre de 2026.** El calendario es la restricción
dominante. Ante la duda entre hacer algo bien y hacer algo más, hazlo bien y no
hagas lo demás.

## Documentos que gobiernan este repositorio

Léelos antes de escribir código. Están en la raíz.

| Documento | Qué contiene | Cuándo consultarlo |
|---|---|---|
| `DECISIONES.md` | Decisiones D-01 a D-53 y conclusiones C-01 a C-11 | **Siempre.** Es la fuente de verdad |
| `ROADMAP.md` | Hitos, criterio de hecho y punto de corte. Entrega 17 sep 2026 | Antes de ampliar alcance |
| `ARQUITECTURA.md` | Arquitectura consolidada, componentes y fronteras de cómputo | Antes de tocar cualquier componente |
| `CONTRATO_SEMANTICO.md` | Prefijo del prompt. **No toques `[PREFIJO]` sin permiso** | Al trabajar en Gold o en el runtime |
| `Preguntas.md` | Catálogo de evaluación (63, con 49 y 52 descartadas) | Al diseñar modelos o evaluar |
| `memoria/FUENTE.md` | Hechos, cifras y hallazgos para redactar la memoria | Al escribir la memoria o al retomar el proyecto |
| `HANDOFF.md` | Estado y primer encargo si este chat se corta | Al abrir un agente nuevo |

Si `ARQUITECTURA.md` y `DECISIONES.md` discrepan, prevalece `DECISIONES.md`.

## Reglas específicas de este proyecto

**No tomes decisiones de arquitectura por tu cuenta.** Si una tarea exige una
decisión que no está en `DECISIONES.md`, detente y pregunta. Las decisiones
tomadas por inercia durante la implementación son irreversibles en la práctica
y no se pueden defender ante un tribunal.

**Toda decisión nueva se registra en `DECISIONES.md`** con el formato existente:
contexto, decisión, justificación, alternativas descartadas. El registro es
material evaluable, no burocracia.

**Nomenclatura (D-36).** La capa Gold va íntegramente en castellano,
`snake_case`, sin tildes ni eñes en identificadores. Bronze y Silver conservan
los nombres de origen. Los valores de dato, como las categorías de producto en
portugués, no se traducen.

**Fronteras de cómputo.** Spark solo de Bronze a Silver. DuckDB solo de Silver
a Gold y en consulta. No hay un tercer motor: Polars quedó eliminado en D-04 y
no debe reaparecer.

**Capa Gold: cuatro OBT, no una (D-11).** `obt_pedidos`, `obt_lineas_pedido`,
`obt_vendedores` y `obt_embudo_web`, cada una con grano declarado. El esquema
está cerrado en `CONTRATO_SEMANTICO.md`.

**Sin frameworks que encapsulen el núcleo NL-to-SQL (D-05).** Nada de
LlamaIndex, LangChain ni equivalentes en la generación, validación o ejecución
de SQL. Delegarían justamente la contribución que el trabajo debe demostrar.

**El contrato semántico es un prefijo invariante (D-33).** Cualquier cambio en
el orden o el contenido de `CONTRATO_SEMANTICO.md` invalida la caché de prefijo
y multiplica la latencia por veinte. La parte variable del prompt va siempre al
final. No interpoles valores dentro del contrato.

**La seguridad no vive en el prompt (D-19).** El mecanismo real es un validador
sobre el AST más una conexión en modo solo lectura. Que el prompt pida solo
`SELECT` es una ayuda al modelo, no un control. No implementes el validador
buscando palabras clave en una cadena: hay que analizar el árbol sintáctico.

**`JOIN` no es una operación prohibida.** Está desaconsejada entre las cuatro
OBT porque la desnormalización la hace innecesaria, pero las subconsultas, los
`WITH` y las autoagregaciones sobre una misma tabla son imprescindibles para el
nivel 3 del catálogo de preguntas.

**Las banderas precalculadas no ocultan la columna cruda (D-13).**
`es_venta_valida` es un atajo; `estado_pedido` sigue siendo consultable. Las
preguntas 8 y 44 dependen de ello.

**Fecha de referencia 2018-10-17 (D-15).** El dataset termina ahí. Ninguna
expresión temporal se resuelve contra el reloj del sistema.

**Modelo del sistema: 7B (D-53).** Qwen2.5-Coder-7B-Instruct Q4_K_M. El 3B
es solo brazo de ablación. No levantes los dos `llama-server` a la vez.

**Memoria (C-03, R-08).** El presupuesto real es de 6 a 7 GB para contenedores,
no de 16. Plataforma e inferencia no se ejecutan a la vez.

**La nube está permitida (D-07, D-28).** El almacenamiento usa una ruta
configurable: local por defecto y ADLS Gen2 mediante Azure for Students. El
diseño no debe depender de la nube, pero tampoco excluirla.

## Herramientas

`uv` para entorno y dependencias, `pytest` para pruebas, `ruff` para linter y
formato, `pyproject.toml` como declaración única (D-40). Estructura del
repositorio en D-41 y en la sección 6 de `ARQUITECTURA.md`.

## Idioma

Identificadores y comentarios en castellano en la capa Gold y en el dominio de
negocio, según D-36. Nombres de librerías, comandos, palabras clave de SQL y
mensajes de error se mantienen tal cual. Documentación y mensajes de commit, en
castellano.

## Qué no hacer

No comprimas los documentos `.md` de la raíz. Son entregables académicos y su
prosa forma parte de lo que se evalúa.

No añadas tecnologías para ampliar el escaparate. Cada componente de esta
arquitectura existe porque una pregunta del catálogo o un requisito normativo
lo exige, y así está justificado en `DECISIONES.md`.

No inventes columnas. Si una tarea parece necesitar una columna que no existe
en `CONTRATO_SEMANTICO.md`, es una decisión de arquitectura: pregunta.
