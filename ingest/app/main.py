import os, tempfile, json, boto3, pika, psycopg2, uuid
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from sqlmodel import SQLModel
from pydantic import BaseModel

app = FastAPI()

# ---------- CONFIG JWT -------------
class Settings(BaseModel):
    authjwt_secret_key: str = os.getenv("JWT_SECRET", "change_me")
    authjwt_algorithm: str = os.getenv("JWT_ALGO", "HS256")

@AuthJWT.load_config
def get_config():
    return Settings()

# Excepción global → 401 json
@app.exception_handler(AuthJWTException)
def auth_exception(request, exc):
    return JSONResponse(status_code=exc.status_code,
                        content={"detail": exc.message})

s3 = boto3.client(
    "s3",
    endpoint_url=f"http://{os.environ['MINIO_ENDPOINT']}",
    aws_access_key_id=os.environ["MINIO_ACCESS_KEY"],
    aws_secret_access_key=os.environ["MINIO_SECRET_KEY"],
)
bucket = os.environ["MINIO_BUCKET"]

# ---------- MODELO lectura ----------
class Transcript(SQLModel, table=False):
    id: int
    created_at: datetime
    text: str | None
    summary: str | None

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
async def upload(file: UploadFile = File(...), Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
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

# ---------- ENDPOINT lectura --------
@app.get("/transcripts", response_model=list[Transcript])
async def list_transcripts(limit: int = 20, offset: int = 0, Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    with psycopg2.connect(os.environ["POSTGRES_DSN"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, created_at, text, summary
                FROM transcripts
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (limit, offset),
            )
            rows = cur.fetchall()
            return [
                Transcript(id=r[0], created_at=r[1], text=r[2], summary=r[3])
                for r in rows
            ]


@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), Authorize: AuthJWT = Depends()):
    access = Authorize.create_access_token(subject=form_data.username, expires_time=False)
    return {"access_token": access, "token_type": "bearer"}