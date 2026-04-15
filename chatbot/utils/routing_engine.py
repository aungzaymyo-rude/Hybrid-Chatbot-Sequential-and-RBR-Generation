from __future__ import annotations

from dataclasses import dataclass

from chatbot.utils.config import load_config
from chatbot.utils.entity_detection import EntityRule, detect_medical_entity
from chatbot.utils.response import render_response
from chatbot.utils.response_retriever import get_response_retriever


@dataclass(frozen=True)
class RouteResult:
    response: str
    source: str
    retrieval_intent: str | None = None
    retrieval_question: str | None = None
    entity_label: str | None = None


STATIC_INTENTS = {
    'greeting',
    'thanks',
    'goodbye',
    'capability_query',
    'out_of_scope',
    'unsafe_medical_request',
    'incomplete_query',
    'language_not_supported',
}

RETRIEVAL_INTENTS = {
    'cbc_info',
    'sample_collection',
    'help',
    'rbc_term',
    'wbc_term',
    'platelet_term',
    'differential_review',
    'coag_test',
    'blood_smear',
    'quality_control',
    'critical_value_reporting',
}


def resolve_route(
    intent: str,
    lang: str,
    *,
    text: str | None = None,
    config_path: str | None = None,
) -> RouteResult:
    if intent in STATIC_INTENTS:
        return RouteResult(response=render_response(intent, lang), source='static')

    entity: EntityRule | None = detect_medical_entity(text or '') if text else None
    retrieval_intent = intent
    retrieval_question = text

    if entity and intent in RETRIEVAL_INTENTS.union({'clarification', 'fallback'}):
        retrieval_intent = entity.intent
        retrieval_question = entity.canonical_question

    if retrieval_intent in RETRIEVAL_INTENTS and retrieval_question and config_path:
        cfg = load_config(config_path)
        retriever = get_response_retriever(
            knowledge_path=cfg['responses']['knowledge_path'],
            threshold=float(cfg['responses'].get('retrieval_threshold', 0.18)),
        )
        retrieved = retriever.retrieve(question=retrieval_question, intent=retrieval_intent)
        if retrieved:
            return RouteResult(
                response=retrieved,
                source='retrieval',
                retrieval_intent=retrieval_intent,
                retrieval_question=retrieval_question,
                entity_label=entity.label if entity else None,
            )

    return RouteResult(
        response=render_response(intent, lang),
        source='static',
        retrieval_intent=retrieval_intent if retrieval_intent != intent else None,
        retrieval_question=retrieval_question if retrieval_question != text else None,
        entity_label=entity.label if entity else None,
    )


def route_intent(
    intent: str,
    lang: str,
    *,
    text: str | None = None,
    config_path: str | None = None,
) -> str:
    return resolve_route(intent, lang, text=text, config_path=config_path).response
