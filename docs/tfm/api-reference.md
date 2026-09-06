# Referencia API resumida

| Método | Ruta | Persistencia | Externo |
|---|---|---|---|
| GET | `/health` | no | no |
| POST | `/transcriptions` | no | ASR local |
| POST | `/analyses` | no | OpenAI texto opcional |
| POST | `/process` | interaction | ASR local + OpenAI texto opcional |
| GET | `/interactions` | lectura | no |
| GET | `/interactions/{id}` | lectura | no |
| GET | `/days/{YYYY-MM-DD}` | lectura/agregación | no |
| POST | `/days/{YYYY-MM-DD}/summary` | daily summary | OpenAI texto derivado opcional |

Errores principales: `400` audio inválido, `409` día vacío o carrera de summary,
`413` límites de audio, `422` entrada inválida, `429` cuota LLM, `502` respuesta
LLM no utilizable, `503` dependencia no disponible o ASR ocupado y `504` timeout.
Los contratos completos se sirven mediante OpenAPI en `/docs` y `/openapi.json`.

`POST /process` acepta opcionalmente `capture_mode` (`manual`, `continuous` o
`smart`), `capture_session_id`, `chunk_index` y `capture_chunk_id`. Continuous
requiere sesión e índice. `capture_chunk_id` es una clave UUID idempotente: si ya
existe, el backend devuelve el resultado persistido sin crear otra Interaction.
Las respuestas de interacción incluyen esos cuatro metadatos; los campos son
compatibles con filas legacy mediante valores seguros.
