from __future__ import annotations

import torch

from chatbot.inference.predictor import IntentPredictor


def test_postprocess_logits_returns_intent():
    logits = torch.tensor([0.1, 2.0])
    id2label = {0: 'greeting', 1: 'help'}
    intent, confidence = IntentPredictor.postprocess_logits(logits, id2label, threshold=0.5)
    assert intent == 'help'
    assert 0.0 <= confidence <= 1.0


def test_postprocess_logits_fallback():
    logits = torch.tensor([0.1, 0.2])
    id2label = {0: 'greeting', 1: 'help'}
    intent, _ = IntentPredictor.postprocess_logits(logits, id2label, threshold=0.9)
    assert intent == 'fallback'
