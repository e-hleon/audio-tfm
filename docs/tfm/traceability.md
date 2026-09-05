# Trazabilidad

| Requisito | Implementación | Tests/evidencia | Estado |
|---|---|---|---|
| Captura manual | `MediaRecorderAudioRecorder`, `CaptureViewModel` | tests JVM, PR #5 | existente |
| Histórico | `ProcessApi.interactions`, `HistoryScreen` | `BackendTest` | implementado, UI física pendiente |
| Vista diaria/resumen | `day`, `generateSummary`, `DayScreen` | backend existente, `BackendTest` | implementado |
| Continuo explícito | `CaptureForegroundService`, `AudioRecord` | tests de lógica | implementado, hardware pendiente |
| Chunks y WAV | `WavWriter`, `SegmentQueue` | `SmartAudioTest` | implementado |
| Smart/VAD | `SmartSegmenter`, `EnergyVad` | PCM sintético | experimental |
| Enrollment/similitud | `VoiceEnrollmentRecorder`, `AcousticSpeakerSimilarity` | tests matemáticos | baseline implementado |
| Privacidad | permisos, servicio visible, plantilla privada | revisión documental | implementado, revisión en dispositivo pendiente |
| Evaluación ASR/LLM | PR #6 separado | CI y harness | externa/pendiente por entorno |
