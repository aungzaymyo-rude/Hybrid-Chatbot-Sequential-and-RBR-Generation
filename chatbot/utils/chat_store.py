from __future__ import annotations

import csv
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from psycopg import connect
from psycopg.rows import dict_row

from chatbot.utils.admin_auth import (
    AuthenticatedAdmin,
    generate_session_token,
    hash_password,
    hash_session_token,
    session_expiry,
    utc_now,
    verify_password,
)
from chatbot.utils.report_analysis import analyze_report_input


class ChatHistoryStore:
    def __init__(self, postgres_cfg: dict[str, Any] | str, admin_auth_cfg: dict[str, Any] | None = None) -> None:
        self.backend = 'postgresql' if isinstance(postgres_cfg, dict) else 'sqlite'
        self.postgres_cfg = postgres_cfg if isinstance(postgres_cfg, dict) else None
        self.sqlite_path = Path(postgres_cfg).resolve() if isinstance(postgres_cfg, str) else None
        self.conninfo = self._build_conninfo(postgres_cfg) if isinstance(postgres_cfg, dict) else None
        self.admin_auth_cfg = admin_auth_cfg or {}
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
                    requested_model_key TEXT,
                    auto_switched INTEGER NOT NULL DEFAULT 0,
                    model_path TEXT,
                    model_version TEXT,
                        corrected_intent TEXT
                    )
                    '''
                )
                conn.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS admin_users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL UNIQUE,
                        password_salt TEXT NOT NULL,
                        password_hash TEXT NOT NULL,
                        must_change_password INTEGER NOT NULL DEFAULT 1,
                        is_active INTEGER NOT NULL DEFAULT 1,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        last_login_at TEXT
                    )
                    '''
                )
                conn.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS admin_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        token_hash TEXT NOT NULL UNIQUE,
                        created_at TEXT NOT NULL,
                        expires_at TEXT NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES admin_users(id) ON DELETE CASCADE
                    )
                    '''
                )
                conn.execute('CREATE INDEX IF NOT EXISTS idx_admin_sessions_token_hash ON admin_sessions (token_hash)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_admin_sessions_expires_at ON admin_sessions (expires_at)')
                self._ensure_default_admin_sqlite(conn)
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
                    requested_model_key VARCHAR(80),
                    auto_switched BOOLEAN NOT NULL DEFAULT FALSE,
                    model_path TEXT,
                    model_version VARCHAR(80),
                    review_status VARCHAR(32) NOT NULL DEFAULT 'unreviewed',
                    corrected_intent VARCHAR(80),
                    admin_notes TEXT
                )
                '''
            )
            cur.execute('ALTER TABLE chat_logs ADD COLUMN IF NOT EXISTS corrected_intent VARCHAR(80)')
            cur.execute('ALTER TABLE chat_logs ADD COLUMN IF NOT EXISTS requested_model_key VARCHAR(80)')
            cur.execute('ALTER TABLE chat_logs ADD COLUMN IF NOT EXISTS auto_switched BOOLEAN NOT NULL DEFAULT FALSE')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_chat_logs_created_at ON chat_logs (created_at DESC)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_chat_logs_intent ON chat_logs (intent)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_chat_logs_model_key ON chat_logs (model_key)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_chat_logs_review_status ON chat_logs (review_status)')
            cur.execute(
                '''
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
                )
                '''
            )
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS admin_sessions (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES admin_users(id) ON DELETE CASCADE,
                    token_hash VARCHAR(128) NOT NULL UNIQUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    expires_at TIMESTAMPTZ NOT NULL
                )
                '''
            )
            cur.execute('CREATE INDEX IF NOT EXISTS idx_admin_users_username ON admin_users (username)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_admin_sessions_token_hash ON admin_sessions (token_hash)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_admin_sessions_expires_at ON admin_sessions (expires_at)')
            self._ensure_default_admin_postgres(cur)
            conn.commit()

    def _default_admin_credentials(self) -> tuple[str, str]:
        return (
            str(self.admin_auth_cfg.get('default_username', 'admin')),
            str(self.admin_auth_cfg.get('default_password', 'admin')),
        )

    def _ensure_default_admin_sqlite(self, conn: sqlite3.Connection) -> None:
        username, password = self._default_admin_credentials()
        existing = conn.execute('SELECT id FROM admin_users WHERE username = ?', (username,)).fetchone()
        if existing:
            return
        salt, digest = hash_password(password)
        now = utc_now().isoformat()
        conn.execute(
            '''
            INSERT INTO admin_users (
                username, password_salt, password_hash, must_change_password, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (username, salt, digest, 1, 1, now, now),
        )

    def _ensure_default_admin_postgres(self, cur) -> None:
        username, password = self._default_admin_credentials()
        cur.execute('SELECT id FROM admin_users WHERE username = %(username)s', {'username': username})
        if cur.fetchone():
            return
        salt, digest = hash_password(password)
        cur.execute(
            '''
            INSERT INTO admin_users (
                username, password_salt, password_hash, must_change_password, is_active
            ) VALUES (%(username)s, %(salt)s, %(digest)s, TRUE, TRUE)
            ''',
            {'username': username, 'salt': salt, 'digest': digest},
        )

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
        requested_model_key: str | None = None,
        auto_switched: bool = False,
        model_path: str = '',
        model_version: str | None = None,
    ) -> None:
        if self.backend == 'sqlite':
            with self._connect() as conn:
                conn.execute(
                    '''
                    INSERT INTO chat_logs (
                        created_at, user_text, detected_lang, intent, confidence, response, model_key, requested_model_key, auto_switched, model_path, model_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        datetime.now(timezone.utc).isoformat(),
                        user_text,
                        detected_lang,
                        intent,
                        confidence,
                        response,
                        model_key,
                        requested_model_key,
                        int(auto_switched),
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
                    is_fallback, is_guardrail, model_key, requested_model_key, auto_switched, model_path, model_version
                ) VALUES (
                    %(session_id)s, %(user_text)s, %(detected_lang)s, %(intent)s, %(confidence)s, %(response)s,
                    %(response_source)s, %(retrieval_intent)s, %(retrieval_question)s, %(entity_label)s,
                    %(is_fallback)s, %(is_guardrail)s, %(model_key)s, %(requested_model_key)s, %(auto_switched)s, %(model_path)s, %(model_version)s
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
                    'requested_model_key': requested_model_key,
                    'auto_switched': auto_switched,
                    'model_path': model_path,
                    'model_version': model_version,
                },
            )
            conn.commit()

    def fetch_summary(self, *, low_confidence_threshold: float, model_key: str | None = None) -> dict[str, Any]:
        where_sql = ''
        params: dict[str, Any] = {'threshold': low_confidence_threshold}
        if model_key:
            where_sql = 'WHERE model_key = %(model_key)s'
            params['model_key'] = model_key
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f'''
                SELECT
                    COUNT(*) AS total_chats,
                    COALESCE(AVG(confidence), 0) AS avg_confidence,
                    COUNT(*) FILTER (WHERE is_fallback) AS fallback_count,
                    COUNT(*) FILTER (WHERE is_guardrail) AS guardrail_count,
                    COUNT(*) FILTER (WHERE confidence < %(threshold)s) AS low_confidence_count,
                    COUNT(*) FILTER (WHERE response_source = 'retrieval') AS retrieval_count,
                    COUNT(*) FILTER (WHERE auto_switched) AS auto_switch_count,
                    COUNT(DISTINCT session_id) FILTER (WHERE session_id IS NOT NULL) AS unique_sessions,
                    COUNT(*) FILTER (WHERE review_status = 'unreviewed') AS unreviewed_count,
                    COUNT(*) FILTER (WHERE review_status = 'accepted') AS accepted_count,
                    COUNT(*) FILTER (WHERE review_status = 'rejected') AS rejected_count
                FROM chat_logs
                {where_sql}
                ''',
                params,
            )
            summary = cur.fetchone() or {}
            total = int(summary.get('total_chats') or 0)
            if total:
                summary['fallback_rate'] = float(summary['fallback_count']) / total
                summary['guardrail_rate'] = float(summary['guardrail_count']) / total
                summary['low_confidence_rate'] = float(summary['low_confidence_count']) / total
                summary['retrieval_rate'] = float(summary['retrieval_count']) / total
                summary['auto_switch_rate'] = float(summary['auto_switch_count']) / total
            else:
                summary['fallback_rate'] = 0.0
                summary['guardrail_rate'] = 0.0
                summary['low_confidence_rate'] = 0.0
                summary['retrieval_rate'] = 0.0
                summary['auto_switch_rate'] = 0.0
            summary['active_model_key'] = model_key or ''
            return summary

    def fetch_intent_breakdown(self, *, limit: int = 20, model_key: str | None = None) -> list[dict[str, Any]]:
        where_sql = ''
        params: dict[str, Any] = {'limit': limit}
        if model_key:
            where_sql = 'WHERE model_key = %(model_key)s'
            params['model_key'] = model_key
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f'''
                SELECT intent, COUNT(*) AS count, ROUND(AVG(confidence)::numeric, 4) AS avg_confidence
                FROM chat_logs
                {where_sql}
                GROUP BY intent
                ORDER BY count DESC, intent ASC
                LIMIT %(limit)s
                ''',
                params,
            )
            return list(cur.fetchall())

    def fetch_flagged_phrases(self, *, low_confidence_threshold: float, limit: int = 15, model_key: str | None = None) -> list[dict[str, Any]]:
        extra_filter = ''
        params: dict[str, Any] = {'threshold': low_confidence_threshold, 'limit': limit}
        if model_key:
            extra_filter = ' AND model_key = %(model_key)s'
            params['model_key'] = model_key
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f'''
                SELECT
                    user_text,
                    COUNT(*) AS hits,
                    MAX(created_at) AS last_seen,
                    MAX(intent) AS latest_intent,
                    ROUND(AVG(confidence)::numeric, 4) AS avg_confidence,
                    MAX(model_key) AS model_key
                FROM chat_logs
                WHERE (is_fallback OR is_guardrail OR confidence < %(threshold)s){extra_filter}
                GROUP BY user_text
                ORDER BY hits DESC, last_seen DESC
                LIMIT %(limit)s
                ''',
                params,
            )
            return list(cur.fetchall())

    def fetch_model_breakdown(self, *, low_confidence_threshold: float) -> list[dict[str, Any]]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                '''
                SELECT
                    COALESCE(model_key, 'unassigned') AS model_key,
                    COUNT(*) AS count,
                    ROUND(AVG(confidence)::numeric, 4) AS avg_confidence,
                    COUNT(*) FILTER (WHERE is_fallback) AS fallback_count,
                    COUNT(*) FILTER (WHERE is_guardrail) AS guardrail_count,
                    COUNT(*) FILTER (WHERE confidence < %(threshold)s) AS low_confidence_count,
                    COUNT(*) FILTER (WHERE response_source = 'retrieval') AS retrieval_count,
                    COUNT(*) FILTER (WHERE auto_switched) AS auto_switch_count
                FROM chat_logs
                GROUP BY COALESCE(model_key, 'unassigned')
                ORDER BY count DESC, model_key ASC
                ''',
                {'threshold': low_confidence_threshold},
            )
            rows = list(cur.fetchall())
            for row in rows:
                total = int(row.get('count') or 0)
                if total:
                    row['fallback_rate'] = float(row['fallback_count']) / total
                    row['guardrail_rate'] = float(row['guardrail_count']) / total
                    row['low_confidence_rate'] = float(row['low_confidence_count']) / total
                    row['retrieval_rate'] = float(row['retrieval_count']) / total
                    row['auto_switch_rate'] = float(row['auto_switch_count']) / total
                else:
                    row['fallback_rate'] = 0.0
                    row['guardrail_rate'] = 0.0
                    row['low_confidence_rate'] = 0.0
                    row['retrieval_rate'] = 0.0
                    row['auto_switch_rate'] = 0.0
            return rows

    def fetch_recent_logs(
        self,
        *,
        limit: int = 50,
        flagged_only: bool = False,
        review_status: str | None = None,
        model_key: str | None = None,
        low_confidence_threshold: float = 0.55,
    ) -> list[dict[str, Any]]:
        clauses = []
        params: dict[str, Any] = {'limit': limit, 'threshold': low_confidence_threshold}
        if flagged_only:
            clauses.append('(is_fallback OR is_guardrail OR confidence < %(threshold)s)')
        if review_status:
            clauses.append('review_status = %(review_status)s')
            params['review_status'] = review_status
        if model_key:
            clauses.append('model_key = %(model_key)s')
            params['model_key'] = model_key
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ''

        query = f'''
            SELECT
                id, created_at, session_id, user_text, detected_lang, intent, confidence, response,
                response_source, retrieval_intent, retrieval_question, entity_label,
                is_fallback, is_guardrail, model_key, requested_model_key, auto_switched, model_version,
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
                    'model_key', 'requested_model_key', 'auto_switched',
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
                    'model_key': row.get('model_key'),
                    'requested_model_key': row.get('requested_model_key'),
                    'auto_switched': row.get('auto_switched'),
                    'review_status': row.get('review_status'),
                    'corrected_intent': row.get('corrected_intent'),
                    'admin_notes': row.get('admin_notes'),
                })
        return output

    def fetch_report_analysis_error_rows(
        self,
        *,
        limit: int = 1000,
        low_confidence_threshold: float = 0.55,
    ) -> list[dict[str, Any]]:
        rows = self.fetch_recent_logs(limit=limit, model_key='report', low_confidence_threshold=low_confidence_threshold)
        output: list[dict[str, Any]] = []
        for row in rows:
            analysis = analyze_report_input(str(row.get('user_text') or ''))
            if analysis is None:
                continue
            intent = str(row.get('intent') or '')
            corrected_intent = str(row.get('corrected_intent') or '')
            confidence = float(row.get('confidence') or 0.0)
            review_status = str(row.get('review_status') or '')
            if (
                intent == 'fallback'
                or confidence < low_confidence_threshold
                or (corrected_intent and corrected_intent != intent)
                or review_status in {'unreviewed', 'rejected'}
            ):
                output.append({
                    'created_at': row.get('created_at'),
                    'user_text': row.get('user_text'),
                    'detected_lang': row.get('detected_lang'),
                    'intent': intent,
                    'confidence': confidence,
                    'response': row.get('response'),
                    'model_key': row.get('model_key'),
                    'review_status': review_status,
                    'corrected_intent': corrected_intent,
                    'admin_notes': row.get('admin_notes'),
                    'recommended_analysis_intent': analysis.intent,
                    'analysis_label': analysis.label,
                    'analysis_criteria': analysis.criteria,
                    'analysis_status': analysis.status,
                    'analysis_demographic_hint': analysis.demographic_hint,
                    'analysis_age_years': analysis.age_years,
                })
        return output

    def export_report_analysis_errors_to_csv(
        self,
        output_path: str | Path,
        *,
        limit: int = 1000,
        low_confidence_threshold: float = 0.55,
    ) -> Path:
        rows = self.fetch_report_analysis_error_rows(limit=limit, low_confidence_threshold=low_confidence_threshold)
        output = Path(output_path).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    'created_at',
                    'user_text',
                    'detected_lang',
                    'intent',
                    'confidence',
                    'response',
                    'model_key',
                    'review_status',
                    'corrected_intent',
                    'admin_notes',
                    'recommended_analysis_intent',
                    'analysis_label',
                    'analysis_criteria',
                    'analysis_status',
                    'analysis_demographic_hint',
                    'analysis_age_years',
                ],
            )
            writer.writeheader()
            writer.writerows(rows)
        return output

    def fetch_report_analysis_error_preview(
        self,
        *,
        limit: int = 25,
        low_confidence_threshold: float = 0.55,
    ) -> list[dict[str, Any]]:
        return self.fetch_report_analysis_error_rows(limit=limit, low_confidence_threshold=low_confidence_threshold)

    def authenticate_admin(self, username: str, password: str, *, session_ttl_hours: int = 12) -> dict[str, Any] | None:
        if self.backend == 'sqlite':
            with self._connect() as conn:
                conn.row_factory = sqlite3.Row
                self._cleanup_expired_sessions_sqlite(conn)
                row = conn.execute(
                    '''
                    SELECT id, username, password_salt, password_hash, must_change_password, is_active
                    FROM admin_users
                    WHERE username = ?
                    ''',
                    (username,),
                ).fetchone()
                if not row or not row['is_active']:
                    return None
                if not verify_password(password, str(row['password_salt']), str(row['password_hash'])):
                    return None
                token = generate_session_token()
                token_hash = hash_session_token(token)
                now = utc_now().isoformat()
                expires_at = session_expiry(session_ttl_hours).isoformat()
                conn.execute('DELETE FROM admin_sessions WHERE user_id = ?', (row['id'],))
                conn.execute(
                    '''
                    INSERT INTO admin_sessions (user_id, token_hash, created_at, expires_at)
                    VALUES (?, ?, ?, ?)
                    ''',
                    (row['id'], token_hash, now, expires_at),
                )
                conn.execute(
                    'UPDATE admin_users SET last_login_at = ?, updated_at = ? WHERE id = ?',
                    (now, now, row['id']),
                )
                return {
                    'token': token,
                    'username': str(row['username']),
                    'must_change_password': bool(row['must_change_password']),
                    'user_id': int(row['id']),
                }

        with self._connect() as conn, conn.cursor() as cur:
            self._cleanup_expired_sessions_postgres(cur)
            cur.execute(
                '''
                SELECT id, username, password_salt, password_hash, must_change_password, is_active
                FROM admin_users
                WHERE username = %(username)s
                ''',
                {'username': username},
            )
            row = cur.fetchone()
            if not row or not row.get('is_active'):
                return None
            if not verify_password(password, str(row['password_salt']), str(row['password_hash'])):
                return None
            token = generate_session_token()
            token_hash = hash_session_token(token)
            expires_at = session_expiry(session_ttl_hours)
            cur.execute('DELETE FROM admin_sessions WHERE user_id = %(user_id)s', {'user_id': row['id']})
            cur.execute(
                '''
                INSERT INTO admin_sessions (user_id, token_hash, expires_at)
                VALUES (%(user_id)s, %(token_hash)s, %(expires_at)s)
                ''',
                {'user_id': row['id'], 'token_hash': token_hash, 'expires_at': expires_at},
            )
            cur.execute(
                'UPDATE admin_users SET last_login_at = NOW(), updated_at = NOW() WHERE id = %(user_id)s',
                {'user_id': row['id']},
            )
            conn.commit()
            return {
                'token': token,
                'username': str(row['username']),
                'must_change_password': bool(row['must_change_password']),
                'user_id': int(row['id']),
            }

    def get_admin_by_session(self, token: str) -> AuthenticatedAdmin | None:
        token_hash = hash_session_token(token)
        if self.backend == 'sqlite':
            with self._connect() as conn:
                conn.row_factory = sqlite3.Row
                self._cleanup_expired_sessions_sqlite(conn)
                row = conn.execute(
                    '''
                    SELECT u.id, u.username, u.must_change_password
                    FROM admin_sessions s
                    JOIN admin_users u ON u.id = s.user_id
                    WHERE s.token_hash = ? AND u.is_active = 1
                    ''',
                    (token_hash,),
                ).fetchone()
                if not row:
                    return None
                return AuthenticatedAdmin(
                    user_id=int(row['id']),
                    username=str(row['username']),
                    must_change_password=bool(row['must_change_password']),
                )

        with self._connect() as conn, conn.cursor() as cur:
            self._cleanup_expired_sessions_postgres(cur)
            cur.execute(
                '''
                SELECT u.id, u.username, u.must_change_password
                FROM admin_sessions s
                JOIN admin_users u ON u.id = s.user_id
                WHERE s.token_hash = %(token_hash)s AND u.is_active = TRUE
                ''',
                {'token_hash': token_hash},
            )
            row = cur.fetchone()
            if not row:
                return None
            return AuthenticatedAdmin(
                user_id=int(row['id']),
                username=str(row['username']),
                must_change_password=bool(row['must_change_password']),
            )

    def revoke_admin_session(self, token: str) -> None:
        token_hash = hash_session_token(token)
        if self.backend == 'sqlite':
            with self._connect() as conn:
                conn.execute('DELETE FROM admin_sessions WHERE token_hash = ?', (token_hash,))
            return
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute('DELETE FROM admin_sessions WHERE token_hash = %(token_hash)s', {'token_hash': token_hash})
            conn.commit()

    def change_admin_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        salt, digest = hash_password(new_password)
        if self.backend == 'sqlite':
            with self._connect() as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    'SELECT password_salt, password_hash FROM admin_users WHERE id = ? AND is_active = 1',
                    (user_id,),
                ).fetchone()
                if not row or not verify_password(current_password, str(row['password_salt']), str(row['password_hash'])):
                    return False
                now = utc_now().isoformat()
                conn.execute(
                    '''
                    UPDATE admin_users
                    SET password_salt = ?, password_hash = ?, must_change_password = 0, updated_at = ?
                    WHERE id = ?
                    ''',
                    (salt, digest, now, user_id),
                )
                return True

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                'SELECT password_salt, password_hash FROM admin_users WHERE id = %(user_id)s AND is_active = TRUE',
                {'user_id': user_id},
            )
            row = cur.fetchone()
            if not row or not verify_password(current_password, str(row['password_salt']), str(row['password_hash'])):
                return False
            cur.execute(
                '''
                UPDATE admin_users
                SET password_salt = %(salt)s,
                    password_hash = %(digest)s,
                    must_change_password = FALSE,
                    updated_at = NOW()
                WHERE id = %(user_id)s
                ''',
                {'salt': salt, 'digest': digest, 'user_id': user_id},
            )
            conn.commit()
            return True

    def _cleanup_expired_sessions_sqlite(self, conn: sqlite3.Connection) -> None:
        conn.execute('DELETE FROM admin_sessions WHERE expires_at <= ?', (utc_now().isoformat(),))

    def _cleanup_expired_sessions_postgres(self, cur) -> None:
        cur.execute('DELETE FROM admin_sessions WHERE expires_at <= NOW()')
