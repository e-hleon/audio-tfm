# Arquitectura de transcripción y análisis estructurado

Estado: transcripción HTTP real con CUDA y tests verificados.
Evidencia en [validación](validation/mvp-transcription.md).
El alcance completo del diario permanece en `scope.md`.

## Componentes

Docker Compose contiene un servicio `api` y PostgreSQL 16. La API contiene FastAPI,
Uvicorn, faster-whisper y la SDK oficial de OpenAI; OpenAI es un proveedor externo,
no un contenedor adicional. PostgreSQL conserva las interacciones y resúmenes cuando
la capa de aplicación los utiliza.
Uvicorn inicia un único proceso y el ciclo de vida de FastAPI carga una instancia
Whisper `base` en CUDA con `int8_float16`. Si no se puede cargar, falla el arranque.

```text
Archivo → POST /transcriptions (multipart/form-data)
               ↓
         FastAPI → faster-whisper / CTranslate2 → GPU NVIDIA
               ↓
         JSON: text, language, model, device, compute_type

Texto → POST /analyses (JSON) → Responses API OpenAI → AnalysisResult
Audio → POST /process → transcripción local → solo texto a OpenAI → JSON conjunto

`POST /process` persiste la interacción después de ASR y análisis. `GET
/interactions/{id}` recupera una interacción y `GET /interactions` ofrece un
histórico paginado con filtros temporales. `/transcriptions` y `/analyses` siguen
siendo operaciones sin persistencia.

GET /days/{YYYY-MM-DD} → interacciones locales ordenadas + agregación determinista
                       + estado missing|ready|stale
POST /days/{YYYY-MM-DD}/summary → datos derivados → Responses API → DailySummary
```

`app/main.py` gestiona HTTP, límites, exclusión mutua y cierre del archivo.
`app/transcription.py` decodifica, valida duración y consume los segmentos del
modelo hasta obtener el texto. El dispositivo y tipo de cálculo de la respuesta
se consultan al modelo efectivo.

`app/analysis.py` contiene el proveedor OpenAI y el protocolo mínimo `Analyzer`.
`app/schemas.py` contiene los contratos Pydantic: `AnalysisResult`, decisiones,
tareas y recordatorios. La API recibe o produce estos contratos y el proveedor usa
el JSON Schema generado con Structured Outputs estricto. Así, un proveedor local
posterior puede implementar `Analyzer` sin cambiar rutas HTTP.

La persistencia síncrona se organiza en `app/db.py`, `app/models.py` y
`app/repositories.py`, con SQLAlchemy 2.x y psycopg. Alembic es la única fuente de
migraciones; no se usa `create_all()` en el arranque. `AnalysisResult` se conserva
como JSONB para mantener el contrato completo sin introducir tablas hijas prematuras.
Los timestamps se almacenan con zona horaria y se normalizan a UTC; `APP_TIMEZONE`
define el intervalo local `[inicio, siguiente inicio)` que agrupa el diario, incluidos
los días de 23 o 25 horas por DST. `recorded_at` sitúa la interacción en el diario;
`created_at` indica cuándo se guardó.

El resumen diario no vuelve a extraer decisiones, tareas ni recordatorios: los agrega
en el orden cronológico de los `AnalysisResult` JSONB ya persistidos. El resumen
narrativo usa su contrato propio `DailySummaryResult` (`summary`, `topics`). Solo se
envía a OpenAI una proyección derivada: hora local, resumen, temas, decisiones, tareas
y recordatorios. No incluye audio, transcripción completa, filename, identificadores
técnicos ni metadatos ASR. Un SHA-256 de `interaction_id` y `updated_at` ordenados
determina si el resumen es `missing`, `ready` o `stale`. `GET` nunca llama al LLM; un
POST explícito genera o regenera. Antes de guardar se recalcula el fingerprint, de modo
que si cambia durante la llamada externa se rechaza el resultado desactualizado.

La petición espera al resultado. La inferencia se ejecuta en un hilo del mismo
proceso; no hay worker separado. Solo se permite una inferencia; las peticiones
simultáneas reciben 503. `GET /health` permanece disponible y comunica la carga
del modelo, sin sustituir una prueba real de transcripción.

El audio nunca abandona el contenedor para análisis. Solamente la cadena `text`
resultante de ASR se pasa a `OpenAIAnalyzer` para el análisis por interacción. El
resumen diario recibe solo datos derivados de esa estructura. Las llamadas usan
Responses API con `store=false` y limitan la salida a 1000 tokens para análisis y 500
para el resumen diario. Esto evita que la respuesta quede
disponible como recurso recuperable y acota coste/tamaño, pero no afirma ni garantiza
cero retención. Los Data Controls del proyecto o cuenta son una configuración
separada que puede permitir compartir inputs y outputs. No se escriben textos,
prompts ni respuestas LLM en logs. Después del JSON Schema se comprueba que cada
`evidence` aparece literalmente en el texto de entrada.

## Datos y límites

El parser multipart utiliza un archivo temporal que se cierra explícitamente en
un bloque `finally`, incluso cuando falla la transcripción. No se copia a un
archivo persistente ni se registra su contenido. `/tmp` es un tmpfs de 128 MiB.
Solo los pesos del modelo se conservan en un volumen Docker.

Se limitan los archivos a 10 MiB después del parsing y el audio a 60 segundos
después de decodificar. Esto acota el uso normal, pero no impide que una entrada
hostil consuma recursos durante recepción o decodificación. El MVP está destinado
a pruebas locales de confianza, con puerto publicado en la interfaz de loopback.

## Dependencias y despliegue

Dockerfile basado en CUDA 12.3.2 con cuDNN 9; CTranslate2 4.6.0 y faster-whisper
1.2.0 y Hugging Face Hub 0.34.4. Esta combinación se ha validado en una
RTX 3050 Laptop de 4 GB con driver 555.99. Hub se fija porque la versión 1.x
no instalaba `requests`, importado por faster-whisper 1.2.0. Las dependencias directas están fijadas; las transitivas
y paquetes apt no tienen un bloqueo completo, por lo que no se garantiza una
reconstrucción idéntica byte a byte.

El target `test` añade pytest y httpx sin aumentar las dependencias del servicio.
Los tests usan un transcriptor simulado para el contrato HTTP y el decodificador
real para entradas inválidas y duración. `scripts/smoke_test.py` prueba el servicio
por HTTP con un audio real y exige metadatos CUDA.

`openai` añade la SDK oficial. `OPENAI_API_KEY` y `OPENAI_MODEL` se pasan mediante
entorno; la clave no se persiste ni se expone. Sin clave, la API inicia y la
transcripción funciona; los endpoints LLM devuelven 503. Los errores de proveedor
se traducen sin exponer detalles: autenticación 502, límite 429, tiempo agotado
504, red 503 y salida inválida o incompleta 502.

## Diferencias frente a la propuesta anterior

No se implementan Android, workers separados ni Redis/RQ. Docker Compose define la
API y PostgreSQL, sin infraestructura adicional. El LLM externo
se incorpora como llamada de texto síncrona porque es el objetivo de este incremento.

El diario diario, la cronología básica y los resúmenes persistidos ya forman parte de
este incremento. Quedan fuera la captura Android, procesamiento asíncrono y funciones
de usuario final más amplias.
Una cola se reconsiderará cuando los
tiempos de espera o la recuperación de trabajos constituyan requisitos reales.
El puerto del host es configurable mediante `API_PORT` (8000 por defecto);
la validación usó 8001 para convivir con un servicio anterior.
La decisión se documenta en [ADR 001](decisions/001-synchronous-transcription-mvp.md).
La decisión de análisis está en [ADR 002](decisions/002-structured-llm-analysis.md).
La base de persistencia está documentada en [ADR 003](decisions/003-persistence-foundation.md).
El resumen diario está documentado en [ADR 004](decisions/004-daily-summary.md).
