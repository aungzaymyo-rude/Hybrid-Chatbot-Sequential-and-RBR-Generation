from __future__ import annotations

from fastapi.testclient import TestClient

from chatbot.api.main import app, get_chat_store, get_registry
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
    app.dependency_overrides[get_registry] = lambda: DummyRegistry()
    app.dependency_overrides[get_chat_store] = lambda: DummyChatStore()
    client = TestClient(app)
    resp = client.get('/admin/api/export-report-analysis-errors')
    assert resp.status_code == 200
    assert 'text/csv' in resp.headers['content-type']
    assert 'WBC is 13.7' in resp.text
    app.dependency_overrides.clear()


def test_report_analysis_preview_endpoint_returns_rows():
    app.dependency_overrides[get_registry] = lambda: DummyRegistry()
    app.dependency_overrides[get_chat_store] = lambda: DummyChatStore()
    client = TestClient(app)
    resp = client.get('/admin/api/report-analysis-preview')
    assert resp.status_code == 200
    payload = resp.json()
    assert payload['rows'][0]['recommended_analysis_intent'] == 'report_numeric_result_analysis'
    app.dependency_overrides.clear()
