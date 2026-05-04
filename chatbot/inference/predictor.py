from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import torch

from chatbot.models.sequential_intent import SequentialIntentClassifier, Vocabulary
from chatbot.utils.config import load_config
from chatbot.utils.language import detect_language
from chatbot.utils.preprocessing import normalize_text
from chatbot.utils.report_analysis import analyze_report_input, extract_age_years

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


@dataclass
class RuleTrace:
    intent: str
    matched_pattern: str
    stage: str


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
        self.available_intents = set(self.label_map.values())

    def _load_json(self, path: Path, default: Dict[str, object]) -> Dict[str, object]:
        if not path.exists():
            return dict(default)
        with path.open('r', encoding='utf-8') as handle:
            return json.load(handle)

    def _load_label_map(self, model_dir: Path) -> Dict[int, str]:
        label_path = model_dir / 'label_map.json'
        if not label_path.exists():
            raise FileNotFoundError(f'label_map.json not found in model directory: {model_dir}')
        with label_path.open('r', encoding='utf-8') as handle:
            raw = json.load(handle)
        return {int(value): key for key, value in raw.items()}

    def _load_vocab(self, model_dir: Path) -> Vocabulary:
        vocab_path = model_dir / 'vocab.json'
        if not vocab_path.exists():
            raise FileNotFoundError(f'vocab.json not found in model directory: {model_dir}')
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

    def _match_rule(self, cleaned: str) -> RuleTrace | None:
        for pattern in GREETING_PATTERNS:
            if cleaned == pattern or cleaned.startswith(pattern + ' '):
                return RuleTrace(intent='greeting', matched_pattern=pattern, stage='greeting_rule')

        for pattern in SMALL_TALK_PATTERNS:
            if cleaned == pattern or cleaned.startswith(pattern + ' '):
                return RuleTrace(intent='small_talk', matched_pattern=pattern, stage='small_talk_rule')

        if cleaned in INCOMPLETE_PATTERNS or (len(cleaned.split()) <= 2 and cleaned.split()[0] in {'what', 'how', 'why', 'which'}):
            return RuleTrace(intent='incomplete_query', matched_pattern=cleaned, stage='incomplete_rule')

        tokens = set(cleaned.split())
        matched_unsafe = sorted(tokens & UNSAFE_KEYWORDS)
        if matched_unsafe:
            return RuleTrace(intent='unsafe_medical_request', matched_pattern=', '.join(matched_unsafe), stage='unsafe_rule')

        return None

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

    def _apply_domain_assist(self, cleaned: str, intent: str, confidence: float) -> Tuple[str, float]:
        analysis = analyze_report_input(cleaned)
        if intent in {'report_numeric_result_analysis', 'report_flag_result_analysis'} and analysis is None:
            if extract_age_years(cleaned) is not None:
                return 'incomplete_query', max(confidence, 0.80)
        if (
            analysis is not None
            and analysis.intent in self.available_intents
            and intent in {
                'fallback',
                'cbc_info',
                'cbc_result_parameter',
                'cbc_flag_explanation',
                'anemia_related_term',
                'platelet_abnormality',
                'differential_result_explanation',
                'report_structure_help',
            }
        ):
            return analysis.intent, max(confidence, 0.85)
        if intent != 'fallback':
            return intent, confidence
        if analysis is None or analysis.intent not in self.available_intents:
            return intent, confidence
        return analysis.intent, max(confidence, 0.80)

    @torch.no_grad()
    def trace(self, text: str, lang: Optional[str] = None, top_k: int = 5) -> Dict[str, object]:
        cleaned = normalize_text(text)
        tokens = cleaned.split() if cleaned else []
        token_ids = self.vocab.encode(cleaned) if cleaned else []
        token_map = [
            {
                'token': token,
                'id': token_ids[idx] if idx < len(token_ids) else self.vocab.unk_id,
                'known': token in self.vocab.stoi,
            }
            for idx, token in enumerate(tokens[: self.vocab.max_length])
        ]

        if not cleaned:
            return {
                'raw_text': text,
                'normalized_text': cleaned,
                'tokens': tokens,
                'token_map': token_map,
                'language': lang or 'unknown',
                'rule_match': {'stage': 'empty_input', 'intent': 'fallback', 'matched_pattern': ''},
                'threshold': self.threshold,
                'top_predictions': [],
                'final_intent': 'fallback',
                'final_confidence': 0.0,
            }

        language = lang or detect_language(cleaned)
        if language != 'en':
            return {
                'raw_text': text,
                'normalized_text': cleaned,
                'tokens': tokens,
                'token_map': token_map,
                'language': language,
                'rule_match': {'stage': 'language_gate', 'intent': 'language_not_supported', 'matched_pattern': language},
                'threshold': self.threshold,
                'top_predictions': [],
                'final_intent': 'language_not_supported',
                'final_confidence': 1.0,
            }

        rule_match = self._match_rule(cleaned)
        if rule_match is not None:
            return {
                'raw_text': text,
                'normalized_text': cleaned,
                'tokens': tokens,
                'token_map': token_map,
                'language': language,
                'rule_match': {
                    'stage': rule_match.stage,
                    'intent': rule_match.intent,
                    'matched_pattern': rule_match.matched_pattern,
                },
                'threshold': self.threshold,
                'top_predictions': [],
                'final_intent': rule_match.intent,
                'final_confidence': 1.0,
            }

        encoded_ids = token_ids or [self.vocab.unk_id]
        encoded = torch.tensor([encoded_ids], dtype=torch.long, device=self.device)
        lengths = torch.tensor([len(encoded_ids)], dtype=torch.long, device=self.device)
        logits = self.model(encoded, lengths)[0]
        probs = torch.softmax(logits, dim=-1)
        sorted_probs, sorted_indices = torch.sort(probs, descending=True)
        top_predictions: List[Dict[str, object]] = []
        for score, idx in zip(sorted_probs[:top_k], sorted_indices[:top_k]):
            top_predictions.append(
                {
                    'intent': self.label_map[int(idx.item())],
                    'confidence': float(score.item()),
                }
            )
        final_intent, final_confidence = self.postprocess_logits(logits, self.label_map, self.threshold)
        assisted_intent, assisted_confidence = self._apply_domain_assist(cleaned, final_intent, final_confidence)
        return {
            'raw_text': text,
            'normalized_text': cleaned,
            'tokens': tokens,
            'token_map': token_map,
            'language': language,
            'rule_match': None,
            'threshold': self.threshold,
            'top_predictions': top_predictions,
            'final_intent': assisted_intent,
            'final_confidence': assisted_confidence,
            'domain_assist': {
                'applied': assisted_intent != final_intent,
                'assisted_intent': assisted_intent if assisted_intent != final_intent else None,
                'base_intent': final_intent,
                'base_confidence': final_confidence,
            },
        }

    @torch.no_grad()
    def predict(self, text: str, lang: Optional[str] = None) -> Prediction:
        cleaned = normalize_text(text)
        if not cleaned:
            return Prediction(intent='fallback', confidence=0.0, language=lang or 'unknown', text=text)

        language = lang or detect_language(cleaned)
        if language != 'en':
            return Prediction(intent='language_not_supported', confidence=1.0, language=language, text=text)

        rule_match = self._match_rule(cleaned)
        if rule_match is not None:
            return Prediction(intent=rule_match.intent, confidence=1.0, language=language, text=text)

        encoded = torch.tensor([self.vocab.encode(cleaned)], dtype=torch.long, device=self.device)
        lengths = torch.tensor([encoded.shape[1]], dtype=torch.long, device=self.device)
        logits = self.model(encoded, lengths)[0]
        intent, confidence = self.postprocess_logits(logits, self.label_map, self.threshold)
        intent, confidence = self._apply_domain_assist(cleaned, intent, confidence)
        return Prediction(intent=intent, confidence=confidence, language=language, text=text)
