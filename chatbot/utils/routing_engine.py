from __future__ import annotations

from chatbot.utils.config import load_config
from chatbot.utils.entity_detection import detect_medical_entity
from chatbot.utils.response import render_response
from chatbot.utils.response_retriever import get_response_retriever


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
    'coag_test',
    'blood_smear',
}


def route_intent(
    intent: str,
    lang: str,
    *,
    text: str | None = None,
    config_path: str | None = None,
) -> str:
    if intent in STATIC_INTENTS:
        return render_response(intent, lang)

    entity = detect_medical_entity(text or '') if text else None
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
            return retrieved

    return render_response(intent, lang)
