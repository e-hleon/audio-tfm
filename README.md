# Audio TFM

Primer incremento del diario personal: archivo de audio → FastAPI →
faster-whisper local en CUDA → JSON. No incluye análisis, persistencia ni cliente
Android. El alcance general sigue en [docs/scope.md](docs/scope.md).

**Transcripción real por HTTP verificada en una RTX 3050 Laptop de 4 GB.**
Modelo `base`, `int8_float16`, ejecución CUDA y 10 tests automatizados correctos.
Véase la evidencia y sus límites en el [registro de validación](docs/validation/mvp-transcription.md).

## Requisitos

- Docker Engine/Desktop con Docker Compose v2 y acceso NVIDIA desde Docker/WSL.
- GPU NVIDIA; configuración inicial prevista para una RTX 3050 Laptop de 4 GB.
- Internet para descargar imagen, paquetes y modelo la primera vez.
- Un puerto local libre (8000 por defecto); `curl` y Python 3 para las pruebas desde el host.

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
```

Compose usa 8000 si no se establece `API_PORT`. Conservar estas variables en la
misma terminal para los siguientes comandos. No detener otros servicios para
liberar el puerto; se puede elegir otro.

```bash
docker compose build --no-cache
docker compose up -d
docker compose logs -f api
```

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

## Pruebas

Tests automatizados de API, errores, cierre de temporales, concurrencia,
decodificación y duración; no descargan modelo ni necesitan GPU:

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
- El modelo requiere descarga inicial. El procesamiento del contenido es local;
  no se llama a proveedores externos para transcribir.
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

Para defender el incremento: explicar inferencia frente a entrenamiento, RAM
frente a VRAM, descarga de pesos frente a envío de datos, y carga del modelo frente
a tiempo de transcripción. Evaluar WER con un texto de referencia y factor de
tiempo real (tiempo de procesamiento / duración del audio), registrando versiones,
modelo y configuración.

- [Arquitectura implementada](docs/architecture.md)
- [Decisión del incremento](docs/decisions/001-synchronous-transcription-mvp.md)
- [Documentación oficial de faster-whisper](https://github.com/SYSTRAN/faster-whisper)
