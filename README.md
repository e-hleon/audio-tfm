## Quick Start

```bash
# 1. Clona y crea el .env
git clone https://github.com/<tu-usuario>/audio-tfm.git
cd audio-tfm && cp .env.example .env       # ← edita API keys si vas a usar cloud

# 2. Descarga un modelo Whisper (small-q5_1 recomendado para CPU)
curl -L -o models/ggml-small-q5_1.bin \
  https://huggingface.co/ggml-org/whisper.cpp/resolve/main/ggml-small-q5_1.bin

# 3. Levanta la pila local (CPU) y crea el bucket idempotente
docker compose up -d
docker compose exec minio sh -c \
  'mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" && \
   mc mb local/audio || true'

# 4. Prueba: login + upload
TOKEN=$(curl -s -d "username=a" -d "password=b" http://localhost/login \
        | python -c 'import sys, json; print(json.load(sys.stdin)["access_token"])')

curl -H "Authorization: Bearer $TOKEN" \
     -F "file=@sample.m4a" \
     http://localhost/upload

