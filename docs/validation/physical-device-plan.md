# Plan operativo de validación física

## Pre-flight del PC

```bash
hostname -I
docker compose config
docker compose up -d db api
docker compose ps
docker compose exec api alembic upgrade head
curl http://127.0.0.1:8000/health
docker compose exec api python -c 'import torch; print(torch.cuda.is_available())'
```

Usar la IP LAN del PC en Android, no `127.0.0.1`. Configurar `API_BIND_HOST=0.0.0.0` solo en la red local de prueba y abrir el firewall únicamente para esa red si es imprescindible; no desactivarlo. Comprobar la clave de forma booleana (`test -n "$OPENAI_API_KEY" && echo configured`) sin imprimirla.

## APK y manual

Descargar el artifact `audio-diary-debug-apk` de CI o localizar `android/app/build/outputs/apk/debug/app-debug.apk`; instalar con `adb install -r app-debug.apk` o manualmente. Conceder micrófono, grabar 5–10 s, detener, enviar y verificar Success, transcript, analysis, interaction id, fila en PostgreSQL y eliminación del M4A de cache.

## Continuous

Conceder notificaciones, iniciar explícitamente, comprobar notificación persistente, salir de Activity y verificar que continúa. Esperar al menos un chunk, detener, comprobar subida serial, histórico agrupado por `capture_session_id`, orden por `chunk_index`, ficheros pendientes y que ningún audio supera 55 s. Provocar una desconexión y verificar que el chunk queda pendiente; repetir el mismo chunk y comprobar que el backend devuelve la Interaction existente sin duplicarla. La pausa acústica reduce cortes durante actividad cuando existe una pausa próxima, pero no garantiza una frontera lingüística.

## Smart

Crear enrollment explícito y comprobar que solo se guarda la plantilla privada. Probar voz propia, silencio y otra voz; anotar aceptados/rechazados y contadores. Verificar que el audio descartado no queda en `cacheDir`, que Stop es visible y que la sesión termina.

### Resultado físico medido en Pixel 8

La primera prueba mostró falsos positivos del VAD incluso sin hablar; este hallazgo
físico no estaba cubierto por los tests sintéticos. La corrección evaluada
posteriormente usa calibración inicial de 2 s, `marginDb=12`, 10 frames
consecutivos de voz (200 ms) y cierre tras 800 ms de silencio.

| Sesión | Resultado observado |
|---|---|
| Silencio | 0 detecciones, 0 `POST /process` |
| Voz del usuario registrado | 3 frases detectadas, 3 envíos |
| Otra voz | Segmentos detectados y aceptados; 0 descartes |

En la sesión con voz propia, Logcat registró cuatro eventos `smart_similarity`
porque una frase se dividió en dos segmentos por una pausa suficientemente larga:

```text
score=1.0000 duration_ms=6200
score=1.0000 duration_ms=2340
score=1.0000 duration_ms=11120
score=1.0000 duration_ms=12000
```

En la sesión con otra voz se observaron:

```text
score=1.0000 duration_ms=5020
score=1.0000 duration_ms=2660
score=1.0000 duration_ms=6220
score=1.0000 duration_ms=7200
```

La mejora del VAD funcionó en esta prueba física: el silencio no produjo detecciones
ni POST. La segmentación de una frase por una pausa larga es una limitación de
segmentación observable, no necesariamente un fallo crítico. En cambio,
`AcousticSpeakerSimilarity` con `[mean, energy, zero-crossing-rate]` y similitud
coseno no discriminó entre hablantes en estas condiciones: todos los scores
observados saturaron en `1.0000`. Por ello se clasifica como baseline experimental
fallido/no discriminativo, no como biometría ni speaker verification.

Estos resultados no permiten calcular FAR/FRR formales: el conjunto físico es mínimo
y no constituye una evaluación estadística de hablantes. No debe afirmarse que SMART
proporciona privacidad basada en la identidad del hablante. Tampoco se cambia el
umbral `0.75`, porque los scores observados ya están saturados.

## Batería

Registrar nivel inicial/final y duración para idle, continuous y smart durante 15–30 min, con la misma red y brillo. Usar `adb shell dumpsys batterystats --reset`, ejecutar el modo, `adb shell dumpsys batterystats <package>` y, si está disponible, Perfetto. Los valores se incorporarán solo como MEDIDOS.

## Android 13/14/15

Android 13 introduce la solicitud de `POST_NOTIFICATIONS`; Android 14 exige declarar el tipo y permiso `FOREGROUND_SERVICE_MICROPHONE` para un FGS de micrófono y restringe el arranque desde background; Android 15 debe verificarse en el dispositivo/imagen concreta. El servicio actual se inicia desde la UI visible, llama a `startForeground` antes de AudioRecord y ofrece STOP.
