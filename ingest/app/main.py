import os, tempfile, json, boto3, pika, psycopg2, uuid
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse

app = FastAPI()
s3 = boto3.client(
    "s3",
    endpoint_url=f"http://{os.environ['MINIO_ENDPOINT']}",
    aws_access_key_id=os.environ["MINIO_ACCESS_KEY"],
    aws_secret_access_key=os.environ["MINIO_SECRET_KEY"],
)
bucket = os.environ["MINIO_BUCKET"]

# connection = pika.BlockingConnection(pika.URLParameters(os.environ["RABBITMQ_URL"]))
# channel = connection.channel()
# channel.queue_declare(queue="transcribe")

# def publish(body: dict):
#     channel.basic_publish(exchange="", routing_key="transcribe", body=json.dumps(body))

def publish(body: dict):
    """Publica un JSON en la cola *transcribe* y cierra la conexión."""
    params = pika.URLParameters(os.environ["RABBITMQ_URL"])
    with pika.BlockingConnection(params) as conn:
        ch = conn.channel()
        ch.queue_declare(queue="transcribe")
        ch.basic_publish(exchange="", routing_key="transcribe",
                         body=json.dumps(body))

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    tmp_path = ""
    try:
#        # 1) guarda temporal
#        suffix = datetime.utcnow().strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex + ".opus"
        # 1) determina la extensión del archivo subido (.wav, .m4a, .mp3…)
        ext = Path(file.filename).suffix or ".wav"
        # 2) guarda temporal con esa misma extensión
        suffix = datetime.utcnow().strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex + ext
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        object_key = f"audio/{suffix}"
        # 2) sube a MinIO
        s3.upload_file(tmp_path, bucket, object_key)
        # 3) publica mensaje
        publish({"object_key": object_key})
        return JSONResponse({"status": "queued", "object_key": object_key})
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
