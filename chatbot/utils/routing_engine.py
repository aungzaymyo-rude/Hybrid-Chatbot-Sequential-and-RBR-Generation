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
    'small_talk',
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
    'cbc_result_parameter',
    'cbc_flag_explanation',
    'anemia_related_term',
    'platelet_abnormality',
    'differential_result_explanation',
    'report_structure_help',
}

ENTITY_OVERRIDE_FIRST_INTENTS = {
    'fallback',
    'help',
    'clarification',
}

ENTITY_OVERRIDE_ALLOWED_INTENTS = ENTITY_OVERRIDE_FIRST_INTENTS.union({'cbc_info'})


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
    if config_path:
        cfg = load_config(config_path)
        retriever = get_response_retriever(
            knowledge_path=cfg['responses']['knowledge_path'],
            threshold=float(cfg['responses'].get('retrieval_threshold', 0.18)),
        )

        # For broad or weak intents, let entity detection refine the retrieval target first.
        if entity and intent in ENTITY_OVERRIDE_FIRST_INTENTS:
            retrieved = retriever.retrieve(question=entity.canonical_question, intent=entity.intent)
            if retrieved:
                return RouteResult(
                    response=retrieved,
                    source='retrieval',
                    retrieval_intent=entity.intent,
                    retrieval_question=entity.canonical_question,
                    entity_label=entity.label,
                )

        # For specific operational/domain intents, stay inside the predicted intent first.
        if intent in RETRIEVAL_INTENTS and text:
            retrieved = retriever.retrieve(question=text, intent=intent)
            if retrieved:
                return RouteResult(
                    response=retrieved,
                    source='retrieval',
                    retrieval_intent=intent,
                    retrieval_question=text,
                    entity_label=entity.label if entity else None,
                )

        # Broad informational intents can still refine through entity detection if direct retrieval missed.
        if entity and intent in ENTITY_OVERRIDE_ALLOWED_INTENTS:
            retrieved = retriever.retrieve(question=entity.canonical_question, intent=entity.intent)
            if retrieved:
                return RouteResult(
                    response=retrieved,
                    source='retrieval',
                    retrieval_intent=entity.intent,
                    retrieval_question=entity.canonical_question,
                    entity_label=entity.label,
                )

    return RouteResult(
        response=render_response(intent, lang),
        source='static',
        retrieval_intent=entity.intent if entity and intent in ENTITY_OVERRIDE_ALLOWED_INTENTS else None,
        retrieval_question=entity.canonical_question if entity and intent in ENTITY_OVERRIDE_ALLOWED_INTENTS else None,
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
