# Validación Android manual

Validado localmente: `testDebugUnitTest` (estados, Retry, borrado temporal, URL y
MockWebServer multipart), `lintDebug`, `assembleDebug` y
`compileDebugAndroidTestKotlin`, con SDK 35 y JDK 17 temporales. CI ejecuta los tres
primeros comandos con JDK 17.

El smoke instrumentado Compose fue compilado, pero no ejecutado: no hay binario
`emulator`, AVD ni `/dev/kvm` disponibles en este entorno. Por tanto siguen pendientes
el runtime instrumentado, el E2E Emulator → backend real y el único smoke final con
Pixel (micrófono, permiso y Wi-Fi reales).

El emulador y la prueba física son distintos: FakeAudioRecorder valida estado, UI y
HTTP reproducibles, pero no el micrófono o MediaRecorder sobre hardware. Smoke final en
Pixel: iniciar backend con `API_BIND_HOST=0.0.0.0` en una LAN confiable, indicar
`http://IP_PC:8000`, conceder micrófono, grabar 5–10 s, enviar y comprobar el resultado
y borrado temporal. No se expone el backend a Internet.
