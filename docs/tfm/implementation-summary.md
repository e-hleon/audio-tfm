# Resumen de implementación

El TFM construye un diario personal local-first a partir de audio. Android captura
manual o explícitamente continua/inteligente; FastAPI recibe multipart, ejecuta
faster-whisper local en CUDA y envía solo texto al analizador OpenAI Structured
Outputs. PostgreSQL conserva interacciones y resúmenes diarios.

La captura manual usa `MediaRecorder` y AAC/M4A hasta 59 s. La continua usa
`AudioRecord`, PCM16 mono a 16 kHz, `ForegroundService`, chunks WAV con mínimo de
25 s y hard cap de 55 s, y una cola de archivos privada limitada. Una heurística
energética busca 800 ms de pausa desde el mínimo. Cada sesión y chunk llevan
metadatos persistentes e idempotencia. El modo inteligente añade buffer circular, VAD
energético baseline, pre-roll y una plantilla acústica local experimental; el
enrollment es explícito y no sale del dispositivo.

El cliente Android ofrece Captura, Histórico y Día. Histórico agrupa visualmente
chunks Continuous de la misma sesión y mantiene los legacy como entradas separadas.
Histórico y Día consultan la
fuente PostgreSQL mediante la API; solo un POST explícito genera el resumen y el
estado `missing/ready/stale` lo decide el backend. ViewModels y StateFlow modelan
estados de carga, vacío, error y éxito.

La calidad automática se cubre con tests backend, JVM Android y Compose compilable.
El análisis semántico continúa siendo por chunk; todavía no se reclama continuidad
semántica entre chunks ni una agregación de sesión sin doble conteo.
La evaluación ASR/LLM está aislada en PR #6. La validación física SMART en Pixel 8
confirmó el efecto de la calibración VAD en silencio, pero mostró que la similitud
acústica no discrimina hablantes; no se presentan FAR/FRR formales.
