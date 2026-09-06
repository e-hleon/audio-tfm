# Notas para la defensa

| Concepto | Qué es y por qué aquí | Alternativa / límite |
|---|---|---|
| Docker/imagen/volumen | Empaqueta API y dependencias; el volumen conserva modelos/BD | instalación directa; no reproduce todo el hardware |
| FastAPI/Uvicorn/REST | API Python HTTP y servidor ASGI; contratos simples | Flask; una petición LLM es síncrona |
| PostgreSQL/SQLAlchemy/Alembic/JSONB | BD relacional, ORM, migraciones y análisis flexible | SQLite; JSONB reduce tablas hijas pero limita consultas |
| multipart | Transporte de archivo y `recorded_at` en `/process` | base64 sería mayor |
| Whisper/faster-whisper/CTranslate2/CUDA/VRAM | ASR preentrenado local acelerado; VRAM limita modelos | CPU, otro tamaño; WER no es comprensión |
| OpenAI Responses/Structured Outputs/JSON Schema/Pydantic | Extrae contrato validado y evidencia literal | LLM local; proveedor externo puede cambiar |
| Kotlin/Compose/ViewModel/StateFlow | UI declarativa y estados observables testeables | XML/LiveData; no se usa DI ceremonial |
| MediaRecorder/AudioRecord/PCM/WAV | AAC simple para manual; PCM permite frames y VAD | WAV ocupa más; el backend decodifica ambos |
| ForegroundService | Notificación persistente para captura explícita fuera de Activity | sin servicio se detiene al ocultar UI |
| VAD | Clasifica frames como voz/no voz por energía adaptativa | modelo VAD; baseline sensible a ruido |
| speaker similarity/coseno | Compara plantilla acústica local con segmento; en Pixel 8 saturó en 1.0000 para dos voces | baseline fallido/no discriminativo; no es biometría ni identifica terceros |
| WER/CER/precision/recall/F1/RTF | Métricas de ASR, extracción y velocidad | dependen de corpus y reglas de matching |
| fingerprint/stale | Huella de entradas del día detecta resumen desactualizado | ventana de concurrencia documentada |

La decisión importante es separar captura y subida Android sin introducir workers
backend: el servidor aún serializa inferencia ASR y el cliente sube una petición a
la vez.
