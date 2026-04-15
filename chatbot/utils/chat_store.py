from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class ChatHistoryStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30)
        conn.execute('PRAGMA journal_mode=MEMORY')
        conn.execute('PRAGMA synchronous=NORMAL')
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS chat_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    user_text TEXT NOT NULL,
                    detected_lang TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    response TEXT NOT NULL,
                    model_key TEXT,
                    model_path TEXT,
                    model_version TEXT
                )
                '''
            )

    def log_chat(
        self,
        *,
        user_text: str,
        detected_lang: str,
        intent: str,
        confidence: float,
        response: str,
        model_key: str | None,
        model_path: str,
        model_version: str | None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                '''
                INSERT INTO chat_logs (
                    created_at, user_text, detected_lang, intent, confidence,
                    response, model_key, model_path, model_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    datetime.now(timezone.utc).isoformat(),
                    user_text,
                    detected_lang,
                    intent,
                    confidence,
                    response,
                    model_key,
                    model_path,
                    model_version,
                ),
            )
