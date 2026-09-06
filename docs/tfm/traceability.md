# Trazabilidad

| Requisito/objetivo | Implementación | Archivo | Test | Validación | Estado | Riesgo pendiente |
|---|---|---|---|---|---|---|
| Captura manual | MediaRecorder + ViewModel | `android/.../AudioRecorder.kt`, `CaptureViewModel.kt` | `CaptureViewModelTest` | `physical-device-plan` | automatizado JVM | dispositivo real |
| ASR local | faster-whisper CUDA | `app/transcription.py` | `tests/test_transcription.py` | smoke/benchmark | implementado | GPU/recurso |
| Análisis estructurado | Analyzer + schema | `app/analysis.py` | `tests/test_analysis.py` | LLM benchmark | implementado | proveedor externo |
| Persistencia | SQLAlchemy/Alembic | `app/models.py`, `repositories.py` | `test_persistence.py` | migración + API | implementado | concurrencia escala |
| Histórico/día | rutas y ViewModels | `app/main.py`, `DiaryViewModels.kt` | backend + JVM | dispositivo | implementado | timezone UI |
| Continuous | FGS, PCM16, sesión, chunking acústico, cola e idempotencia | `CaptureForegroundService.kt` | `SmartAudioTest`, `test_persistence.py` | dispositivo | automatizado; validación física de cambios pendiente | pausa acústica no es semántica; reanudación Android |
| Smart experimental | VAD, ring, similarity | `SmartAudio.kt` | `SmartAudioTest` | corpus sintético + Pixel 8 limitado | MEASURED físico limitado; baseline speaker no discriminativo | no biometría, sin FAR/FRR |
| Privacidad | cache privada, no audio al LLM | arquitectura + manifest | static check | revisión | implementado | terceros/retención |
