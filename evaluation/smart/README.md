# Evaluación funcional sintética de smart capture

`generate_corpus.py` crea WAV PCM16 mono de 16 kHz con silencio, ruido y bloques
sinusoidales speech-like, más un manifest de intervalos ground truth. Estos datos
solo prueban que el protocolo y los límites son reproducibles; no son habla real y
no permiten afirmar precisión de reconocimiento. La métrica planificada cuenta
frames predichos como activos si intersectan un intervalo real con tolerancia de
100 ms y calcula TP/FP/FN, precision, recall y F1. La calibración speaker debe usar
separadamente enrollment/genuine/impostor consentidos y reportar FAR/FRR.

```bash
python3 evaluation/smart/generate_corpus.py
```
