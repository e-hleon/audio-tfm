FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# ─── necesitamos el CLI de Docker; en Debian es el paquete docker.io ───
RUN apt-get update \
 && apt-get install -y --no-install-recommends docker.io ffmpeg \
 && rm -rf /var/lib/apt/lists/*
COPY app/ app/
CMD ["python", "-u", "app/local_worker.py"]
