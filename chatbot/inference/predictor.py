from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

import torch

from chatbot.models.sequential_intent import SequentialIntentClassifier, Vocabulary
from chatbot.utils.config import load_config
from chatbot.utils.language import detect_language
from chatbot.utils.preprocessing import normalize_text

GREETING_PATTERNS = (
    'hello',
    'hi',
    'hi there',
    'hey',
    'good morning',
    'good afternoon',
    'good evening',
    'greetings',
)

SMALL_TALK_PATTERNS = (
    'how are you',
    'how are u',
    'how r u',
    'how is it going',
    'how is going',
    'hows it going',
    "how's it going",
    'how are things',
    'whats up',
    "what's up",
    'how have you been',
    'hope you are well',
    'are you okay',
)

INCOMPLETE_PATTERNS = {
    'what',
    'what is',
    'how',
    'why',
    'which',
    'which one',
    'can you',
    'explain',
    '?',
    '???',
}

UNSAFE_KEYWORDS = {
    'inject',
    'injection',
    'treat',
    'treatment',
    'drug',
    'dose',
    'dosage',
    'prescribe',
    'prescription',
    'antibiotic',
    'medicine',
    'medication',
    'diagnose',
    'diagnosis',
    'therapy',
}


@dataclass
class Prediction:
    intent: str
    confidence: float
    language: str
    text: str


class IntentPredictor:
    def __init__(
        self,
        model_dir: Optional[str] = None,
        config_path: Optional[str] = None,
        device: Optional[str] = None,
    ) -> None:
        config_path = config_path or str(Path(__file__).resolve().parents[1] / 'config.yaml')
        cfg = load_config(config_path)
        model_dir = model_dir or cfg['training']['output_dir']
        self.threshold = float(cfg['inference']['threshold'])
        self.max_length = int(cfg['model'].get('max_length', 64))

        self.model_dir = Path(model_dir).resolve()
        self.metadata = self._load_json(self.model_dir / 'model_metadata.json', default={})
        self.model_type = self.metadata.get('model_type', 'sequential')

        if device is None or device == 'auto':
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.device = torch.device(device)

        self.label_map = self._load_label_map(self.model_dir)
        self.vocab = self._load_vocab(self.model_dir)
        self.model = self._load_sequential_model()
        self.model.to(self.device)
        self.model.eval()

    def _load_json(self, path: Path, default: Dict[str, object]) -> Dict[str, object]:
        if not path.exists():
            return dict(default)
        with path.open('r', encoding='utf-8') as handle:
            return json.load(handle)

    def _load_label_map(self, model_dir: Path) -> Dict[int, str]:
        label_path = model_dir / 'label_map.json'
        if not label_path.exists():
            raise FileNotFoundError('label_map.json not found in model directory')
        with label_path.open('r', encoding='utf-8') as handle:
            raw = json.load(handle)
        return {int(value): key for key, value in raw.items()}

    def _load_vocab(self, model_dir: Path) -> Vocabulary:
        vocab_path = model_dir / 'vocab.json'
        if not vocab_path.exists():
            raise FileNotFoundError('vocab.json not found in model directory')
        with vocab_path.open('r', encoding='utf-8') as handle:
            payload = json.load(handle)
        itos = payload['itos']
        stoi = {token: idx for idx, token in enumerate(itos)}
        return Vocabulary(stoi=stoi, itos=itos, max_length=int(self.metadata.get('max_length', self.max_length)))

    def _load_sequential_model(self) -> SequentialIntentClassifier:
        model = SequentialIntentClassifier(
            vocab_size=len(self.vocab.itos),
            embedding_dim=int(self.metadata.get('embedding_dim', 128)),
            hidden_dim=int(self.metadata.get('hidden_dim', 128)),
            num_classes=len(self.label_map),
            architecture=str(self.metadata.get('architecture', 'bilstm')),
            num_layers=int(self.metadata.get('num_layers', 1)),
            dropout=float(self.metadata.get('dropout', 0.2)),
            padding_idx=self.vocab.pad_id,
        )
        state = torch.load(self.model_dir / 'model.pt', map_location='cpu')
        model.load_state_dict(state)
        return model

    @staticmethod
    def postprocess_logits(
        logits: torch.Tensor,
        id2label: Dict[int, str],
        threshold: float,
    ) -> Tuple[str, float]:
        probs = torch.softmax(logits, dim=-1)
        conf, idx = torch.max(probs, dim=-1)
        intent = id2label[int(idx.item())]
        confidence = float(conf.item())
        if confidence < threshold:
            intent = 'fallback'
        return intent, confidence

    @torch.no_grad()
    def predict(self, text: str, lang: Optional[str] = None) -> Prediction:
        cleaned = normalize_text(text)
        if not cleaned:
            return Prediction(intent='fallback', confidence=0.0, language=lang or 'unknown', text=text)

        language = lang or detect_language(cleaned)
        if language != 'en':
            return Prediction(intent='language_not_supported', confidence=1.0, language=language, text=text)

        for pattern in GREETING_PATTERNS:
            if cleaned == pattern or cleaned.startswith(pattern + ' '):
                return Prediction(intent='greeting', confidence=1.0, language=language, text=text)

        for pattern in SMALL_TALK_PATTERNS:
            if cleaned == pattern or cleaned.startswith(pattern + ' '):
                return Prediction(intent='small_talk', confidence=1.0, language=language, text=text)

        if cleaned in INCOMPLETE_PATTERNS or (len(cleaned.split()) <= 2 and cleaned.split()[0] in {'what', 'how', 'why', 'which'}):
            return Prediction(intent='incomplete_query', confidence=1.0, language=language, text=text)

        tokens = set(cleaned.split())
        if tokens & UNSAFE_KEYWORDS:
            return Prediction(intent='unsafe_medical_request', confidence=1.0, language=language, text=text)

        encoded = torch.tensor([self.vocab.encode(cleaned)], dtype=torch.long, device=self.device)
        lengths = torch.tensor([encoded.shape[1]], dtype=torch.long, device=self.device)
        logits = self.model(encoded, lengths)[0]
        intent, confidence = self.postprocess_logits(logits, self.label_map, self.threshold)
        return Prediction(intent=intent, confidence=confidence, language=language, text=text)
