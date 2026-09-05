# Validación — persistencia y diario diario

Fecha de validación: 2026-09-05. Se usó el audio público `jfk.wav` de
whisper.cpp, guardado temporalmente e ignorado por Git. No se usaron datos
personales ni se versionaron audio, modelos, respuestas o credenciales.

## Pruebas automatizadas

Con PostgreSQL 16 real y Alembic aplicado desde una base vacía:

```text
57 passed, 1 warning
```

Los tests usan transcriptor y generador LLM falsos: no requieren GPU, clave de
OpenAI ni llamadas externas. Cubren la agregación cronológica, UTC/Madrid/DST,
`missing`/`ready`/`stale`, regeneración, carrera de fingerprint, fallos seguros de
LLM y base de datos, y la proyección privada enviada al resumen diario.

## Ejecución real de extremo a extremo

La API se reconstruyó con Docker Compose y se ejecutó `alembic upgrade head`.
La instancia cargó faster-whisper `base` en `cuda`, `int8_float16`.

1. `POST /process` con `recorded_at=2026-09-05T10:00:00Z` creó la interacción
   `f19d984c-de71-442f-a1bf-b89e787ee436`. ASR produjo texto no vacío y OpenAI
   devolvió un análisis estructurado válido.
2. `GET /interactions/{id}` confirmó la persistencia. `GET /days/2026-09-05` devolvió
   inicialmente `missing`.
3. `POST /days/2026-09-05/summary` devolvió `ready`; su lectura posterior también
   fue `ready`.
4. Un segundo `POST /process` público, con `recorded_at=2026-09-05T11:00:00Z`, creó
   `a4571e15-0752-4821-930e-e7eda7876882`. La lectura pasó a `stale`.
5. La regeneración explícita devolvió y mantuvo `ready`, con dos interacciones.
6. Se reiniciaron `postgres` y `api` sin borrar `postgres_data`; la lectura posterior
   mantuvo dos interacciones y el resumen `ready`. `GET /interactions` devolvió esas
   dos entradas en orden cronológico.

Modelo OpenAI efectivo: `gpt-5.4-mini-2026-03-17`.

| Llamada | Latencia | Tokens entrada/salida |
| --- | ---: | ---: |
| Análisis primera interacción | 1563 ms | 431 / 61 |
| Primer resumen diario | 3073 ms | 225 / 60 |
| Análisis segunda interacción | 1833 ms | 431 / 75 |
| Resumen regenerado | 2230 ms | 320 / 87 |

El test del generador falso inspecciona exactamente la entrada diaria y prueba que
solo contiene `local_time`, `summary`, `topics`, `decisions`, `tasks` y `reminders`.
La implementación serializa esa misma proyección en la llamada real; no incluye la
transcripción, audio, filename, identificadores técnicos ni metadatos ASR. `store=false`
se valida en las pruebas del proveedor. Esto no equivale a cero retención: los Data
Controls de la cuenta/proyecto se administran aparte.

## Límites

La generación sigue siendo síncrona y puede responder 409 si una interacción cambia
durante la llamada al proveedor. No hay reintentos automáticos, workers ni evaluación
formal de calidad del resumen. PostgreSQL conserva texto y análisis JSONB, pero no
guarda audio ni filename.
