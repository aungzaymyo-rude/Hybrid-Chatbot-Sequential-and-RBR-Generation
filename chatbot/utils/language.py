from __future__ import annotations

import os
import re
from pathlib import Path

try:
    import fasttext
except Exception:  # pragma: no cover - optional dependency
    fasttext = None

_MODEL = None
_DEFAULT_MODEL_PATH = Path(__file__).resolve().parents[1] / 'data' / 'lid.176.ftz'


def _load_model() -> object | None:
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    if fasttext is None:
        return None
    model_path = os.getenv('FASTTEXT_MODEL_PATH', str(_DEFAULT_MODEL_PATH))
    model_file = Path(model_path)
    if not model_file.exists():
        return None
    _MODEL = fasttext.load_model(str(model_file))
    return _MODEL


def detect_language(text: str) -> str:
    cleaned = (text or '').strip()
    if not cleaned:
        return 'unknown'

    # Script-based hints for higher accuracy on short inputs.
    if re.search(r'[\u1000-\u109F]', cleaned):
        return 'my'
    if re.search(r'[\u3040-\u30FF\u4E00-\u9FFF]', cleaned):
        return 'ja'

    try:
        model = _load_model()
        if model is not None:
            labels, _ = model.predict(cleaned, k=1)
            lang = labels[0].replace('__label__', '') if labels else 'unknown'
        else:
            lang = 'unknown'
    except Exception:
        lang = 'unknown'

    supported = {'en', 'my', 'es', 'fr', 'ja'}
    if lang in supported:
        return lang

    # Short ASCII text often gets misclassified; default to English.
    if re.fullmatch(r'[\x00-\x7F]+', cleaned) and len(cleaned) <= 20:
        return 'en'

    # If fastText isn't available, fall back to ASCII-based English detection.
    if lang == 'unknown' and re.fullmatch(r'[\x00-\x7F]+', cleaned):
        return 'en'

    return lang
