-- Idempotent schema; applied on start-up by every service that needs the database.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS machines (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    machine_type    TEXT NOT NULL CHECK (machine_type IN ('pump', 'motor', 'compressor')),
    model           TEXT NOT NULL,
    location        TEXT NOT NULL,
    rated_current_a REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS sensor_readings (
    id             BIGSERIAL PRIMARY KEY,
    machine_id     TEXT NOT NULL REFERENCES machines(id),
    ts             TIMESTAMPTZ NOT NULL DEFAULT now(),
    temperature_c  REAL,
    vibration_mm_s REAL,
    pressure_bar   REAL,
    current_a      REAL
);
CREATE INDEX IF NOT EXISTS sensor_readings_machine_ts ON sensor_readings (machine_id, ts DESC);

CREATE TABLE IF NOT EXISTS documents (
    id            SERIAL PRIMARY KEY,
    doc_id        TEXT NOT NULL UNIQUE,
    filename      TEXT NOT NULL,
    title         TEXT NOT NULL,
    machine_type  TEXT NOT NULL,
    access_level  TEXT NOT NULL CHECK (access_level IN ('viewer', 'technician')),
    pages         INTEGER NOT NULL,
    sha256        TEXT NOT NULL,
    ingested_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
    id              BIGSERIAL PRIMARY KEY,
    document_id     INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page            INTEGER NOT NULL,
    chunk_index     INTEGER NOT NULL,
    content         TEXT NOT NULL,
    machine_type    TEXT NOT NULL,
    access_level    TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    embedding       vector(1024) NOT NULL
);
CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS chunks_filter ON chunks (embedding_model, machine_type, access_level);

CREATE TABLE IF NOT EXISTS tickets (
    id          SERIAL PRIMARY KEY,
    machine_id  TEXT NOT NULL REFERENCES machines(id),
    title       TEXT NOT NULL,
    description TEXT NOT NULL,
    priority    TEXT NOT NULL CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    status      TEXT NOT NULL DEFAULT 'open',
    created_by  TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_log (
    id         BIGSERIAL PRIMARY KEY,
    ts         TIMESTAMPTZ NOT NULL DEFAULT now(),
    principal  TEXT NOT NULL,
    role       TEXT,
    tool       TEXT NOT NULL,
    arguments  JSONB NOT NULL,
    status     TEXT NOT NULL CHECK (status IN ('ok', 'denied', 'invalid', 'error')),
    detail     TEXT
);
CREATE INDEX IF NOT EXISTS audit_log_ts ON audit_log (ts DESC);
