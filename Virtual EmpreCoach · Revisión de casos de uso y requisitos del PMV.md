# Virtual EmpreCoach · Revisión de casos de uso y requisitos del PMV

Nov 17, 2026 · @Cátedra

## Objetivo de la revisión

Esta revisión cierra los casos de uso y requisitos del PMV, primer entregable de la fase «Preparación y corpus» (semanas S1–S2 del [Plan de desarrollo de Virtual EmpreCoach](https://claude.ai/artifact/Pk7kpGqGSHLXJTHsgRacPR)). Lo que se apruebe aquí fija el alcance de las fases de ingesta, generación, interfaz y evaluación.

Todo lo escrito es una **propuesta de partida** derivada del plan; no son decisiones del equipo hasta que se marquen como aprobadas. Cada caso de uso y requisito tiene una columna «Decisión» para registrar si se aprueba, se modifica o se descarta.

## Punto de partida

Cinco decisiones ya están fijadas y no se revisan aquí; los casos de uso deben ser compatibles con ellas.

| Decisión fijada | Origen |
| --- | --- |
| Arquitectura RAG con dos procesos: ingesta y generación | Artículo de Trujillo Sáez y Romero Olmedo |
| Back-end en Python con Flask; front-end en HTML, CSS y JavaScript | Artículo |
| Evaluación automática (usuario simulado) más evaluación humana | Artículo |
| PMV = pregunta y respuesta por texto desde una página web, con citas y búsqueda web opcional | Plan de desarrollo |
| Servidor local (protección de datos); Telegram y app después del PMV, sin procesamiento de imágenes | Plan de desarrollo |

## Actores

El actor principal es el estudiante del Máster en Educación Digital y Emprendimiento, que es quien participa en el piloto; los demás actores son internos del equipo.

| Actor | Quién es | Qué hace en el PMV | Por confirmar |
| --- | --- | --- | --- |
| Estudiante | Estudiante del Máster (piloto) | Pregunta, consulta fuentes, activa la búsqueda web, valora respuestas | ¿Se abre a otros estudiantes o emprendedores externos? |
| Docente | Profesorado del Máster | Propone documentos del corpus y preguntas de prueba; revisa respuestas | ¿Necesita ver conversaciones agregadas en el PMV? |
| Gestor del corpus | Miembro del equipo | Añade, actualiza y retira documentos; lanza la ingesta | Quién asume el rol |
| Evaluador | Miembro del equipo | Mantiene el conjunto de prueba, ejecuta la evaluación y analiza el registro | Quién asume el rol |
| Administrador técnico | Miembro del equipo | Despliega, monitoriza y hace copias del servidor | Quién asume el rol |
| Sistemas externos | Modelo local, Qdrant, SearXNG | Generan, recuperan y buscan | — |

## Casos de uso del PMV

Se proponen 12 casos de uso: 7 del estudiante, que son el núcleo del PMV, y 5 internos de gestión y evaluación. El CU-12 (orientación personalizada) es el más dudoso y conviene decidirlo primero, porque cambia el prompt y la evaluación.

| ID | Caso de uso | Actor | Flujo principal | Alternativas y excepciones | Decisión |
| --- | --- | --- | --- | --- | --- |
| CU-01 | Hacer una pregunta sobre emprendimiento | Estudiante | Escribe la pregunta → el sistema recupera fragmentos del corpus → genera la respuesta en streaming con citas | Pregunta ambigua: el sistema pide precisión | Pendiente |
| CU-02 | Pregunta sin respuesta en el corpus | Estudiante | El sistema no encuentra fragmentos suficientes → indica que no tiene la información y sugiere activar la búsqueda web | Si la búsqueda web ya está activa, se aplica CU-03 | Pendiente |
| CU-03 | Preguntar con búsqueda web | Estudiante | Activa el interruptor → el sistema consulta SearXNG y combina web y corpus → la respuesta separa qué viene de cada origen | Sin resultados web: responde solo con el corpus y lo indica. Tiempo de respuesta mayor | Pendiente |
| CU-04 | Consultar las fuentes citadas | Estudiante | Pulsa una cita → ve el documento, página o URL y el fragmento usado | Documento con acceso restringido: muestra solo la referencia | Pendiente |
| CU-05 | Conversación de varios turnos | Estudiante | Hace preguntas de seguimiento → el sistema usa el historial de la sesión | Historial largo: se recorta o resume | Pendiente |
| CU-06 | Valorar una respuesta | Estudiante | Pulsa útil / no útil y, opcionalmente, escribe un comentario | — | Pendiente |
| CU-07 | Iniciar y cerrar sesión de chat | Estudiante | Abre la web → ve el aviso de privacidad y lo acepta → conversa → puede borrar la conversación | No acepta el aviso: no puede usar el chat | Pendiente |
| CU-08 | Pregunta fuera de dominio o inadecuada | Estudiante | El sistema reconoce que la pregunta no trata de emprendimiento, o pide asesoría legal, fiscal o financiera vinculante → responde con un límite claro y, si procede, remite a un servicio | Contenido ofensivo o datos personales: no responde y avisa | Pendiente |
| CU-09 | Gestionar el corpus | Gestor del corpus | Añade, actualiza o retira un documento con sus metadatos y permisos → lanza la ingesta → comprueba que queda indexado | Formato no admitido o fallo de extracción: se registra el error | Pendiente |
| CU-10 | Ejecutar la evaluación | Evaluador | Lanza el conjunto de prueba y el usuario simulado → obtiene métricas frente a los umbrales | — | Pendiente |
| CU-11 | Revisar el registro de interacciones | Evaluador, docente | Consulta preguntas, fragmentos recuperados y valoraciones seudonimizadas; exporta para análisis | — | Pendiente |
| CU-12 | Recibir orientación sobre su propio proyecto | Estudiante | Describe su idea → el sistema hace preguntas de coaching y propone pasos basados en el corpus | **Por decidir:** ¿entra en el PMV o se limita a preguntas y respuestas? | Pendiente |

## Requisitos funcionales

Se proponen 16 requisitos funcionales, 11 imprescindibles para dar el PMV por cerrado. La prioridad es una propuesta inicial que el equipo debe confirmar.

| ID | Requisito | Casos de uso | Prioridad | Decisión |
| --- | --- | --- | --- | --- |
| RF-01 | Ingesta de documentos PDF, DOCX y páginas web con metadatos (título, autor, fecha, tipo, licencia) | CU-09 | Imprescindible | Pendiente |
| RF-02 | Fragmentación e indexación en Qdrant; reindexado sin reentrenar el modelo | CU-09 | Imprescindible | Pendiente |
| RF-03 | Recuperación semántica de los fragmentos más relevantes para cada pregunta | CU-01, CU-05 | Imprescindible | Pendiente |
| RF-04 | Respuesta generada solo a partir de los fragmentos recuperados, en español | CU-01 | Imprescindible | Pendiente |
| RF-05 | Toda afirmación relevante lleva cita a su fuente (documento y página, o URL) | CU-01, CU-04 | Imprescindible | Pendiente |
| RF-06 | Si no hay información suficiente, el sistema lo dice en lugar de inventar | CU-02 | Imprescindible | Pendiente |
| RF-07 | Respuesta en streaming | CU-01 | Imprescindible | Pendiente |
| RF-08 | Historial de la sesión usado como contexto en preguntas de seguimiento | CU-05 | Imprescindible | Pendiente |
| RF-09 | Búsqueda web activable por el usuario, con citas que distinguen web y corpus | CU-03 | Deseable | Pendiente |
| RF-10 | Vista de la fuente citada con el fragmento usado | CU-04 | Deseable | Pendiente |
| RF-11 | Valoración útil / no útil por respuesta, con comentario opcional | CU-06 | Imprescindible | Pendiente |
| RF-12 | Registro seudonimizado de pregunta, fragmentos, respuesta, modelo y valoración | CU-10, CU-11 | Imprescindible | Pendiente |
| RF-13 | Exportación del registro (CSV o JSON) para análisis | CU-11 | Deseable | Pendiente |
| RF-14 | Aviso de privacidad y aceptación antes del primer uso | CU-07 | Imprescindible | Pendiente |
| RF-15 | Filtro de preguntas fuera de dominio y aviso de límites (no asesoría legal, fiscal ni financiera) | CU-08 | Deseable | Pendiente |
| RF-16 | Ejecución automatizada del conjunto de prueba y del usuario simulado | CU-10 | Deseable | Pendiente |

## Requisitos no funcionales

Los umbrales de calidad repiten los del plan de evaluación; los de rendimiento son una propuesta a partir de las estimaciones del plan y deben medirse en el servidor real.

| ID | Ámbito | Requisito | Cómo se verifica | Decisión |
| --- | --- | --- | --- | --- |
| RNF-01 | Privacidad | Modelo, base vectorial y registro en el servidor local; ningún dato de conversación sale a servicios externos, salvo la consulta de búsqueda web sin datos personales | Revisión de arquitectura y del tráfico de red | Pendiente |
| RNF-02 | Privacidad | Registro seudonimizado, periodo de conservación definido y borrado a petición; revisión con el delegado de protección de datos de la UGR | Informe del DPD | Pendiente |
| RNF-03 | Ética | Consentimiento informado para el piloto y consulta al comité de ética de la UGR si procede | Documento aprobado antes del piloto | Pendiente |
| RNF-04 | Calidad | Recuperación ≥ 80 %, fidelidad ≥ 85 %, citas correctas ≥ 90 %, fuera de dominio ≥ 90 %, URL web correctas ≥ 85 % | Conjunto de prueba de unas 100 preguntas (CU-10) | Pendiente |
| RNF-05 | Rendimiento | Primera palabra en ≤ 3 s y respuesta completa en ≤ 15 s con 1 usuario sin búsqueda web (propuesta) | Prueba de carga | Pendiente |
| RNF-06 | Capacidad | Una clase de 25–30 estudiantes preguntando a la vez sin errores, aunque con más espera | Prueba de carga con usuarios concurrentes | Pendiente |
| RNF-07 | Accesibilidad | Interfaz conforme a WCAG 2.1 AA y usable en móvil | Auditoría de accesibilidad | Pendiente |
| RNF-08 | Identidad | Interfaz con la identidad visual de la Cátedra Ceuta-IATEB | Revisión de diseño | Pendiente |
| RNF-09 | Idioma | Interfaz y respuestas en español; documentos del corpus en español o inglés | Muestra del conjunto de prueba | Pendiente |
| RNF-10 | Mantenibilidad | API Flask documentada y reutilizable por Telegram y la app; modelo intercambiable por API compatible con OpenAI; despliegue con Docker | Revisión de código y prueba de cambio de modelo | Pendiente |
| RNF-11 | Seguridad | HTTPS, límite de peticiones por sesión y protección frente a inyección de instrucciones en documentos y páginas web | Pruebas de seguridad básicas | Pendiente |

## Fuera del PMV

Según el plan, estas funciones quedan fuera del PMV; cualquier propuesta nueva de la revisión que no sea imprescindible se añade aquí.

- Cuentas de usuario e inicio de sesión personal (el PMV usa sesiones anónimas).
- Entrada o salida por voz.
- Procesamiento de imágenes (descartado del proyecto).
- Integración con Telegram (fase posterior 1).
- App instalable, PWA o nativa (fase posterior 2), y funcionamiento sin conexión.
- Propuesta: panel de administración con interfaz gráfica; en el PMV, corpus y evaluación se gestionarían con scripts.

## Preguntas abiertas

Ocho preguntas condicionan el cierre; las tres primeras cambian el alcance y deben resolverse en la primera sesión.

- [ ] ¿El PMV es solo pregunta y respuesta, o incluye orientación personalizada sobre el proyecto del estudiante (CU-12)?
- [ ] ¿Quién puede usar el PMV: solo estudiantes del Máster en el piloto, o también otros públicos?
- [ ] ¿Qué temas cubre el corpus (idea de negocio, modelo de negocio, financiación, aspectos legales…) y qué documentos entran en el primer inventario?
- [ ] ¿Se conserva el historial entre sesiones o solo dentro de una sesión? Afecta a RF-08 y a privacidad.
- [ ] ¿Cuánto tiempo se conservan los registros y quién accede a ellos?
- [ ] ¿Los docentes necesitan ver conversaciones agregadas durante el piloto (CU-11)?
- [ ] ¿Qué tiempos de respuesta son aceptables para el piloto (RNF-05) y cuántos estudiantes usarán el sistema a la vez?
- [ ] ¿Quién asume los roles de gestor del corpus, evaluador y administrador técnico?

## Procedimiento y criterios de cierre

La revisión cabe en las dos semanas de la fase con dos sesiones de trabajo; las fechas y los asistentes están por fijar.

1. Lectura individual del documento; cada persona deja comentarios en las filas que quiera cambiar.
2. Sesión 1, alcance: resolver las tres primeras preguntas abiertas y decidir cada caso de uso.
3. Sesión 2, requisitos: confirmar prioridad y decisión de cada requisito y ajustar los umbrales.
4. Contraste con al menos un docente del Máster (propuesta) sobre CU-01 a CU-08 y el contenido del corpus.
5. Aprobación final y enlace del documento desde la ficha del proyecto en el Drive.

La fase se da por cerrada cuando se cumplen estas condiciones:

- [ ] Ningún caso de uso ni requisito queda en «Pendiente».
- [ ] Las preguntas abiertas están resueltas o pasan explícitamente a una fase posterior.
- [ ] Cada requisito imprescindible tiene su forma de verificación.
- [ ] Las primeras 30 preguntas de prueba están redactadas y vinculadas a CU-01, CU-02, CU-03 y CU-08.

### Registro de cambios

| Fecha | Cambio | Quién |
| --- | --- | --- |
| 17/11/2026 | Borrador inicial a partir del plan de desarrollo | Asistente de la Cátedra |
