from __future__ import annotations

import csv
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from psycopg import connect
from psycopg.rows import dict_row


class ChatHistoryStore:
    def __init__(self, postgres_cfg: dict[str, Any] | str) -> None:
        self.backend = 'postgresql' if isinstance(postgres_cfg, dict) else 'sqlite'
        self.postgres_cfg = postgres_cfg if isinstance(postgres_cfg, dict) else None
        self.sqlite_path = Path(postgres_cfg).resolve() if isinstance(postgres_cfg, str) else None
        self.conninfo = self._build_conninfo(postgres_cfg) if isinstance(postgres_cfg, dict) else None
        if self.sqlite_path is not None:
            self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @staticmethod
    def _build_conninfo(postgres_cfg: dict[str, Any]) -> str:
        host = postgres_cfg.get('host', 'localhost')
        port = postgres_cfg.get('port', 5432)
        database = postgres_cfg.get('database', 'chatbot')
        user = postgres_cfg.get('user', 'postgres')
        password = postgres_cfg.get('password', 'P@ssw0rd')
        sslmode = postgres_cfg.get('sslmode', 'prefer')
        return (
            f"host={host} port={port} dbname={database} user={user} "
            f"password={password} sslmode={sslmode}"
        )

    def _connect(self):
        if self.backend == 'sqlite':
            return sqlite3.connect(str(self.sqlite_path), timeout=30)
        return connect(self.conninfo, row_factory=dict_row)

    def _initialize(self) -> None:
        if self.backend == 'sqlite':
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
                        model_version TEXT,
                        corrected_intent TEXT
                    )
                    '''
                )
            return

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                '''
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
                    model_path TEXT,
                    model_version VARCHAR(80),
                    review_status VARCHAR(32) NOT NULL DEFAULT 'unreviewed',
                    corrected_intent VARCHAR(80),
                    admin_notes TEXT
                )
                '''
            )
            cur.execute('ALTER TABLE chat_logs ADD COLUMN IF NOT EXISTS corrected_intent VARCHAR(80)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_chat_logs_created_at ON chat_logs (created_at DESC)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_chat_logs_intent ON chat_logs (intent)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_chat_logs_review_status ON chat_logs (review_status)')
            conn.commit()

    def log_chat(
        self,
        *,
        session_id: str | None = None,
        user_text: str,
        detected_lang: str,
        intent: str,
        confidence: float,
        response: str,
        response_source: str = 'static',
        retrieval_intent: str | None = None,
        retrieval_question: str | None = None,
        entity_label: str | None = None,
        is_fallback: bool = False,
        is_guardrail: bool = False,
        model_key: str | None = None,
        model_path: str = '',
        model_version: str | None = None,
    ) -> None:
        if self.backend == 'sqlite':
            with self._connect() as conn:
                conn.execute(
                    '''
                    INSERT INTO chat_logs (
                        created_at, user_text, detected_lang, intent, confidence, response, model_key, model_path, model_version
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
            return

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO chat_logs (
                    session_id, user_text, detected_lang, intent, confidence, response,
                    response_source, retrieval_intent, retrieval_question, entity_label,
                    is_fallback, is_guardrail, model_key, model_path, model_version
                ) VALUES (
                    %(session_id)s, %(user_text)s, %(detected_lang)s, %(intent)s, %(confidence)s, %(response)s,
                    %(response_source)s, %(retrieval_intent)s, %(retrieval_question)s, %(entity_label)s,
                    %(is_fallback)s, %(is_guardrail)s, %(model_key)s, %(model_path)s, %(model_version)s
                )
                ''',
                {
                    'session_id': session_id,
                    'user_text': user_text,
                    'detected_lang': detected_lang,
                    'intent': intent,
                    'confidence': confidence,
                    'response': response,
                    'response_source': response_source,
                    'retrieval_intent': retrieval_intent,
                    'retrieval_question': retrieval_question,
                    'entity_label': entity_label,
                    'is_fallback': is_fallback,
                    'is_guardrail': is_guardrail,
                    'model_key': model_key,
                    'model_path': model_path,
                    'model_version': model_version,
                },
            )
            conn.commit()

    def fetch_summary(self, *, low_confidence_threshold: float) -> dict[str, Any]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                '''
                SELECT
                    COUNT(*) AS total_chats,
                    COALESCE(AVG(confidence), 0) AS avg_confidence,
                    COUNT(*) FILTER (WHERE is_fallback) AS fallback_count,
                    COUNT(*) FILTER (WHERE is_guardrail) AS guardrail_count,
                    COUNT(*) FILTER (WHERE confidence < %(threshold)s) AS low_confidence_count,
                    COUNT(*) FILTER (WHERE response_source = 'retrieval') AS retrieval_count,
                    COUNT(DISTINCT session_id) FILTER (WHERE session_id IS NOT NULL) AS unique_sessions,
                    COUNT(*) FILTER (WHERE review_status = 'unreviewed') AS unreviewed_count,
                    COUNT(*) FILTER (WHERE review_status = 'accepted') AS accepted_count,
                    COUNT(*) FILTER (WHERE review_status = 'rejected') AS rejected_count
                FROM chat_logs
                ''',
                {'threshold': low_confidence_threshold},
            )
            summary = cur.fetchone() or {}
            total = int(summary.get('total_chats') or 0)
            if total:
                summary['fallback_rate'] = float(summary['fallback_count']) / total
                summary['guardrail_rate'] = float(summary['guardrail_count']) / total
                summary['low_confidence_rate'] = float(summary['low_confidence_count']) / total
                summary['retrieval_rate'] = float(summary['retrieval_count']) / total
            else:
                summary['fallback_rate'] = 0.0
                summary['guardrail_rate'] = 0.0
                summary['low_confidence_rate'] = 0.0
                summary['retrieval_rate'] = 0.0
            return summary

    def fetch_intent_breakdown(self, *, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                '''
                SELECT intent, COUNT(*) AS count, ROUND(AVG(confidence)::numeric, 4) AS avg_confidence
                FROM chat_logs
                GROUP BY intent
                ORDER BY count DESC, intent ASC
                LIMIT %(limit)s
                ''',
                {'limit': limit},
            )
            return list(cur.fetchall())

    def fetch_flagged_phrases(self, *, low_confidence_threshold: float, limit: int = 15) -> list[dict[str, Any]]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                '''
                SELECT
                    user_text,
                    COUNT(*) AS hits,
                    MAX(created_at) AS last_seen,
                    MAX(intent) AS latest_intent,
                    ROUND(AVG(confidence)::numeric, 4) AS avg_confidence
                FROM chat_logs
                WHERE is_fallback OR is_guardrail OR confidence < %(threshold)s
                GROUP BY user_text
                ORDER BY hits DESC, last_seen DESC
                LIMIT %(limit)s
                ''',
                {'threshold': low_confidence_threshold, 'limit': limit},
            )
            return list(cur.fetchall())

    def fetch_recent_logs(
        self,
        *,
        limit: int = 50,
        flagged_only: bool = False,
        review_status: str | None = None,
        low_confidence_threshold: float = 0.55,
    ) -> list[dict[str, Any]]:
        clauses = []
        params: dict[str, Any] = {'limit': limit, 'threshold': low_confidence_threshold}
        if flagged_only:
            clauses.append('(is_fallback OR is_guardrail OR confidence < %(threshold)s)')
        if review_status:
            clauses.append('review_status = %(review_status)s')
            params['review_status'] = review_status
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ''

        query = f'''
            SELECT
                id, created_at, session_id, user_text, detected_lang, intent, confidence, response,
                response_source, retrieval_intent, retrieval_question, entity_label,
                is_fallback, is_guardrail, model_key, model_version,
                review_status, corrected_intent, admin_notes
            FROM chat_logs
            {where_sql}
            ORDER BY created_at DESC
            LIMIT %(limit)s
        '''
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(query, params)
            return list(cur.fetchall())

    def update_review(
        self,
        *,
        log_id: int,
        review_status: str,
        corrected_intent: str | None,
        admin_notes: str | None,
    ) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                '''
                UPDATE chat_logs
                SET review_status = %(review_status)s,
                    corrected_intent = %(corrected_intent)s,
                    admin_notes = %(admin_notes)s
                WHERE id = %(log_id)s
                ''',
                {
                    'review_status': review_status,
                    'corrected_intent': corrected_intent,
                    'admin_notes': admin_notes,
                    'log_id': log_id,
                },
            )
            conn.commit()

    def fetch_reviewed_for_export(self, *, limit: int | None = None) -> list[dict[str, Any]]:
        query = '''
            SELECT user_text, COALESCE(NULLIF(corrected_intent, ''), intent) AS export_intent, detected_lang
            FROM chat_logs
            WHERE review_status = 'accepted'
              AND COALESCE(NULLIF(corrected_intent, ''), intent) IS NOT NULL
            ORDER BY created_at ASC
        '''
        params: dict[str, Any] = {}
        if limit is not None:
            query += ' LIMIT %(limit)s'
            params['limit'] = limit
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(query, params)
            return list(cur.fetchall())

    def export_reviewed_to_csv(self, output_path: str | Path, *, limit: int | None = None) -> Path:
        rows = self.fetch_reviewed_for_export(limit=limit)
        output = Path(output_path).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=['text', 'intent', 'lang'])
            writer.writeheader()
            for row in rows:
                writer.writerow({'text': row['user_text'], 'intent': row['export_intent'], 'lang': row['detected_lang']})
        return output

    def export_logs_to_csv(self, output_path: str | Path, *, limit: int = 500) -> Path:
        rows = self.fetch_recent_logs(limit=limit)
        output = Path(output_path).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    'created_at', 'session_id', 'user_text', 'detected_lang', 'intent', 'confidence',
                    'response', 'response_source', 'retrieval_intent', 'entity_label',
                    'review_status', 'corrected_intent', 'admin_notes'
                ],
            )
            writer.writeheader()
            for row in rows:
                writer.writerow({
                    'created_at': row.get('created_at'),
                    'session_id': row.get('session_id'),
                    'user_text': row.get('user_text'),
                    'detected_lang': row.get('detected_lang'),
                    'intent': row.get('intent'),
                    'confidence': row.get('confidence'),
                    'response': row.get('response'),
                    'response_source': row.get('response_source'),
                    'retrieval_intent': row.get('retrieval_intent'),
                    'entity_label': row.get('entity_label'),
                    'review_status': row.get('review_status'),
                    'corrected_intent': row.get('corrected_intent'),
                    'admin_notes': row.get('admin_notes'),
                })
        return output
