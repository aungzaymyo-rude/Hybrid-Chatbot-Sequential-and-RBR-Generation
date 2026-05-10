from __future__ import annotations

from fastapi.testclient import TestClient

from chatbot.api.main import app, get_chat_store, get_registry
from chatbot.utils.admin_auth import AuthenticatedAdmin
from chatbot.inference.predictor import Prediction


class DummyPredictor:
    def predict(self, text: str, lang: str | None = None) -> Prediction:
        return Prediction(intent='greeting', confidence=0.99, language=lang or 'en', text=text)


class DummyRegistry:
    config = {'model_default_key': 'general'}

    def get_predictor(self, model_key: str | None = None, model_dir: str | None = None) -> DummyPredictor:
        return DummyPredictor()

    def resolve_model_info(self, model_key: str | None = None, model_dir: str | None = None) -> dict:
        return {'path': 'chatbot/models/intent_general', 'version': 'test'}


class DummyChatStore:
    def authenticate_admin(self, username: str, password: str, *, session_ttl_hours: int = 12):
        if username == 'admin' and password == 'admin':
            return {'token': 'test-token', 'username': 'admin', 'must_change_password': True, 'user_id': 1}
        return None

    def get_admin_by_session(self, token: str):
        if token == 'test-token':
            return AuthenticatedAdmin(user_id=1, username='admin', must_change_password=True)
        return None

    def revoke_admin_session(self, token: str) -> None:
        return None

    def change_admin_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        return current_password == 'admin' and len(new_password) >= 8

    def log_chat(self, **_: object) -> None:
        return None

    def export_report_analysis_errors_to_csv(self, output_path, **_: object):
        path = output_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('user_text,intent\nWBC is 13.7,fallback\n', encoding='utf-8')
        return path

    def fetch_report_analysis_error_preview(self, **_: object):
        return [
            {
                'user_text': 'WBC is 13.7',
                'intent': 'fallback',
                'confidence': 0.21,
                'recommended_analysis_intent': 'report_numeric_result_analysis',
                'analysis_label': 'WBC',
            }
        ]


def admin_client() -> TestClient:
    app.dependency_overrides[get_registry] = lambda: DummyRegistry()
    app.dependency_overrides[get_chat_store] = lambda: DummyChatStore()
    client = TestClient(app)
    login = client.post('/admin/api/login', json={'username': 'admin', 'password': 'admin'})
    assert login.status_code == 200
    return client


def test_chat_endpoint_returns_response():
    app.dependency_overrides[get_registry] = lambda: DummyRegistry()
    app.dependency_overrides[get_chat_store] = lambda: DummyChatStore()
    client = TestClient(app)
    resp = client.post('/chat', json={'text': 'Hello'})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload['intent'] == 'greeting'
    assert payload['response']
    assert payload['support_note'] is None
    app.dependency_overrides.clear()


def test_export_report_analysis_errors_endpoint_returns_csv():
    client = admin_client()
    resp = client.get('/admin/api/export-report-analysis-errors')
    assert resp.status_code == 200
    assert 'text/csv' in resp.headers['content-type']
    assert 'WBC is 13.7' in resp.text
    app.dependency_overrides.clear()


def test_report_analysis_preview_endpoint_returns_rows():
    client = admin_client()
    resp = client.get('/admin/api/report-analysis-preview')
    assert resp.status_code == 200
    payload = resp.json()
    assert payload['rows'][0]['recommended_analysis_intent'] == 'report_numeric_result_analysis'
    app.dependency_overrides.clear()


def test_admin_session_requires_login():
    app.dependency_overrides[get_registry] = lambda: DummyRegistry()
    app.dependency_overrides[get_chat_store] = lambda: DummyChatStore()
    client = TestClient(app)
    resp = client.get('/admin/api/session')
    assert resp.status_code == 401
    app.dependency_overrides.clear()


def test_admin_change_password_endpoint():
    client = admin_client()
    resp = client.post('/admin/api/change-password', json={'current_password': 'admin', 'new_password': 'newsecure123'})
    assert resp.status_code == 200
    assert resp.json()['status'] == 'password_updated'
    app.dependency_overrides.clear()
