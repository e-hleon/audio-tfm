# ADR 006: captura continua explícita y segmentada

La captura manual conserva `MediaRecorder`/MPEG-4/AAC. Las sesiones continuas e
inteligentes usan `AudioRecord` PCM mono a 16 kHz. Continuous usa chunks WAV con
mínimo de 25 s y hard cap de 55 s, busca una pausa acústica y sube secuencialmente
desde un `ForegroundService` visible. La cola son archivos privados de `cacheDir`,
limitada a 20 segmentos; el fallo conserva el archivo. Cada sesión y chunk tienen
metadatos y `capture_chunk_id` evita duplicados tras un retry.

`AudioRecord` permite frames y pre-roll, mientras que el formato comprimido sigue
siendo apropiado para la nota manual. El hard cap queda claramente bajo el límite backend
de 60 s. Android exige un servicio foreground para mantener una captura iniciada
por el usuario cuando la Activity deja de estar visible.
