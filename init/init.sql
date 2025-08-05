CREATE TABLE IF NOT EXISTS transcripts (
  id SERIAL PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  object_key TEXT NOT NULL,
  text TEXT,
  summary TEXT
);
