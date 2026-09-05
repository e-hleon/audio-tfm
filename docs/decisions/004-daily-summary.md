# 004 — Diario y resumen diario con datos derivados

## Problema

Las interacciones persistidas necesitan una vista diaria y un resumen narrativo sin
repetir extracción semántica ni enviar de nuevo la transcripción completa a un LLM.

## Decisión

Un día se calcula en `APP_TIMEZONE` como `[inicio local, siguiente inicio local)` y
se consulta en PostgreSQL usando sus límites UTC. `GET /days/{fecha}` agrega en orden
cronológico las decisiones, tareas y recordatorios ya guardados en `analysis` JSONB.
No hace llamadas externas.

`POST /days/{fecha}/summary` envía a OpenAI únicamente una proyección derivada por
interacción: hora local, resumen, temas, decisiones, tareas y recordatorios. Usa
Responses API, Structured Outputs estricto, `store=false` y un límite de 500 tokens.
El resultado `DailySummaryResult` se guarda en `daily_summaries` junto con un
fingerprint SHA-256 de los pares ordenados `interaction_id` y `updated_at`.

El estado se calcula al leer: sin fila es `missing`, un fingerprint igual es `ready`
y uno diferente es `stale`. Tras la llamada al LLM se recalcula el fingerprint; si
cambió, no se persiste el resultado y el cliente recibe 409 para reintentar.

## Alternativas descartadas

- Volver a enviar las transcripciones: aumenta innecesariamente los datos externos.
- Pedir de nuevo decisiones, tareas y recordatorios: puede alterar elementos ya
  validados y duplica coste.
- Guardar un booleano `stale`: se desincroniza con facilidad; el fingerprint es la
  fuente determinista de verdad.
- Locks distribuidos, Redis o workers: no son necesarios para detectar y rechazar la
  carrera en este flujo síncrono.

## Consecuencias

La generación es explícita y puede devolver 409 si el día cambia durante la llamada.
El volumen PostgreSQL conserva el resumen y las interacciones al recrear contenedores.
`store=false` no implica cero retención; los Data Controls de la cuenta o proyecto se
configuran por separado.
