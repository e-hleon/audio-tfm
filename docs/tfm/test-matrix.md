# Matriz final de pruebas

| Función | Unit | Integración | E2E | Físico | Estado |
|---|---|---|---|---|---|
| ASR | sí, mock/decodificación | suite Docker | GPU fallback real | no | MEASURED parcial |
| LLM | sí | contratos | OpenAI histórico | no | MEASURED sintético |
| Persistencia | sí | PostgreSQL fresco | flujo mock | no | MEASURED |
| DailySummary | sí | timezone/fingerprint | OpenAI real no repetido | no | MEASURED parcial |
| Manual Android | JVM | CI Android | no | no | CI MEASURED |
| Continuous | JVM lógico | no | no | no | NOT MEASURED |
| Smart | JVM lógico | no | no | no | MEASURED sintético |
| Speaker baseline | JVM numérico | no | no | no | MEASURED limitado |
| Batería | no | no | no | no | NOT MEASURED |
| Emulator `androidTest` | compilación workflow separado | no | dispatch bloqueado | no | BLOCKED |
