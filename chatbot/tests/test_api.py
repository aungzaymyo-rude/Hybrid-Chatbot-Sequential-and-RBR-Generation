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


def test_chat_endpoint_returns_response():
    app.dependency_overrides[get_registry] = lambda: DummyRegistry()
    app.dependency_overrides[get_chat_store] = lambda: DummyChatStore()
    client = TestClient(app)
    resp = client.post('/chat', json={'text': 'Hello'})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload['intent'] == 'greeting'
    assert payload['response']
    app.dependency_overrides.clear()
