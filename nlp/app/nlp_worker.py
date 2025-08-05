import os, json, psycopg2, openai, pika, traceback
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

# RabbitMQ
connection = pika.BlockingConnection(pika.URLParameters(os.environ["RABBITMQ_URL"]))
channel = connection.channel()
channel.queue_declare(queue="nlp")
channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue="nlp", on_message_callback=callback)
print(" [*] NLP worker started. Waiting for messages.")
channel.start_consuming()
