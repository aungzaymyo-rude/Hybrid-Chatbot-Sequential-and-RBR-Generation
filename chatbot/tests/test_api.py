from __future__ import annotations

from fastapi.testclient import TestClient

from chatbot.api.main import app, get_predictor
from chatbot.inference.predictor import Prediction


class DummyPredictor:
    def predict(self, text: str, lang: str | None = None) -> Prediction:
        return Prediction(intent='greeting', confidence=0.99, language=lang or 'en', text=text)


def test_chat_endpoint_returns_response():
    app.dependency_overrides[get_predictor] = lambda: DummyPredictor()
    client = TestClient(app)
    resp = client.post('/chat', json={'text': 'Hello'})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload['intent'] == 'greeting'
    assert payload['response']
    app.dependency_overrides.clear()
