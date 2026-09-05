# 002 — Análisis LLM estructurado mediante OpenAI

## Problema

Tras transcribir localmente, el diario necesita extraer resumen, temas, decisiones,
tareas y recordatorios de manera que la API pueda validar el resultado y no dependa
de texto JSON informal generado por un prompt.

## Alternativas consideradas

1. Reglas locales: son transparentes, pero no cubren lenguaje espontáneo ni la
   variación necesaria para este TFM.
2. LLM local: preservaría también el texto en el equipo, pero un modelo útil para
   extracción compete por los 4 GB de VRAM con ASR, añade distribución de pesos y
   todavía no hay requisito que justifique esa complejidad.
3. OpenAI con JSON libre y validación posterior: deja la forma de la salida a una
   instrucción de lenguaje natural y aumenta fallos de integración.
4. OpenAI Responses API con Structured Outputs: separa ASR local de análisis y
   fuerza el JSON Schema de la API.

## Decisión

Elegir la cuarta opción con la SDK oficial `openai`, modelo configurable
`OPENAI_MODEL` y valor inicial `gpt-5.4-mini`, que es el modelo usado en la
validación real. Se usan `store=false`, un máximo de 1000 tokens de salida (el
esquema breve del MVP no necesita más y así se acotan coste y tamaño), JSON Schema
estricto y validación Pydantic posterior. Además, cada evidencia se valida como
subcadena literal del texto original.

Se introduce el protocolo mínimo `Analyzer`; OpenAI es su primera implementación.
La API conserva un proceso y añade `/analyses` y `/process`. Este último reutiliza
la transcripción y entrega solo el texto al analizador. Las instrucciones obligan a
una extracción conservadora y evidencia literal breve.

## Consecuencias

El audio permanece local, pero la transcripción se transmite a OpenAI cuando se
solicita análisis. `store=false` evita almacenar la respuesta como recurso de
Responses recuperable; no implica por sí mismo cero retención. Los Data Controls del
proyecto o cuenta son independientes y pueden permitir compartir inputs/outputs. Por
ello la interfaz y documentación informan del flujo y no se registran textos ni prompts.

Hay coste, latencia y disponibilidad externos. Sin `OPENAI_API_KEY`, la
transcripción sigue operativa y el análisis devuelve 503. La API traduce errores
comunes del proveedor sin revelar detalles sensibles. Un LLM local puede reemplazar
la implementación de `Analyzer` cuando haya evidencia de que sus recursos y calidad
son adecuados.
