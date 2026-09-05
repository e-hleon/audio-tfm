# Evaluación experimental

## Objetivo y preguntas

Esta primera evaluación mide el comportamiento observable de los dos componentes
centrales del sistema: transcripción local y extracción estructurada posterior. Las
preguntas son: (P1) ¿qué WER presenta `base` frente a `small` en español?, (P2) ¿qué
coste de latencia introduce el modelo mayor y siguen siendo más rápidos que tiempo
real?, y (P3) ¿con qué precisión, recall y F1 se extraen decisiones, tareas y
recordatorios, incluyendo negativos?

## Entorno y metodología

Cada agregado registra fecha, commit, plataforma, modelo y parámetros. ASR usa el
pipeline real `app.transcription.Transcriber`, `device=cuda` y
`compute_type=int8_float16`, carga separada de inferencia y un warmup. Se guarda una
línea por muestra para poder reanudar. RTF se define como `inference_seconds /
audio_duration_seconds`; RTF menor que 1 significa más rápido que tiempo real.

El corpus ASR es [FLEURS](https://huggingface.co/datasets/google/fleurs) español `es_es`, validation, descargado automáticamente y
seleccionado mediante seed fija; el manifiesto conserva IDs. La fuente declara CC BY
4.0 (consúltese la ficha de `google/fleurs` en Hugging Face). WER y CER se calculan
tras una normalización conservadora: NFC, minúsculas, puntuación fuera y espacios
colapsados. Se distinguen WER de corpus (distancia agregada) y media de WER por clip.

El benchmark LLM contiene 36 textos sintéticos versionados, con responsables y
fechas presentes/ausentes, negaciones, hechos pasados, hipótesis, acciones vagas,
casos multi-categoría y conversaciones sin acción. El ground truth ancla cada
elemento en `evidence`. Un predicho y un esperado coinciden solo con la misma
categoría y evidencia igual tras normalización ligera o contención completa; el
matching es 1:1. Las métricas principales son TP/FP/FN y precision/recall/F1.

## Resultados

Los números se generan automáticamente; no se copian manualmente. La tabla ASR y
la tabla LLM se encuentran en [`summary-tables.md`](results/summary-tables.md) cuando
se han ejecutado los experimentos. Las figuras son `figures/asr-wer.(png|svg)`,
`figures/asr-rtf.(png|svg)` y `figures/llm-prf.(png|svg)`.

En este entorno de ejecución no se pudo medir todavía el benchmark real: no hay
acceso CUDA/NVML (`nvidia-smi` informa que el sistema bloquea GPU), no existe
`OPENAI_API_KEY` y Python no incluye `venv`/`pip` para instalar las dependencias.
Por tanto no se presentan cifras inventadas. Cuando se ejecute en el entorno del
TFM, `evaluation.report` leerá los JSON agregados y actualizará esta sección de
resultados mediante los artefactos generados.

## Interpretación y limitaciones

No es válido concluir que `small` mejora base ni que el LLM es fiable hasta disponer
de las ejecuciones reales. Incluso entonces, FLEURS contiene locuciones leídas y no
representa todas las conversaciones espontáneas, acentos o ruido. El tamaño de la
muestra es limitado y WER no mide comprensión semántica. El corpus LLM fue diseñado
por nosotros, una sola ejecución no mide varianza del proveedor y la API/modelo
externo pueden cambiar. F1 depende de la regla de evidence, aunque evita un juez
semántico opaco. La telemetría GPU puede ser incompleta en WSL. Esta evaluación no
mide captura continua, consumo energético, VAD ni diarización.

## Reproducibilidad

Consultar [`evaluation/README.md`](../../evaluation/README.md). Los comandos son
reanudables y los resultados crudos permanecen fuera de Git cuando contienen audio
o predicciones de gran tamaño. El benchmark no entrena modelos ni envía audio a
OpenAI; el benchmark LLM usa únicamente textos sintéticos.
