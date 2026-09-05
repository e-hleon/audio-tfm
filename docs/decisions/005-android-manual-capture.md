# 005 — Captura manual Android

La primera aplicación móvil usa Kotlin, Jetpack Compose, ViewModel y StateFlow en una
única pantalla. Compose recompone la interfaz al cambiar el estado explícito
`Idle/Recording/Ready/Processing/Success/Error`; ViewModel mantiene la lógica fuera de
la Activity.

`MediaRecorder` produce AAC en MPEG-4 (`.m4a`) en `cacheDir`: basta para pulsar
grabar/detener y no exige permisos de almacenamiento. `AudioRecord` queda para captura
continua futura, que requerirá segmentación y un servicio en primer plano. La grabación
se cancela si la app deja el primer plano y se limita a 59 s por el límite actual del
backend. `recorded_at` se captura al comienzo en UTC.

Retrofit/OkHttp envía multipart a `/process`; kotlinx.serialization tipa la respuesta.
Android no contiene ninguna clave OpenAI. No hay retry automático porque una respuesta
perdida tras persistir podría duplicar la interacción sin idempotency key; el usuario
decide Retry y el audio temporal se conserva solo tras error. Debug permite HTTP para
LAN/emulador; release no habilita cleartext.
