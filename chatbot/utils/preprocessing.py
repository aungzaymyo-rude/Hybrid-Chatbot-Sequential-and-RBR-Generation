from __future__ import annotations

import re
from typing import List


_control_chars = re.compile(r"[\x00-\x1F\x7F]")
_whitespace = re.compile(r"\s+")
_token_pattern = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?")


def normalize_text(text: str) -> str:
    if not text:
        return ""
    cleaned = _control_chars.sub(" ", text)
    cleaned = cleaned.strip().lower()
    cleaned = _whitespace.sub(" ", cleaned)
    return cleaned


def tokenize_text(text: str) -> List[str]:
    return _token_pattern.findall(normalize_text(text))
