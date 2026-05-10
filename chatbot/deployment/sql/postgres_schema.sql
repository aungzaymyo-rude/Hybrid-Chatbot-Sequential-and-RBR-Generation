CREATE TABLE IF NOT EXISTS chat_logs (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    session_id TEXT,
    user_text TEXT NOT NULL,
    detected_lang VARCHAR(12) NOT NULL,
    intent VARCHAR(80) NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    response TEXT NOT NULL,
    response_source VARCHAR(32) NOT NULL DEFAULT 'static',
    retrieval_intent VARCHAR(80),
    retrieval_question TEXT,
    entity_label VARCHAR(80),
    is_fallback BOOLEAN NOT NULL DEFAULT FALSE,
    is_guardrail BOOLEAN NOT NULL DEFAULT FALSE,
    model_key VARCHAR(80),
    requested_model_key VARCHAR(80),
    auto_switched BOOLEAN NOT NULL DEFAULT FALSE,
    model_path TEXT,
    model_version VARCHAR(80),
    review_status VARCHAR(32) NOT NULL DEFAULT 'unreviewed',
    corrected_intent VARCHAR(80),
    admin_notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_chat_logs_created_at ON chat_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_logs_intent ON chat_logs (intent);
CREATE INDEX IF NOT EXISTS idx_chat_logs_model_key ON chat_logs (model_key);
CREATE INDEX IF NOT EXISTS idx_chat_logs_review_status ON chat_logs (review_status);

CREATE TABLE IF NOT EXISTS admin_users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    password_salt VARCHAR(128) NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    must_change_password BOOLEAN NOT NULL DEFAULT TRUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_admin_users_username ON admin_users (username);

CREATE TABLE IF NOT EXISTS admin_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES admin_users(id) ON DELETE CASCADE,
    token_hash VARCHAR(128) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_admin_sessions_token_hash ON admin_sessions (token_hash);
CREATE INDEX IF NOT EXISTS idx_admin_sessions_expires_at ON admin_sessions (expires_at);
