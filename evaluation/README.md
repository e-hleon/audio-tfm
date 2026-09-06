# Evaluación reproducible

La evaluación está separada del runtime en `requirements-eval.txt`. Los audios,
pesos y cachés se guardan en `.evaluation-cache/`, ignorado por Git.

## ASR

FLEURS (`google/fleurs`, configuración `es_419`, split `validation`) se descarga
con `datasets`. Su ficha declara licencia CC BY 4.0. Se ordenan los IDs y se aplica
una permutación con seed `20260905`; se conservan clips con referencia no vacía y
audio válido, preferentemente los clips cortos del corpus. El manifiesto registra
los IDs elegidos. Esto no pretende representar conversación espontánea: es una
medición controlada de reconocimiento de español.

```bash
python -m evaluation.asr.prepare --limit 50 --seed 20260905
python -m evaluation.asr.run --models base small --limit 50 --device cuda \
  --compute-type int8_float16 --resume
python -m evaluation.report
```

El tiempo de carga y el warmup quedan fuera de la latencia por muestra. Cada línea
JSONL registra audio, textos original/normalizado, idioma, duración, inferencia,
RTF, WER y CER. WER es la distancia de edición sobre palabras; la normalización es
Unicode NFC, minúsculas, eliminación de puntuación y espacios colapsados. No se
alteran números ni palabras. `nvidia-smi` se intenta sin bloquear el experimento;
si falla se registra que la telemetría no es fiable.

## LLM

`evaluation/fixtures/llm_cases.jsonl` contiene 36 textos sintéticos, con 17 casos
negativos o ambiguos y anotación explícita de decisiones, tareas y recordatorios.
Se llama una vez por caso a `OpenAIAnalyzer`, con el mismo prompt, schema estricto
y `store=false` de producción. Evidence se empareja 1:1 por igualdad tras
normalización ligera o porque una evidencia contiene a la otra. No se usa otro LLM
como juez. JSONL permite `--resume` y guarda errores; se registran modelo efectivo,
latencia y tokens devueltos por la SDK.

```bash
python -m evaluation.llm.run --fixtures evaluation/fixtures/llm_cases.jsonl \
  --model gpt-5.4-mini --max-cases 40 --resume
python -m evaluation.report
```

CI solo ejecuta los tests rápidos (`tests/test_evaluation.py`), sin GPU, corpus real
ni OpenAI. Los agregados medidos, si existen, se guardan en `docs/evaluation/results`
y las figuras regenerables en `docs/evaluation/figures`.

El holdout se ejecuta por separado:

```bash
python -m evaluation.llm.run --fixtures evaluation/fixtures/llm_holdout.jsonl \
  --output-dir docs/evaluation/results/llm-holdout --max-cases 15
```

Para ejecutar con el mismo runtime CUDA sin instalar dependencias en WSL:

```bash
docker build --target eval -t audio-tfm-eval .
docker run --rm --gpus all -v "$PWD/.evaluation-cache:/app/.evaluation-cache" \
  -v "$PWD/docs/evaluation:/app/docs/evaluation" audio-tfm-eval \
  python3 -m evaluation.asr.prepare --limit 50 --seed 20260905
docker run --rm --gpus all -v "$PWD/.evaluation-cache:/app/.evaluation-cache" \
  -v "$PWD/docs/evaluation:/app/docs/evaluation" audio-tfm-eval \
  python3 -m evaluation.asr.run --models base small --limit 50 --device cuda --compute-type int8_float16 --resume
```

El target es solo evaluación y no modifica la imagen `runtime` de producción.
