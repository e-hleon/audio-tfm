# Audio TFM

MVP del diario personal: audio → transcripción local CUDA → análisis estructurado.
La base de persistencia incluye PostgreSQL para interacciones y resúmenes diarios.
`/process` persiste las interacciones, el histórico se consulta mediante `/interactions`
y el diario local mediante `/days/{YYYY-MM-DD}`.
El alcance general sigue en [docs/scope.md](docs/scope.md).

**Transcripción real por HTTP verificada en una RTX 3050 Laptop de 4 GB.**
Modelo `base`, `int8_float16`, ejecución CUDA y 57 tests automatizados correctos.
Véase la evidencia y sus límites en el [registro de validación](docs/validation/mvp-transcription.md).

## Requisitos

- Docker Engine/Desktop con Docker Compose v2 y acceso NVIDIA desde Docker/WSL.
- GPU NVIDIA; configuración inicial prevista para una RTX 3050 Laptop de 4 GB.
- Internet para descargar imagen, paquetes y modelo la primera vez.
- Un puerto local libre (8000 por defecto); `curl` y Python 3 para las pruebas desde el host.
- Android Studio reciente o JDK 17 para el proyecto [android/](android/). La app usa
  Kotlin 2.0.21, AGP 8.6.1, compile/target SDK 35 y minSdk 26.

No hace falta instalar Python ni CUDA en el host para ejecutar la API.
El contenedor usa CUDA 12.3.2 y cuDNN 9; las versiones directas de Python están
fijadas en `requirements.txt`. La combinación se ha probado con CTranslate2 4.6.0
y faster-whisper 1.2.0. Hub 0.34.4 mantiene la API y dependencia `requests` que
requiere esta versión de faster-whisper; Hub 1.x causó un fallo de importación.

## Arranque

Desde la raíz del repositorio, elegir un puerto libre. En el equipo de validación
se utilizó 8001 porque un servicio anterior ocupaba 8000:

```bash
export API_PORT=8001
export API_URL="http://127.0.0.1:${API_PORT}"
cp .env.example .env
# Editar .env localmente y establecer OPENAI_API_KEY si se usará análisis.
```

Compose usa 8000 si no se establece `API_PORT`. Conservar estas variables en la
misma terminal para los siguientes comandos. No detener otros servicios para
liberar el puerto; se puede elegir otro.

```bash
docker compose build --no-cache
docker compose up -d
docker compose logs -f api
```

Para probar desde un teléfono en una LAN de confianza, usar
`API_BIND_HOST=0.0.0.0` y la IP LAN del PC como URL en la app. Por defecto se mantiene
`127.0.0.1`; no existe autenticación, por lo que nunca se debe exponer ese puerto a
Internet.

PostgreSQL 16 se ejecuta como servicio Compose y conserva sus datos en el volumen
`postgres_data`. La primera migración se aplica explícitamente antes de usar la
persistencia:

```bash
docker compose exec api alembic upgrade head
```

`/process` guarda la transcripción y el análisis después de completar correctamente
ambos pasos. El audio y el filename siguen siendo temporales y no se almacenan.

El primer arranque descarga el modelo `base` multilingüe al volumen Docker
`models`. Esperar al mensaje `Application startup complete`. Salir de los logs
con Ctrl+C no detiene el servicio.

```bash
curl --fail "$API_URL/health"
curl --fail-with-body --max-time 180 \
  -F 'file=@/ruta/a/grabacion.wav' \
  "$API_URL/transcriptions"
```

Respuesta esperada (ejemplo ilustrativo, no una medición realizada):

```json
{"text":"Hoy he revisado el proyecto.","language":"es","model":"base","device":"cuda","compute_type":"int8_float16"}
```

También se puede subir un archivo desde `http://127.0.0.1:8001/docs`
(o el puerto elegido).
La respuesta espera a la transcripción completa. El modelo se carga una vez;
no se debe aumentar `--workers` ni usar recarga automática para estas pruebas.
`/health` indica que el modelo ha cargado, pero por sí solo no demuestra inferencia.

## Análisis estructurado externo

La transcripción se realiza localmente. Para analizar el contenido, solo se envía
**el texto de la transcripción** a OpenAI; el audio nunca se envía a ese proveedor.
Configurar la clave exclusivamente en `.env`, que está ignorado por Git:

```dotenv
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.4-mini
```

`gpt-5.4-mini` es la configuración validada y sigue siendo configurable mediante
`OPENAI_MODEL`. Cada llamada usa `store=false`, Structured Outputs con JSON Schema
estricto y un límite de 1000 tokens de salida: el esquema del MVP contiene campos
breves, y el límite acota coste y tamaño de respuesta. `store=false` evita crear una
respuesta recuperable mediante la API, pero no equivale a cero retención. Los Data
Controls del proyecto o la cuenta son una configuración distinta y pueden permitir
compartir entradas y salidas según la política elegida; revísalos antes de usar datos
personales.

La API inicia sin clave y `/transcriptions` sigue disponible. `/analyses` y
`/process` devuelven 503 hasta configurar la clave. La respuesta de `/health` indica
`analysis_configured` sin revelar la clave.

```bash
curl --fail-with-body "$API_URL/analyses" \
  -H 'Content-Type: application/json' \
  -d '{"text":"Decidimos publicar la propuesta. Ana la preparará. Recuérdame revisarla el lunes."}'

curl --fail-with-body --max-time 240 \
  -F 'file=@/ruta/a/grabacion.wav' \
  "$API_URL/process"
```

`POST /analyses` recibe `{ "text": "..." }` y `POST /process` devuelve la
transcripción, su análisis e `interaction_id` sin repetir la lógica ASR. El histórico
se consulta con `GET /interactions/{id}` o `GET /interactions`; admite `limit`,
`offset`, `from` y `to` como intervalos timezone-aware. El análisis contiene:

```json
{
  "summary": "...",
  "topics": ["..."],
  "decisions": [{"text": "...", "evidence": "..."}],
  "tasks": [{"text": "...", "assignee": null, "due_date": null, "evidence": "..."}],
  "reminders": [{"text": "...", "when": null, "evidence": "..."}]
}
```

Las listas vacías expresan que no hay evidencia suficiente. `evidence` debe ser un
fragmento breve que aparezca literalmente en el texto de entrada; si no aparece, la
respuesta del proveedor se considera inválida. Las fechas sin contexto se devuelven como `null`.
La API no registra texto, prompts ni respuestas de análisis: solo modelo, latencia y
tokens cuando OpenAI los proporciona. El coste externo depende de los tokens de la
transcripción, de la respuesta y del precio vigente del modelo.

## Diario diario

`recorded_at` determina el día de cada interacción. El instante se conserva en UTC,
pero el día se calcula con `APP_TIMEZONE` (por defecto `UTC`) como el intervalo
`[inicio local, siguiente inicio local)`, por lo que también respeta cambios DST.

```bash
curl --fail "$API_URL/days/2026-09-05"
curl --fail-with-body -X POST "$API_URL/days/2026-09-05/summary"
```

`GET /days/{fecha}` no llama a OpenAI. Devuelve las interacciones cronológicas y
las decisiones, tareas y recordatorios ya extraídos, además del estado del resumen:
`missing` cuando no existe, `ready` cuando corresponde a los datos actuales y
`stale` cuando se añadió o modificó una interacción después de generarlo o cuando
fue generado con otra `APP_TIMEZONE`.

`POST /days/{fecha}/summary` genera o regenera explícitamente un `DailySummaryResult`
con `summary` y `topics`. Para reducir datos enviados, OpenAI recibe solo hora local,
resumen, temas, decisiones, tareas y recordatorios de cada interacción; nunca audio,
transcripciones completas, filename, metadatos ASR ni identificadores técnicos. La
llamada mantiene `store=false`, Structured Outputs estricto y un máximo de 500 tokens
de salida, suficiente para ese contrato breve. Si el día cambia mientras OpenAI
responde, el resultado no se guarda y se devuelve 409 para reintentarlo.

## Pruebas

Tests automatizados de API, errores, cierre de temporales, concurrencia,
decodificación, duración y análisis; no llaman a OpenAI ni necesitan GPU:

```bash
docker build --target test -t audio-tfm-tests .
docker run --rm --entrypoint python3 audio-tfm-tests -m pytest -q
```

Para la integración, usar voz propia no sensible o la muestra pública de discurso
JFK empleada por whisper.cpp. Guardar las muestras en `tmp/`, ignorado por Git:

```bash
mkdir -p tmp
curl --fail --location \
  https://raw.githubusercontent.com/ggml-org/whisper.cpp/master/samples/jfk.wav \
  --output tmp/jfk.wav
python3 scripts/smoke_test.py tmp/jfk.wav
```

`API_URL` permite dirigir la prueba al puerto elegido (por defecto 8000).
La prueba exige texto no vacío y dispositivo CUDA, y verifica errores de archivo
vacío e inválido. Para JFK, revisar además que el texto reconoce el pasaje
«ask not what your country can do for you». El script imprime la transcripción:
no redirigir grabaciones privadas a archivos versionados.

Comprobar GPU y configuración efectiva:

```bash
docker compose exec api nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
docker compose logs api
```

Los metadatos `device` y `compute_type` proceden del modelo CTranslate2 cargado,
no de una constante en la respuesta. No hay alternativa automática a CPU.
Una respuesta con texto demuestra que se ha consumido el generador de segmentos
que ejecuta la inferencia. Para reproducir desde una imagen nueva:

```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

Repetir la prueba HTTP cuando termine el arranque. `--no-cache` reconstruye
las capas de aplicación; no elimina el volumen de pesos. Para comprobar una
descarga inicial independiente, usar otro proyecto Compose después de parar el
anterior: `docker compose -p audio-tfm-clean up -d --build`.

Detener con `docker compose down`; conserva los pesos para el siguiente arranque.

## Límites y privacidad

- Una inferencia simultánea; otra petición recibe HTTP 503 y puede reintentarse.
- Máximo 10 MiB por archivo y 60 segundos de audio decodificado. HTTP 413 si se
  superan; 400 para audio vacío o inválido; 422 si falta el campo `file`.
- Los límites se comprueban después del parsing multipart y la duración después
  de decodificar. No es un servicio endurecido contra cargas hostiles. Usar audios
  breves y fiables; el puerto se publica solo en `127.0.0.1`.
- Se admite lo que pueda decodificar PyAV; el formato de prueba prioritario es WAV.
- Los temporales de subida se cierran al acabar, incluso ante errores. `/tmp` del
  contenedor es memoria temporal limitada; no se guardan audios ni transcripciones.
- El modelo requiere descarga inicial. No se llama a proveedores externos para
  transcribir. El análisis LLM, cuando se configura, sí transmite texto a OpenAI.
- PostgreSQL guarda transcripciones y análisis JSONB de las interacciones, además de
  resúmenes diarios. El volumen `postgres_data` conserva esos datos al recrear el
  contenedor; no guarda audio ni filename.
- No hay recuperación de trabajos tras reinicios ni garantía de transcripción
  exacta. Se ha verificado el flujo con una muestra pública en inglés; todavía
  falta una evaluación sistemática de precisión en español, latencia y VRAM.

## Decisiones y conceptos para el TFM

FastAPI define el contrato HTTP; Uvicorn sirve las conexiones; `python-multipart`
interpreta la subida de archivos. faster-whisper aporta el ASR que Python estándar
no incluye; CTranslate2 ejecuta el modelo y PyAV decodifica el audio sin instalar
el ejecutable FFmpeg por separado. No se añade PyTorch ni una cola.

`base` e `int8_float16` son el punto de partida para dejar margen en 4 GB de VRAM:
la cuantización reduce la precisión numérica de parte del cálculo para ahorrar
memoria. Esta configuración ha transcrito la muestra real y su repetición de 44 segundos
sin agotar la GPU. No se ha comparado con `small`: esa evaluación queda pendiente.

La petición es síncrona porque el cliente espera al texto. Un hilo del mismo
proceso ejecuta el cálculo para mantener disponible `/health`; no es un worker
independiente ni un sistema de trabajos persistentes. Un bloqueo de exclusión
mutua impide dos inferencias a la vez.

En el diario, el fingerprint SHA-256 contiene únicamente `interaction_id` y
`updated_at`, ordenados de forma estable. Detecta altas o cambios sin volver a hashear
transcripciones o JSON completos. El resumen se escribe solo si ese fingerprint sigue
siendo igual después de la llamada externa; así no se presenta como vigente un resumen
hecho con datos antiguos. Esta comprobación reduce la carrera habitual, aunque queda
una ventana mínima entre la comprobación final y el commit; una lectura posterior
volverá a evaluar el fingerprint y marcará `stale` si los datos cambiaron.

Para defender el incremento: explicar inferencia frente a entrenamiento, RAM
frente a VRAM, descarga de pesos frente a envío de datos, y carga del modelo frente
a tiempo de transcripción. Evaluar WER con un texto de referencia y factor de
tiempo real (tiempo de procesamiento / duración del audio), registrando versiones,
modelo y configuración.

- [Arquitectura implementada](docs/architecture.md)
- [Decisión del incremento](docs/decisions/001-synchronous-transcription-mvp.md)
- [Decisión de análisis estructurado](docs/decisions/002-structured-llm-analysis.md)
- [Validación del análisis](docs/validation/structured-analysis.md)
- [Documentación oficial de faster-whisper](https://github.com/SYSTRAN/faster-whisper)

## Captura Android avanzada

La app también ofrece Histórico y Día, además de captura manual, continua e
inteligente. Manual conserva `MediaRecorder`/M4A. Continua usa `AudioRecord` PCM16
mono a 16 kHz, `ForegroundService`, notificación persistente, STOP explícito y
chunks WAV con mínimo de 25 s y hard cap de 55 s que se suben de uno en uno desde
una cola privada acotada. Continuous asigna una sesión, índice de chunk y clave
idempotente para evitar duplicados tras un retry.

Inteligente es experimental: usa frames de 20 ms, VAD energético adaptativo, un
pre-roll de aproximadamente un segundo y una plantilla acústica local registrada
explícitamente. Puede omitir voz o aceptar audio incorrectamente; no es seguridad
biométrica. El detalle técnico está en [arquitectura](docs/architecture.md),
[ADR 006](docs/decisions/006-continuous-android-capture.md) y
[ADR 007](docs/decisions/007-smart-selective-capture.md).
