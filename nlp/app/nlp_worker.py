import os, json, psycopg2, openai, pika, traceback, time
openai.api_key = os.environ["OPENAI_API_KEY"]

conn = psycopg2.connect(os.environ["POSTGRES_DSN"])

def add_summary(tid: int, summary: str):
    with conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE transcripts SET summary=%s WHERE id=%s", (summary, tid))

def callback(ch, method, properties, body):
    try:
        tid = json.loads(body)["transcript_id"]
        with conn.cursor() as cur:
            cur.execute("SELECT text FROM transcripts WHERE id=%s", (tid,))
            text = cur.fetchone()[0]

        prompt = f"Resume el siguiente texto en 3 frases:\n\n{text}"
        resp = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        add_summary(tid, resp.choices[0].message.content.strip())
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        traceback.print_exc()
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def connect_rabbit():
    params = pika.URLParameters(os.environ["RABBITMQ_URL"])
    params.heartbeat = 60
    params.blocked_connection_timeout = 300
    while True:
        try:
            c = pika.BlockingConnection(params)
            ch = c.channel()
            ch.queue_declare(queue="nlp")
            ch.basic_qos(prefetch_count=1)
            return c, ch
        except Exception as e:
            print(f"⏳ RabbitMQ no disponible ({e}); reintento en 3s", flush=True)
            time.sleep(3)

while True:
    connection, channel = connect_rabbit()
    channel.basic_consume(queue="nlp", on_message_callback=callback)
    print(" [*] NLP worker started. Waiting for messages.", flush=True)
    try:
        channel.start_consuming()
    except Exception as e:
        print(f"⚠️  NLP interrumpido: {e}. Reintentando en 2s…", flush=True)
        try: connection.close()
        except Exception: pass
        time.sleep(2)
