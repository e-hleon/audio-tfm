# Validación del análisis estructurado

Estado: validación real completada.

## Plan de evidencia

- Ejecutado: `docker run --rm --entrypoint python3 audio-tfm-tests -m pytest -q`.
  Resultado: **32 passed**, una advertencia de deprecación de Starlette/AnyIO.
  Incluye esquema, endpoints, errores y flujo `/process` con un analizador simulado;
  no requiere red, GPU ni clave OpenAI.
- La instancia Docker arrancó con `analysis_configured=true`, CUDA y
  `faster-whisper` `base` en `int8_float16`.
- Verificado por tests: el analizador recibe solamente el texto de la transcripción;
  la solicitud a la SDK se crea con `store: false` y `text.format` de tipo
  `json_schema` estricto. Los modelos Pydantic rechazan campos extra, evidencia
  ausente y texto vacío.
- `POST /analyses` con una transcripción sintética española no privada devolvió HTTP
  200. El resultado cumplió exactamente las cinco claves del esquema: una decisión,
  una tarea asignada a Ana, un recordatorio y evidencias no vacías. La frase sobre
  lluvia no fue convertida en tarea.
- `POST /process` con el WAV público JFK devolvió HTTP 200. La transcripción no fue
  vacía, indicó `device: cuda`, y el objeto `analysis` cumplió exactamente el esquema
  Pydantic; al ser una frase informativa no produjo decisiones, tareas ni recordatorios.
- Modelo efectivo: `gpt-5.4-mini-2026-03-17`, configurado mediante
  `OPENAI_MODEL=gpt-5.4-mini`. La llamada sintética usó 458 tokens de entrada,
  181 de salida y 1924 ms. `/process` usó 431 tokens de entrada, 51 de salida y
  1187 ms.
- En la ronda de endurecimiento, una salida que parafraseaba `evidence` fue rechazada
  determinísticamente con HTTP 502; una nota sintética sin elementos accionables y el
  flujo `/process` con JFK pasaron después de la corrección. Las llamadas mantienen
  `store=false` y `max_output_tokens=1000`.

## Privacidad y Git

La clave se configuró localmente sin inspeccionarla ni mostrarla. No aparece en los
logs ni en el repositorio. El audio usado fue público y se mantuvo en `tmp/`,
ignorado por Git. No se prepararon para commit claves, `.env`, audios, pesos de
modelos ni datos privados.

Las instrucciones conservadoras exigen evidencia breve y literal, listas vacías
cuando no hay soporte textual y `null` para fechas o responsables no deducibles.
