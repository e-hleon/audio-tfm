# Resumen de implementación

El TFM construye un diario personal local-first a partir de audio. Android captura
manual o explícitamente continua/inteligente; FastAPI recibe multipart, ejecuta
faster-whisper local en CUDA y envía solo texto al analizador OpenAI Structured
Outputs. PostgreSQL conserva interacciones y resúmenes diarios.

La captura manual usa `MediaRecorder` y AAC/M4A hasta 59 s. La continua usa
`AudioRecord`, PCM16 mono a 16 kHz, `ForegroundService`, chunks WAV de 30 s y una
cola de archivos privada limitada. El modo inteligente añade buffer circular, VAD
energético baseline, pre-roll y una plantilla acústica local experimental; el
enrollment es explícito y no sale del dispositivo.

El cliente Android ofrece Captura, Histórico y Día. Histórico y Día consultan la
fuente PostgreSQL mediante la API; solo un POST explícito genera el resumen y el
estado `missing/ready/stale` lo decide el backend. ViewModels y StateFlow modelan
estados de carga, vacío, error y éxito.

La calidad automática se cubre con tests backend, JVM Android y Compose compilable.
La evaluación ASR/LLM está aislada en PR #6; esta rama añade la lógica y método de
evaluación del selector, pero no inventa mediciones de hardware ausente.
