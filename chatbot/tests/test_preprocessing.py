from __future__ import annotations

from chatbot.utils.preprocessing import normalize_text


def test_normalize_text_basic():
    text = '  Hello\nWorld  '
    assert normalize_text(text) == 'hello world'


def test_normalize_text_empty():
    assert normalize_text('') == ''
