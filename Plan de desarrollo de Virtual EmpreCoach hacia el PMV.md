# Plan de desarrollo de Virtual EmpreCoach: hacia el PMV

## Resumen y objetivo

El plan parte del artículo *AI in entrepreneurship training in higher education: foundations for the design of Virtual EmpreCoach* (Trujillo Sáez y Romero Olmedo, Cátedra Ceuta-IATEB). Del artículo se toman tres decisiones ya fijadas: arquitectura RAG con dos procesos (ingesta y generación), back-end en Python con Flask y front-end en HTML, CSS y JavaScript, y evaluación automática (usuario simulado) más evaluación humana.

## Alcance del PMV y fases posteriores

El PMV se limita a pregunta y respuesta por texto desde una página web, con respuestas basadas en el corpus documental y, cuando el usuario la activa, en una búsqueda web, citando siempre sus fuentes. Todo lo demás queda fuera del PMV.

| Fase | Funcionalidad | Incluye | Queda fuera |
| --- | --- | --- | --- |
| PMV | Chat web texto-texto con RAG | Ingesta de PDF, DOCX y web; recuperación semántica; búsqueda web opcional; respuesta con citas; historial de la sesión; registro de interacciones para evaluación | Usuarios con cuenta, imágenes, voz, canales externos |
| Post-PMV 1 | Integración con Telegram | Bot que reutiliza la API del PMV | Pagos, grupos grandes |
| Post-PMV 2 | Aplicación | App instalable (PWA o nativa) sobre la misma API | Funcionamiento sin conexión |

## Arquitectura RAG propuesta

La arquitectura sigue los dos procesos del artículo: la ingesta prepara el conocimiento una vez y la generación lo consulta en cada pregunta, de modo que el corpus se actualiza sin reentrenar el modelo.

&#91;embedded content: arquitectura RAG · ingesta y generación\]

El modelo solo recibe la pregunta y los fragmentos recuperados, y se le instruye para citar su fuente o reconocer que no tiene la respuesta. Si el usuario activa la búsqueda web, Flask consulta además un SearXNG autoalojado, descarga y trocea las páginas más relevantes y las añade al contexto junto a los fragmentos del corpus; la respuesta distingue qué procede de la web (con su URL) y qué del corpus, y tarda más por la búsqueda y descarga de páginas. Telegram y la app se conectarán más adelante a la misma API Flask, sin duplicar lógica.

## Stack tecnológico y alternativas

Se propone un stack 100 % de pesos abiertos con Qwen3.8 como generador y modelos Qwen3 de embeddings y reranking, servido en local para que los datos de los estudiantes no salgan de la infraestructura de la UGR. La elección definitiva depende del hardware disponible, que es la primera decisión pendiente.

| Componente | Propuesta para el PMV | Alternativas | Motivo |
| --- | --- | --- | --- |
| Modelo generador | Qwen3.6-35B-A3B ([Qwen](https://github.com/QwenLM/Qwen3.8)) o Gemma 4 26B A4B ([Google](https://ai.google.dev/gemma/docs/core/model_card_4?authuser=5)), ambos MoE cuantizados a 4 bits; se elige uno en la evaluación | Qwen: Qwen3.8-27B, Qwen3.5-9B. Google: Gemma 4 31B. BSC (ALIA): Salamandra 7B, ALIA-40B | Licencia Apache 2.0 y caben en la R9700 de 32 GB; los MoE responden unas tres veces más rápido que los densos. Detalle en «Comparativa de modelos» |
| Embeddings | [Qwen3-Embedding-0.6B](https://qwenlm.github.io/blog/qwen3-embedding) | Qwen3-Embedding-4B; BAAI bge-m3 | Multilingüe (español e inglés), Apache 2.0, ligero |
| Reranker | Qwen3-Reranker-0.6B, a partir del sprint de calidad | bge-reranker-v2-m3 | Mejora la precisión de los fragmentos recuperados sin cambiar el generador |
| Búsqueda web | SearXNG autoalojado en Docker, activable por el usuario | API comercial de búsqueda (p. ej. Brave Search API) | Metabuscador de código abierto en el propio servidor, sin cuenta ni dependencia de un proveedor; las consultas sí salen hacia los buscadores |
| Base vectorial | Qdrant en Docker | ChromaDB (más simple); PostgreSQL con pgvector | Filtros por metadatos (fuente, tipo de documento) y servicio independiente reutilizable por Telegram y la app |
| Orquestación RAG | LlamaIndex | LLMWare; LangChain; código propio | Conectores de ingesta maduros y soporte para Qdrant, Qwen y modelos servidos por API compatible con OpenAI |
| Servidor del modelo | Ollama en desarrollo; vLLM en producción | llama.cpp server | Ambos exponen una API compatible con OpenAI, así el modelo se cambia sin tocar el back-end |
| Back-end | Python + Flask + Gunicorn | — | Fijado en el artículo |
| Front-end | HTML, CSS y JavaScript | — | Fijado en el artículo |
| Registro y evaluación | PostgreSQL (o SQLite en desarrollo) | — | Guarda preguntas, fragmentos recuperados y valoraciones para la evaluación |

## Servidor local para el PMV

| Componente | Modelo | Precio | Origen |
| --- | --- | --- | --- |
| GPU | AMD Radeon AI PRO R9700 32 GB | 2.700 € | PcComponentes |
| CPU | AMD Ryzen 7 9700X (8 núcleos) o similar | 400–500 € | PcComponentes |
| Placa base | AM5 (B850) con PCIe 5.0 x16 y 4 ranuras de RAM | 200 € | PcComponentes |
| RAM | 32 GB DDR5 (2×16 GB), ampliable a 64 GB | 560–600 € | PcComponentes |
| Almacenamiento | Kioxia Exceria Plus G3 2 TB M.2 NVMe PCIe 4.0 | 250–400 € | PcComponentes |
| Fuente | 1.000 W, 80 Plus Gold | 180 € | PcComponentes |
| Caja | Forgeon Airflow Mithril ARGB Mesh ATX | 100–150 € | PcComponentes |
| Refrigeración | Tempest Liquid Cooler Darken 360 mm | 55 € | PcComponentes |
| **Total** |  | **4.450–4.800 €** |  |

## Comparativa de modelos

| Modelo | Tipo | Generación, 1 usuario | Lectura del contexto | Preguntas a la vez (estimación) | Encaje para el RAG |
| --- | --- | --- | --- | --- | --- |
| **Qwen3.6-35B-A3B** | MoE, \~3B activos | \~77 tokens/s | \~2.400 tokens/s | 8–10 | Finalista: rápido y con contexto largo |
| **Gemma 4 26B A4B** | MoE, 3,8B activos | \~74 tokens/s | \~2.700 tokens/s | 8–10 | Finalista: rápido, multilingüe, 256K de contexto |
| Qwen3.8-27B | Denso | \~25 tokens/s | \~900–950 tokens/s | 3–4 | Más reciente, pero lento en esta tarjeta |
| Gemma 4 31B | Denso | \~22 tokens/s | Sin datos | 3–4 | Buena calidad, igual de lento que el 27B |
| gpt-oss-20b (OpenAI) | MoE | \~60 tokens/s | Sin datos | 8 o más | Rápido; español por comprobar |
| Qwen3.5-9B | Denso | 28–50 tokens/s (estimación) | Sin datos | 8 o más | Ligero, probablemente menos capaz |
| Salamandra 7B (BSC, ALIA) | Denso | Sin datos | Sin datos | Sin datos | Mucho español en el entrenamiento; contexto de 8K |
| ALIA-40B (BSC) | Denso | Sin datos | Sin datos | 1–2 | Cabe muy justo; poco margen para varios usuarios |

Supuestos: prompts RAG de unos 3.500 tokens y respuestas de unos 400 tokens. Con un modelo MoE, la primera palabra tarda en torno a 1,5 s y la respuesta completa unos 7 s, frente a 3–4 s y unos 20 s con Qwen3.8-27B. Eso equivale a unos 40–60 usuarios activos, frente a 15–20; si una clase de 25–30 estudiantes pregunta a la vez, la última respuesta llegaría en torno a un minuto. Las cifras de preguntas a la vez y usuarios son estimaciones propias.

Fuentes de rendimiento: [pruebas de llama.cpp en R9700](https://github.com/truelies444/amd-radeon-ai-pro-r9700-llama-cpp-rocm-benchmarks) (Qwen3.6 27B, Qwen3.6-35B-A3B, Gemma 4 31B y 26B A4B, cuantización Q5\_K\_M); [ASRock](https://asrock.com/blog/blog-details.asp?id=6) (gpt-oss-20b con vLLM); [Puget Systems](https://www.pugetsystems.com/labs/articles/amd-radeon-ai-pro-r9700-dual-gpu-ai-inference-performance/) (modelos de 8B). Licencias y características: [ficha de Gemma 4](https://ai.google.dev/gemma/docs/core/model_card_4?authuser=5), [repositorio de Qwen](https://github.com/QwenLM/Qwen3.8), [caso de estudio de ALIA](https://interoperable-europe.ec.europa.eu/node/734547).

Recomendación:

1. Comparar los dos finalistas en el sprint de evaluación con el mismo conjunto de preguntas: fidelidad a las fuentes, calidad de las citas, español natural y respuesta ante preguntas fuera del corpus.
2. Usar cuantización de 4 bits (Q4\_K\_M) para dejar memoria libre para varias conversaciones; con 5 bits quedan solo unos 6–7 GB.
3. Incluir Salamandra 7B como referencia opcional por su valor institucional como modelo público español.
4. Reevaluar si Qwen publica un modelo MoE pequeño de la generación 3.8.

Para ganar capacidad sin cambiar de equipo: desactivar el modo de razonamiento de Qwen o Gemma en el chat, limitar el contexto RAG a unos 2.000 tokens y las respuestas a 300–400 tokens, y activar MTP si el motor lo soporta. El siguiente salto es una segunda R9700.

Limitaciones: las cifras de rendimiento proceden de pruebas de terceros con configuraciones concretas y variarán con otro motor o cuantización; no hay comparativas independientes de estos modelos en español para RAG; los modelos pequeños razonan peor y pueden seguir peor la instrucción de citar, por lo que la evaluación de fidelidad es clave; la plataforma no usa memoria ECC, aceptable para el PMV pero no para producción; los precios deben confirmarse con presupuestos.

## Planificación temporal

&#91;embedded content: cronograma · PMV y fases posteriores\]

| Fase | Semanas | Entregables |
| --- | --- | --- |
| Preparación y corpus | S1–S2 | Casos de uso y requisitos cerrados; inventario del corpus con permisos de uso; repositorio, entorno Docker y servidor del modelo funcionando; primeras 30 preguntas de prueba |
| Pipeline de ingesta | S3–S5 | Ingesta reproducible de PDF, DOCX y web; corpus indexado en Qdrant con metadatos; primera medida de recuperación |
| Generación y API Flask | S6–S8 | Endpoint de chat con recuperación, prompt con citas, respuesta en streaming e historial de sesión; registro de interacciones |
| Interfaz web | S7–S9 | Chat accesible y adaptable a móvil con la identidad visual de la Cátedra, fuentes visibles y botón de valoración |
| Búsqueda web | S8–S9 | SearXNG desplegado; descarga y troceado de páginas; mezcla con los fragmentos del corpus; citas que distinguen web y corpus; interruptor en la interfaz |
| Evaluación y ajuste | S9–S11 | Conjunto de prueba completo; usuario simulado; reranker; ajuste de fragmentación y prompt hasta cumplir los umbrales |
| Piloto | S12 | Despliegue en servidor, piloto con estudiantes, informe de resultados y cierre del PMV |
| Telegram | 3 semanas | Bot conectado a la API existente, con las mismas citas y registro |
| App | 12 semanas (incluye la semana de Semana Santa) | PWA (recomendada para empezar) o app nativa sobre la misma API |

## Plan de evaluación

El PMV se da por alcanzado cuando supera los criterios de aceptación en la evaluación automática y completa un piloto con usuarios reales. Los umbrales de la tabla son una propuesta inicial que el equipo debe validar.

| Evaluación | Cómo | Métrica | Umbral propuesto |
| --- | --- | --- | --- |
| Recuperación | Conjunto de prueba de unas 100 preguntas con su documento de referencia, elaborado por el equipo | Documento correcto entre los 5 primeros fragmentos | ≥ 80 % |
| Fidelidad de la respuesta | Evaluación automática tipo RAGAS o un LLM como juez, con revisión manual de una muestra | Respuestas sustentadas en los fragmentos recuperados | ≥ 85 % |
| Citas | Revisión manual de una muestra | Respuestas con cita a la fuente correcta | ≥ 90 % |
| Fuera de dominio | Preguntas sin respuesta en el corpus | El sistema reconoce que no lo sabe en lugar de inventar | ≥ 90 % |
| Búsqueda web | Muestra de preguntas de actualidad, revisada manualmente | Respuestas cuya URL citada contiene de verdad la información | ≥ 85 % |
| Diálogo | Usuario simulado, siguiendo la metodología de Rodríguez-Sánchez et al. (2025) citada en el artículo | Coherencia en conversaciones de varios turnos | A definir tras la primera ronda |
| Rendimiento | Pruebas de carga en el servidor de despliegue | Latencia hasta el primer token y respuesta completa | A definir según hardware |
| Experiencia de usuario | Piloto con estudiantes del Máster en Educación Digital y Emprendimiento | Naturalidad, coherencia y satisfacción (cuestionario) | Media ≥ 4 sobre 5 |

El piloto con estudiantes requiere consentimiento informado y revisar si procede informe del comité de ética de la UGR antes de recoger datos.

## Riesgos y mitigaciones

El riesgo que más puede retrasar el PMV es no disponer a tiempo de una GPU adecuada; el resto se controla con decisiones de diseño tempranas.

| Riesgo | Impacto | Mitigación |
| --- | --- | --- |
| Sin GPU de unos 24 GB en las semanas 1-2 | Alto: bloquea pruebas con el modelo final | Desarrollar con un Qwen más pequeño tras la misma API; gestionar ya con el servicio de informática de la UGR o con un proveedor de cómputo |
| Corpus insuficiente o con derechos de uso dudosos | Alto: el RAG solo es tan bueno como sus documentos | Inventario y revisión de licencias en el sprint 1; priorizar documentación propia del Máster y fuentes en acceso abierto |
| Alucinaciones pese al RAG | Medio | Prompt que obliga a citar y a reconocer cuando no hay respuesta; reranker; evaluación de fidelidad continua |
| Datos personales en las conversaciones | Medio | Registro seudonimizado, aviso de privacidad, periodo de conservación definido y revisión con el delegado de protección de datos de la UGR |
| Calidad baja en español por la cuantización | Medio | Comparar 4 y 8 bits con el conjunto de prueba en el sprint de calidad |
| Dedicación del equipo menor de la prevista | Medio | Mantener el alcance del PMV cerrado; las mejoras pasan a fases posteriores |
| Consultas enviadas a buscadores externos y fuentes web poco fiables | Medio | SearXNG autoalojado; no reenviar datos personales de la conversación en la consulta; lista de dominios preferentes; separar en la respuesta lo que viene de la web y del corpus |
