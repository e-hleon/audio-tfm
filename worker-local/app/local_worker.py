import os, json, subprocess, tempfile, shutil, boto3, psycopg2, pika, traceback, sys
from pathlib import Path

# ─── configuración ───────────────────────────────────────────────────
SHARE_DIR = Path("/share")          # volumen compartido
# nombre del helper (puedes sobre-escribir con env si lo cambias)
CONTAINER = os.getenv("WHISPER_RUNTIME_CONTAINER", "whisper-runtime")
BIN       = os.getenv("WHISPER_BIN", "whisper-cli")       # wrapper opcional
MODEL     = os.getenv("WHISPER_MODEL")   # único parámetro que viene de .env

# ── CPU / GPU auto-detect ────────────────────────────────────────────
def _runtime_image() -> str:
    """Devuelve la imagen del contenedor helper (ej.: …whisper.cpp:main-cuda)."""
    try:
        return subprocess.check_output(
            ["docker", "inspect", "--format={{.Config.Image}}", CONTAINER],
            text=True).strip()
    except subprocess.CalledProcessError:
        return ""

# ① ¿el usuario seleccionó el profile 'gpu'?  → imagen acaba en 'cuda'
GPU_REQUESTED = "cuda" in _runtime_image().lower()

# ② ¿realmente hay GPU accesible dentro del contenedor?
def _gpu_available() -> bool:
    try:
        subprocess.check_call(
            ["docker", "exec", CONTAINER, "nvidia-smi", "-L"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

GPU_AVAILABLE = _gpu_available()

# ——— aborta si se pidió GPU y no existe ————————————————
if GPU_REQUESTED and not GPU_AVAILABLE:
    print("❌  Profile 'gpu' seleccionado pero no se detecta GPU. Saliendo.")
    sys.exit(1)

# flag para whisper.cpp
GPU_ON   = GPU_REQUESTED and GPU_AVAILABLE
gpu_flag = [] if GPU_ON else ["-ng"]

if not MODEL:
    # fallback: 1er .bin encontrado en /models
    default_bins = sorted(Path("/models").glob("*.bin"))
    if not default_bins:
        raise RuntimeError(
            "❌ WHISPER_MODEL no definido y no hay modelos en /models")
    MODEL = str(default_bins[0])
    print(f"ℹ️  WHISPER_MODEL no definido → usaremos {MODEL}")

# ─── clientes S3 / PG / etc. ───────────────────────────
s3 = boto3.client("s3",
    endpoint_url=f"http://{os.environ['MINIO_ENDPOINT']}",
    aws_access_key_id=os.environ["MINIO_ACCESS_KEY"],
    aws_secret_access_key=os.environ["MINIO_SECRET_KEY"])
bucket = os.environ["MINIO_BUCKET"]
pg = psycopg2.connect(os.environ["POSTGRES_DSN"])

# si el modelo no lleva /models delante → lo corregimos
if not MODEL.startswith("/"):
    MODEL = f"/models/{MODEL.lstrip('/')}"

def save_transcript(key: str, text: str) -> int:
    with pg, pg.cursor() as cur:
        cur.execute(
            "INSERT INTO transcripts (created_at, object_key, text)"
            " VALUES (NOW(), %s, %s) RETURNING id",
            (key, text))
        return cur.fetchone()[0]

# ─── invocación Whisper ------------------------------------------------
def transcribe(src: Path) -> str:
    # ── 1) normaliza a wav ─────────────────────────────
    if src.suffix.lower() != ".wav":
        dst = src.with_suffix(".wav")
        subprocess.check_call(
            ["ffmpeg", "-y", "-i", src, "-ar", "16000", "-ac", "1", dst],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        src.unlink()
        src = dst

    # ── 2) mueve al volumen compartido ─────────────────
    shared = SHARE_DIR / src.name
    shutil.move(src, shared)
    out_base = shared.with_suffix("")          # /share/tmpabcd

    # ── 3) invoca whisper.cpp (GPU o CPU) ──────────────
    cmd = ["docker","exec",CONTAINER,BIN,
           "-m", MODEL, "-l", "es", *gpu_flag,
           "-otxt", "-of", str(out_base), str(shared)]
    subprocess.check_call(cmd)

    # ── 4) recoge resultado y limpia ───────────────────
    txt = out_base.with_suffix(".txt").read_text()
    shared.unlink(missing_ok=True)
    out_base.with_suffix(".txt").unlink(missing_ok=True)
    return txt


# ---------- RabbitMQ ----------
def callback(ch, method, _props, body):
    try:
        msg = json.loads(body)
        key = msg["object_key"]
        ext = Path(key).suffix or ".wav"

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            s3.download_file(bucket, key, tmp.name)
            txt  = transcribe(Path(tmp.name))
            tid  = save_transcript(key, txt)

            # avisa al worker NLP
            ch.basic_publish(exchange="", routing_key="nlp",
                             body=json.dumps({"transcript_id": tid}))

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception:
        traceback.print_exc()
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

params   = pika.URLParameters(os.environ["RABBITMQ_URL"])
channel  = pika.BlockingConnection(params).channel()
channel.queue_declare(queue="transcribe")
channel.queue_declare(queue="nlp")
channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue="transcribe", on_message_callback=callback)
print(" [*] Transcribe worker started. Waiting for messages.")
channel.start_consuming()
