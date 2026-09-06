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

El corpus ASR es [FLEURS](https://huggingface.co/datasets/google/fleurs) español `es_419`, validation, descargado automáticamente y
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

En esta sesión Docker confirma acceso de cómputo a una NVIDIA RTX 3050 Laptop y la
imagen reproducible de evaluación se construye correctamente. La preparación de
FLEURS falló al descargar un artefacto público desde Hugging Face (error de red del
transporte Xet); el reintento alternativo no completó. La clave no se imprime ni se
incorpora al repositorio. La ejecución LLM real de 36 fixtures sintéticos sí completó 36 llamadas:
6 respuestas válidas (16,67 %) y 30 rechazadas por `AnalysisInvalidResponse` porque
la evidencia devuelta no aparecía literalmente. Modelo efectivo:
`gpt-5.4-mini-2026-03-17`; latencia media 0,860 s, mediana 0,785 s, p95 0,971 s;
2.509 tokens de entrada y 306 de salida. El artefacto inicial no guardó subcategorías
de rechazo, por lo que la causa exacta de cada caso es retrospectivamente no disponible.
TP/FP/FN y F1 no se interpretan como
calidad semántica positiva al quedar rechazadas la mayoría de respuestas. Cuando
FLEURS esté disponible, `evaluation.report` leerá sus JSON agregados.

Tras una instrucción general de copia exacta de substring contiguo, la repetición
obtuvo 36/36 válidas. Desarrollo: decisions F1=0,783, tasks F1=0,923, reminders
F1=0,800 y micro F1=0,841 (TP=29, FP=9, FN=2). Latencia posterior: media 1,437 s,
mediana 1,428 s, p95 1,875 s; 16.256 tokens de entrada y 2.841 de salida. En un
holdout sintético independiente de 15 casos: 15/15 válidos y micro precision, recall
y F1=1,000. No debe generalizarse fuera de este corpus pequeño.

Como fallback acotado, se ejecutó SLR61 (OpenSLR), usando únicamente sus 100
mensajes meteorológicos españoles seleccionados con seed `20260906`. Este corpus
es distinto de FLEURS: contiene habla leída de español argentino/peninsular y se
distribuye bajo CC BY-SA 4.0. Con CUDA `int8_float16` y una RTX 3050, `base`
obtuvo WER de corpus 0,3315, CER 0,2880, latencia media 0,211 s y RTF medio
0,0642; `small` obtuvo WER 0,2166, CER 0,2540, latencia media 0,388 s y RTF
medio 0,1187. No hubo fallos en 100 muestras por modelo. Estos resultados son
MEASURED para SLR61 fallback, no sustituyen ni se presentan como resultados de
FLEURS ni como precisión sobre conversaciones espontáneas. La repetibilidad de
latencia se midió en 20 muestras fijas durante tres pasadas por modelo; los
valores están en `results/asr/fallback-latency-repeatability.json`.

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
