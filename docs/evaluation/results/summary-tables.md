# Resultados agregados

## ASR

| Modelo | muestras | WER | CER | latencia mediana (s) | p95 (s) | RTF | load time (s) |
|---|---:|---:|---:|---:|---:|---:|---:|

## Extracción LLM

### Desarrollo posterior al prompt

| Categoría | TP | FP | FN | precision | recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| decisions | 9 | 5 | 0 | 0.643 | 1.000 | 0.783 |
| tasks | 12 | 0 | 2 | 1.000 | 0.857 | 0.923 |
| reminders | 8 | 4 | 0 | 0.667 | 1.000 | 0.800 |
| micro | 29 | 9 | 2 | 0.763 | 0.935 | 0.841 |

### Holdout sintético independiente

| Categoría | TP | FP | FN | precision | recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| decisions | 5 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| tasks | 6 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| reminders | 4 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| micro | 15 | 0 | 0 | 1.000 | 1.000 | 1.000 |
