# Validación Android manual

Automatizado previsto: tests JVM para estados, UTC, borrado temporal y Retry; y
MockWebServer para multipart y parseo. CI ejecuta `testDebugUnitTest`, `lintDebug` y
`assembleDebug` con JDK 17.

Se añadió un smoke instrumentado Compose que comprueba los controles iniciales sin
usar hardware. En este entorno no hay AVD/KVM configurado, por lo que no se ejecutó;
la app y sus tests JVM sí se compilaron con SDK 35 temporal.

El emulador y la prueba física son distintos: FakeAudioRecorder valida estado, UI y
HTTP reproducibles, pero no el micrófono o MediaRecorder sobre hardware. Smoke final en
Pixel: iniciar backend con `API_BIND_HOST=0.0.0.0` en una LAN confiable, indicar
`http://IP_PC:8000`, conceder micrófono, grabar 5–10 s, enviar y comprobar el resultado
y borrado temporal. No se expone el backend a Internet.
