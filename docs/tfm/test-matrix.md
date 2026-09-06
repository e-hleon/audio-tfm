# Matriz final de pruebas

| Función | Unit | Integración | E2E | Físico | Estado |
|---|---|---|---|---|---|
| ASR | sí, mock/decodificación | suite Docker | GPU fallback real | no | MEASURED parcial |
| LLM | sí | contratos | OpenAI histórico | no | MEASURED sintético |
| Persistencia | sí | PostgreSQL fresco | flujo mock | no | MEASURED |
| DailySummary | sí | timezone/fingerprint | OpenAI real no repetido | no | MEASURED parcial |
| Manual Android | JVM | CI Android | no | no | CI MEASURED |
| Continuous | JVM lógico: pausa, hard cap, flush y conservación de samples | API/PostgreSQL: metadata + retry idempotente | no | Pixel 8 ya validó captura física previa; cambios nuevos pendientes | AUTOMATED; PHYSICAL PENDING |
| Smart | JVM lógico | no | no | Pixel 8: silencio y frases consentidas | MEASURED físico limitado; VAD mejorado, sin precisión general |
| Speaker baseline | JVM numérico | no | no | Pixel 8: voz propia y otra voz | MEASURED físico mínimo: no discriminativo; FAR/FRR NOT MEASURED |
| Batería | no | no | no | no | NOT MEASURED |
| Emulator `androidTest` | compilación workflow separado | no | dispatch bloqueado | no | BLOCKED |
