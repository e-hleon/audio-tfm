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

Conceder notificaciones, iniciar explícitamente, comprobar notificación persistente, salir de Activity y verificar que continúa. Esperar al menos un chunk, detener, comprobar subida serial, histórico/día, ficheros pendientes y que ningún audio supera 60 s. Provocar una desconexión y verificar que el chunk queda pendiente; no hacer retry automático del POST ambiguo.

## Smart

Crear enrollment explícito y comprobar que solo se guarda la plantilla privada. Probar voz propia, silencio y otra voz; anotar aceptados/rechazados y contadores. Verificar que el audio descartado no queda en `cacheDir`, que Stop es visible y que la sesión termina.

## Batería

Registrar nivel inicial/final y duración para idle, continuous y smart durante 15–30 min, con la misma red y brillo. Usar `adb shell dumpsys batterystats --reset`, ejecutar el modo, `adb shell dumpsys batterystats <package>` y, si está disponible, Perfetto. Los valores se incorporarán solo como MEDIDOS.

## Android 13/14/15

Android 13 introduce la solicitud de `POST_NOTIFICATIONS`; Android 14 exige declarar el tipo y permiso `FOREGROUND_SERVICE_MICROPHONE` para un FGS de micrófono y restringe el arranque desde background; Android 15 debe verificarse en el dispositivo/imagen concreta. El servicio actual se inicia desde la UI visible, llama a `startForeground` antes de AudioRecord y ofrece STOP.
