# ADR 006: captura continua explícita y segmentada

La captura manual conserva `MediaRecorder`/MPEG-4/AAC. Las sesiones continuas e
inteligentes usan `AudioRecord` PCM mono a 16 kHz, se dividen en chunks WAV de 30 s y
se suben secuencialmente desde un `ForegroundService` visible. La cola son archivos
privados de `cacheDir`, limitada a 20 segmentos; el fallo conserva el archivo y el
reintento es manual al iniciar una nueva sesión. No se añade idempotencia ni cola de
backend en este hito.

`AudioRecord` permite frames y pre-roll, mientras que el formato comprimido sigue
siendo apropiado para la nota manual. 30 s queda claramente bajo el límite backend
de 60 s. Android exige un servicio foreground para mantener una captura iniciada
por el usuario cuando la Activity deja de estar visible.
