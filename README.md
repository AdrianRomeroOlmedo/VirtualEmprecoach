# Virtual EmpreCoach

Primer prototipo local de un asistente educativo de emprendimiento: web en español, Flask, RAG con recuperación semántica y Salamandra a través de Ollama. No usa base de datos: la ingesta crea un índice JSON local y el historial vive únicamente en la pestaña del navegador.

**No está listo para un piloto ni para producción.** El único documento incluido es un ejemplo ficticio, no un corpus docente validado. Las citas identifican fragmentos recuperados, pero no garantizan que la respuesta esté respaldada por ellos. Salamandra puede generar contenido inapropiado; su [ficha oficial](https://huggingface.co/BSC-LT/salamandra-7b-instruct) advierte de sus limitaciones. No se han evaluado los umbrales de calidad, seguridad ni accesibilidad del plan.

## Requisitos

- Python 3.10 o posterior.
- [Ollama](https://ollama.com/download) instalado y ejecutándose en el mismo equipo.
- Espacio y memoria para Salamandra 7B cuantizado (GGUF de aproximadamente 5 GB) y Qwen3-Embedding-0.6B (aproximadamente 639 MB), más el espacio de trabajo de Ollama.
- Conexión a Internet para instalar dependencias y descargar modelos. Las consultas y la ingesta se ejecutan localmente después de descargarlos.

## Puesta en marcha en Windows (PowerShell)

### Inicio automático

Haz doble clic en `Iniciar Virtual EmpreCoach.cmd`. Mantén abierta la ventana que aparece mientras uses la web. El lanzador instala Python 3.12 y Ollama mediante `winget` si no los encuentra, prepara las dependencias, descarga los modelos, indexa el corpus la primera vez y abre el navegador. Si Windows solicita permisos o aceptación, confírmalos. Necesitas conexión, `winget` y espacio libre para las descargas y las copias del modelo; el primer inicio puede tardar bastante. En ejecuciones posteriores reutiliza los modelos y el índice existente.

El lanzador usa exclusivamente Ollama local y los nombres predeterminados, aunque tengas configuradas las variables descritas abajo. Si no puede instalar Python u Ollama, muestra el error: instálalos manualmente y vuelve a ejecutar el lanzador. Para parar la web cierra la ventana; Ollama puede seguir ejecutándose en segundo plano. No cierres Ollama si lo usan otras aplicaciones.

### Inicio manual

Desde la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Inicia Ollama. Descarga el archivo `salamandra-7b-instruct-Q4_K_M.gguf` desde la [conversión GGUF de Hugging Face](https://huggingface.co/hdnh2006/BSC-LT-salamandra-7b-instruct-gguf/blob/main/salamandra-7b-instruct-Q4_K_M.gguf) y colócalo junto a `Modelfile`. Esa conversión es de un tercero; el modelo original es [BSC-LT/salamandra-7b-instruct](https://huggingface.co/BSC-LT/salamandra-7b-instruct). Revisa su procedencia y licencia antes de usarlo. Después:

```powershell
ollama create salamandra-emprecoach -f Modelfile
ollama pull qwen3-embedding:0.6b
python ingest.py
python app.py
```

Abre <http://127.0.0.1:5000>. La primera carga de los modelos puede tardar varios minutos. Si PowerShell bloquea la activación del entorno, ejecuta directamente `.\.venv\Scripts\python.exe` en vez de activarlo.

## Corpus e ingesta

Coloca en `corpus` los documentos autorizados en formato `.txt` o `.md` (UTF-8), `.pdf` o `.docx`. Se recorren todas sus subcarpetas recursivamente y las citas conservan la ruta relativa del archivo. Otros formatos, incluidos los archivos `.NO_PDF.html` generados por el script de descarga cuando un enlace no devuelve un PDF, no se indexan. El PDF debe contener texto extraíble, pues no se realiza OCR. DOCX solo extrae párrafos, no tablas. La cita muestra el nombre del archivo, la página para PDF y el fragmento recuperado. Las fuentes no se sirven ni se convierten en enlaces.

Las dependencias incluyen soporte para fuentes CFF y PDF cifrados con AES que pueden abrirse sin contraseña. Los PDF que requieran una contraseña de apertura deben sustituirse por una copia autorizada accesible; el prototipo no solicita contraseñas.

Retira el ejemplo ficticio cuando añadas el corpus real. El lanzador reutiliza `data\index.json` si ya existe y no detecta automáticamente cambios en los documentos. Ejecuta `python ingest.py` tras añadir, modificar o retirar documentos para reconstruir el índice. Si falla la ingesta, se conserva el índice anterior y debe corregirse el error y repetirse el proceso; **no se reflejan los cambios del corpus hasta que termine correctamente**. El índice contiene texto y embeddings del corpus: protégelo igual que los documentos originales.

## Uso y límites

Escribe una pregunta y despliega «Consultar fuentes seleccionadas» para ver los fragmentos que el modelo indica haber usado. «Nueva conversación» borra el historial de la pestaña. La API recibe hasta seis mensajes anteriores, no conserva conversaciones intencionadamente y no realiza búsquedas externas. Evita introducir datos personales o confidenciales: el navegador y el servidor procesan el contenido y pueden existir registros ajenos a la aplicación. La respuesta no sustituye al asesoramiento profesional.

El modelo selecciona fuentes en una respuesta estructurada; el sistema comprueba que sus identificadores existen, pero no que respalden cada afirmación. No se garantiza una cita por afirmación. Si el modelo no proporciona fuentes válidas, se muestra un error en lugar de afirmar que no hay información. También se le pide ignorar instrucciones en documentos, sin garantizar protección frente a inyección de instrucciones. Revisa las fuentes manualmente. El prototipo se ejecuta solo en `127.0.0.1`, sin autenticación, HTTPS ni control de acceso; no lo expongas a la red.

No implementa búsqueda web, streaming, valoraciones, registros para evaluación, aceptación de privacidad, evaluación automática, OCR ni gestión web del corpus. Son funcionalidades y decisiones pendientes del plan, no resultados ya alcanzados.

## Configuración y API

Opcionalmente se pueden establecer `OLLAMA_URL` (por defecto `http://127.0.0.1:11434`), `CHAT_MODEL` (`salamandra-emprecoach`) y `EMBED_MODEL` (`qwen3-embedding:0.6b`). Un Ollama remoto recibirá preguntas y documentos: úsalo solo si está autorizado. Al cambiar el modelo de embeddings es obligatorio volver a ejecutar la ingesta.

`POST /api/chat` recibe JSON, por ejemplo:

```json
{"question":"¿Cómo valido una idea?","history":[]}
```

Devuelve `{"answer":"...","sources":[{"id":1,"name":"ejemplo.txt","page":null,"excerpt":"..."}],"notice":"Fuentes seleccionadas automáticamente por el modelo; comprueba que respaldan la respuesta."}` o un objeto `{"error":"..."}` con código HTTP distinto de 200. Si el modelo no encuentra información, devuelve la respuesta de abstención y una lista de fuentes vacía. El historial es una lista de objetos `{"role":"user"|"assistant","content":"..."}`. La API valida tamaños y comunica los errores de índice y Ollama.

Para ejecutar las pruebas:

```powershell
python -m unittest discover -s tests -v
```

Las pruebas simulan Ollama; no sustituyen una comprobación con los modelos reales ni la evaluación con el corpus definitivo.
