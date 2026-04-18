from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass(frozen=True)
class KnowledgeEntry:
    intent: str
    question: str
    answer: str


class ResponseRetriever:
    def __init__(self, knowledge_path: str, threshold: float = 0.18) -> None:
        self.knowledge_path = Path(knowledge_path)
        self.threshold = threshold
        self.entries = self._load_entries(self.knowledge_path)
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), lowercase=True)
        self.matrix = self.vectorizer.fit_transform([entry.question for entry in self.entries])

    @staticmethod
    def _load_entries(path: Path) -> List[KnowledgeEntry]:
        entries: List[KnowledgeEntry] = []
        with path.open('r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                entries.append(
                    KnowledgeEntry(
                        intent=payload['intent'],
                        question=payload['question'],
                        answer=payload['answer'],
                    )
                )
        if not entries:
            raise ValueError(f'No knowledge entries found in {path}')
        return entries

    def retrieve(self, question: str, intent: str) -> Optional[str]:
        ranked = self.rank(question=question, intent=intent, limit=1)
        if not ranked:
            return None
        top = ranked[0]
        if float(top['score']) < self.threshold:
            return None
        return str(top['answer'])

    def rank(self, question: str, intent: str, limit: int = 5) -> List[Dict[str, object]]:
        query = self.vectorizer.transform([question])
        scores = cosine_similarity(query, self.matrix)[0]

        ranked: List[Dict[str, object]] = []
        for idx, entry in enumerate(self.entries):
            if entry.intent != intent:
                continue
            ranked.append(
                {
                    'intent': entry.intent,
                    'question': entry.question,
                    'answer': entry.answer,
                    'score': float(scores[idx]),
                }
            )
        ranked.sort(key=lambda item: float(item['score']), reverse=True)
        return ranked[:limit]


_CACHE: Dict[str, ResponseRetriever] = {}


def get_response_retriever(knowledge_path: str, threshold: float) -> ResponseRetriever:
    cache_key = f'{knowledge_path}:{threshold}'
    if cache_key not in _CACHE:
        _CACHE[cache_key] = ResponseRetriever(knowledge_path=knowledge_path, threshold=threshold)
    return _CACHE[cache_key]
