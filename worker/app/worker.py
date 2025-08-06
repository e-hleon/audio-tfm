import os, json, tempfile, psycopg2, boto3, openai, pika, traceback
import os, json, tempfile, psycopg2, boto3, openai, pika, traceback, time
from datetime import datetime
from pathlib import Path

openai.api_key = os.environ["OPENAI_API_KEY"]

s3 = boto3.client(
    "s3",
    endpoint_url=f"http://{os.environ['MINIO_ENDPOINT']}",
    aws_access_key_id=os.environ["MINIO_ACCESS_KEY"],
    aws_secret_access_key=os.environ["MINIO_SECRET_KEY"],
)
bucket = os.environ["MINIO_BUCKET"]

conn = psycopg2.connect(os.environ["POSTGRES_DSN"])

def save_transcript(obj_key: str, text: str) -> int:
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO transcripts (created_at, object_key, text) VALUES (now(), %s, %s) RETURNING id",
                (obj_key, text),
            )
            return cur.fetchone()[0]

def callback(ch, method, properties, body):
    try:
        msg = json.loads(body)
        key = msg["object_key"]
        ext = Path(key).suffix or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            s3.download_file(bucket, key, tmp.name)
            with open(tmp.name, "rb") as audio:
                resp = openai.audio.transcriptions.create(model="gpt-4o-mini-transcribe", file=audio)
                tid = save_transcript(key, resp.text)
                # envía a cola nlp
                ch.basic_publish(exchange="", routing_key="nlp", body=json.dumps({"transcript_id": tid}))
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except openai.RateLimitError:
        print("⚠️ Rate-limit: reencolando tras 60 s")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        time.sleep(60)
    except openai.BadRequestError as e:
        print("⚠️ Archivo no soportado:", e)
        ch.basic_ack(delivery_tag=method.delivery_tag)  # descarta mensaje
    except Exception as e:
        traceback.print_exc()
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

# RabbitMQ
connection = pika.BlockingConnection(pika.URLParameters(os.environ["RABBITMQ_URL"]))
channel = connection.channel()
channel.queue_declare(queue="transcribe")
channel.queue_declare(queue="nlp")
channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue="transcribe", on_message_callback=callback)
print(" [*] Transcribe worker started. Waiting for messages.")
channel.start_consuming()