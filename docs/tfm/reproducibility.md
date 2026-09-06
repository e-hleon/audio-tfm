# Reproducibilidad

## Estado medido

- Host: WSL2, Linux 6.18, RTX 3050 Laptop 4 GiB, driver 555.99.
- Docker: 28.3.2; imagen CUDA 12.3.2/cuDNN 9.
- Python runtime: 3.10 en la imagen.
- PostgreSQL: 16; migración `20260905_0001`.
- ASR: faster-whisper/CTranslate2 fijados por `requirements.txt`.
- Fallback: OpenSLR SLR61, mensajes meteorológicos, seed `20260906`.

## Comandos

```bash
docker compose -p audio-tfm-rehearsal up -d --wait postgres
docker build --target test -t audio-tfm-test .
alembic upgrade head
python3 -m pytest -q
python3 -m evaluation.asr.prepare --limit 50 --seed 20260905
```

FLEURS `es_419` sigue siendo el corpus previsto; su descarga quedó bloqueada en
esta sesión. No se versionan audio, modelos, claves, caches ni APKs.
