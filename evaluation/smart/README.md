# Evaluación del selector inteligente

`SmartAudioTest` verifica la lógica con PCM matemático. Para una medición real,
un JSONL debe contener por segmento `expected_voice`, `detected_voice`,
`expected_user` y `accepted_user`. El script calcula VAD TP/FP/FN y, cuando hay
etiqueta de hablante, genuine/impostor accepted/rejected. No incluye cifras hasta
que existan grabaciones etiquetadas y consentidas.

```bash
python -m evaluation.smart.run --segments path/to/consented-segments.jsonl
```
