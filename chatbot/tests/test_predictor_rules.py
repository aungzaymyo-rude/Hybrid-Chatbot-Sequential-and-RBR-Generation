from __future__ import annotations

from chatbot.inference.predictor import GREETING_PATTERNS, INCOMPLETE_PATTERNS, UNSAFE_KEYWORDS


def test_incomplete_patterns_cover_basic_short_queries():
    assert "what is" in INCOMPLETE_PATTERNS
    assert "how" in INCOMPLETE_PATTERNS
    assert "???" in INCOMPLETE_PATTERNS


def test_unsafe_keywords_cover_treatment_language():
    assert "inject" in UNSAFE_KEYWORDS
    assert "treat" in UNSAFE_KEYWORDS
    assert "prescribe" in UNSAFE_KEYWORDS


def test_greeting_patterns_still_include_basic_greetings():
    assert "hello" in GREETING_PATTERNS
    assert "hi" in GREETING_PATTERNS
