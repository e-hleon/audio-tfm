# Inventario de pruebas

| Grupo | Qué valida | Qué no valida |
|---|---|---|
| Backend API | status codes, límites, contratos y errores | GPU real y red Android |
| Persistence | migraciones, CRUD, timezone, fingerprint | rendimiento a gran escala |
| LLM | schema, provider mapping y evidence | verdad factual o variabilidad del modelo |
| Evaluation | normalización, WER/CER, PRF, resume | que el dataset represente al usuario |
| Android manual | estados, retry, descarte, cache | micrófono físico |
| Android network | multipart, JSON, timeouts HTTP | backend completo conectado |
| Continuous/smart JVM | WAV, frames, cola, VAD, ring, similitud | lifecycle real y consumo |
| Compose | pantalla inicial instrumentada | permisos y audio real |
| Instrumented | integración en emulador | características acústicas del dispositivo |

Los tests se ejecutan con `python -m pytest -q` y `./gradlew testDebugUnitTest`; el workflow separado ejecuta `connectedDebugAndroidTest`. Las cifras de tests deben generarse con `pytest --collect-only -q` y el runner Gradle, no escribirse a mano.
