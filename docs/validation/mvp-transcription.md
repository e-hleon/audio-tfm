# Validación del MVP — 2026-09-05

## Resultado

**Flujo real completado:** WAV → POST multipart a FastAPI → faster-whisper en
CUDA → JSON con texto. Repetido tras reconstrucción sin caché y en un proyecto
Compose independiente con un volumen de modelos recién creado.

## Entorno y configuración efectivos

- Docker Engine 28.3.2, Compose v2.38.2, Docker Desktop sobre WSL2.
- NVIDIA GeForce RTX 3050 Laptop GPU, 4096 MiB, driver 555.99.
- Imagen `nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04`.
- Digest base observado:
  `sha256:fa44193567d1908f7ca1f3abf8623ce9c63bc8cba7bcfdb32702eb04d326f7a8`.
- Python 3.10, faster-whisper 1.2.0, CTranslate2 4.6.0,
  Hugging Face Hub 0.34.4, PyAV 17.1.0.
- Modelo `base` multilingüe; dispositivo efectivo `cuda`; cálculo efectivo
  `int8_float16`; una instancia y un proceso Uvicorn.
- Revisión descargada de `Systran/faster-whisper-base`:
  `ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66`.
- Puerto 8001: el 8000 estaba ocupado por una instalación anterior, conservada.

La consulta de `/proc/1/maps` después de inferir confirmó `libcuda`, cuBLAS
12.3.4.1 y bibliotecas cuDNN 9 cargadas en el servidor (incluida la biblioteca
9.1.0 empaquetada por CTranslate2). La prueba no se limita a `nvidia-smi`: el
modelo efectivo comunica CUDA y la petición consume todos los segmentos ASR.

## Prueba real

Muestra pública JFK de
[whisper.cpp](https://github.com/ggml-org/whisper.cpp/blob/master/samples/jfk.wav),
11 segundos. Descargada únicamente en `tmp/`, ignorado por Git.

SHA-256:
`59dfb9a4acb36fe2a2affc14bacbee2920ff435cb13cc314a08c13f66ba7860e`.

```bash
API_URL=http://127.0.0.1:8001 python3 scripts/smoke_test.py tmp/jfk.wav
curl --fail-with-body --max-time 180 \
  -F 'file=@tmp/jfk.wav' http://127.0.0.1:8001/transcriptions
```

Respuesta obtenida, HTTP 200:

```json
{
  "text": "And so my fellow Americans, ask not what your country can do for you, ask what you can do for your country.",
  "language": "en",
  "model": "base",
  "device": "cuda",
  "compute_type": "int8_float16"
}
```

## Comprobaciones

| Comprobación | Resultado |
|---|---|
| Construcción inicial y descarga de paquetes | Correctas tras fijar Hub compatible |
| Descarga del modelo y arranque | `Application startup complete`, `/health` 200 |
| Transcripción HTTP y texto reconocible | Correctos con muestra JFK |
| CUDA real | Modelo efectivo CUDA y bibliotecas GPU cargadas durante inferencia |
| Archivo inválido y vacío | HTTP 400 en servicio real |
| Temporales del servidor | Observados durante subida grande; ninguno pendiente al terminar |
| Tests automatizados | 10 passed, 1 warning, 0.62 s |
| Consistencia de paquetes | `pip check`: No broken requirements found |
| Reconstrucción `docker compose build --no-cache` | Correcta; nueva instancia vuelve a transcribir |
| Arranque independiente con volumen nuevo | Proyecto `audio-tfm-clean`, puerto 8002: descarga y prueba HTTP correctas |
| Instrucciones README | Construcción, arranque, pytest, descarga de audio, script HTTP y curl ejecutados |

La advertencia de pytest procede de un alias obsoleto de AnyIO utilizado por
Starlette TestClient; no es un fallo de prueba.

Para comprobar temporales reales se generó en memoria un WAV de 44 segundos
repitiendo la muestra cuatro veces: 1 408 044 bytes, suficiente para que el parser
multipart deje de almacenarlo solo en memoria. Se observó `/proc/1/fd` durante la
petición: había un descriptor de `/tmp` mientras transcribía y ninguno después.
Se repitió con 1,8 MB de contenido inválido: HTTP 400 y ningún descriptor temporal
pendiente. No se conserva ese audio ni se incluyen muestras en Git.

Los tests cubren: modelo cargado una vez, respuesta con texto, cierre de archivos
en éxito y errores, archivo ausente/vacío/grande, duración excesiva, decodificación
inválida real, consumo de segmentos y rechazo de inferencias simultáneas mientras
`/health` continúa disponible.

## Problemas encontrados y resueltos

1. El primer intento quedó bloqueado por DNS que resolvía a `10.0.0.1`.
   El usuario restableció la red antes de esta validación.
2. Docker Desktop estaba detenido tras ese cambio. Se inició y se recuperó la
   integración WSL sin reinstalar Docker.
3. El puerto 8000 estaba ocupado. Se añadió `API_PORT`, conservando 8000 por
   defecto, y se validó en 8001 sin detener el servicio anterior.
4. faster-whisper 1.2.0 importa `requests`, pero la resolución a Hub 1.x ya no lo
   instalaba. Se fijó Hub 0.34.4, cuya API y dependencias son compatibles;
   se reconstruyó y se repitieron las pruebas.

## Límites de la evidencia

Esto demuestra funcionamiento, no precisión general. No se ha evaluado WER en
español ni comparado `base` con `small`, ni medido el pico de VRAM con un perfilador.
Los pesos y las dependencias transitivas no están bloqueados completamente;
las versiones y revisión anteriores describen esta ejecución concreta.
Los límites de tamaño y duración se aplican después de recepción y decodificación,
respectivamente: el servicio es para pruebas locales con entradas de confianza.
