from __future__ import annotations

from typing import Any

from chatbot.inference.registry import ModelRegistry
from chatbot.utils.config import load_config
from chatbot.utils.entity_detection import detect_medical_entity
from chatbot.utils.model_advisory import recommend_model_switch
from chatbot.utils.response import render_response
from chatbot.utils.response_retriever import get_response_retriever
from chatbot.utils.routing_engine import ENTITY_OVERRIDE_ALLOWED_INTENTS, ENTITY_OVERRIDE_FIRST_INTENTS, RETRIEVAL_INTENTS, STATIC_INTENTS, resolve_route


def build_trace(text: str, *, model_key: str | None, config_path: str) -> dict[str, Any]:
    cfg = load_config(config_path)
    registry = ModelRegistry(config_path)
    requested_model_key = registry._normalize_model_key(model_key) or registry.config.get('model_default_key')
    suggested_model_key, advisory_message = recommend_model_switch(text, requested_model_key)
    effective_model_key = suggested_model_key or requested_model_key

    predictor = registry.get_predictor(model_key=effective_model_key)
    prediction_trace = predictor.trace(text)
    prediction = predictor.predict(text)
    entity = detect_medical_entity(text)
    route = resolve_route(prediction.intent, prediction.language, text=prediction.text, config_path=config_path)

    retrieval_candidates: list[dict[str, Any]] = []
    direct_candidates: list[dict[str, Any]] = []
    entity_candidates: list[dict[str, Any]] = []
    route_explanation = 'Static response path'
    if prediction.intent not in STATIC_INTENTS:
        retriever = get_response_retriever(
            knowledge_path=cfg['responses']['knowledge_path'],
            threshold=float(cfg['responses'].get('retrieval_threshold', 0.18)),
        )
        if text and prediction.intent in RETRIEVAL_INTENTS:
            direct_candidates = retriever.rank(question=text, intent=prediction.intent, limit=5)
        if entity and prediction.intent in ENTITY_OVERRIDE_FIRST_INTENTS.union(ENTITY_OVERRIDE_ALLOWED_INTENTS):
            entity_candidates = retriever.rank(question=entity.canonical_question, intent=entity.intent, limit=5)

        if route.source == 'retrieval':
            retrieval_candidates = direct_candidates if route.retrieval_question == text else entity_candidates
            if route.retrieval_question == text:
                route_explanation = 'Predicted intent retrieved directly from the user question.'
            else:
                route_explanation = 'Entity detection refined the retrieval target after prediction.'
        else:
            route_explanation = 'No retrieval candidate passed threshold, so the static response template was used.'

    static_preview = render_response(prediction.intent, prediction.language)
    model_info = registry.resolve_model_info(effective_model_key, None)
    return {
        'input': {
            'text': text,
            'requested_model_key': requested_model_key,
            'effective_model_key': effective_model_key,
            'auto_switched': bool(suggested_model_key and suggested_model_key != requested_model_key),
            'advisory_message': advisory_message,
            'model_version': model_info.get('version') or '',
        },
        'preprocessing': {
            'normalized_text': prediction_trace['normalized_text'],
            'tokens': prediction_trace['tokens'],
            'token_map': prediction_trace['token_map'],
            'language': prediction_trace['language'],
        },
        'rules': {
            'matched': prediction_trace['rule_match'] is not None,
            'details': prediction_trace['rule_match'],
        },
        'classifier': {
            'threshold': prediction_trace['threshold'],
            'top_predictions': prediction_trace['top_predictions'],
            'final_intent': prediction.intent,
            'final_confidence': prediction.confidence,
        },
        'entity_detection': {
            'matched': entity is not None,
            'label': entity.label if entity else '',
            'intent': entity.intent if entity else '',
            'canonical_question': entity.canonical_question if entity else '',
        },
        'retrieval': {
            'threshold': float(cfg['responses'].get('retrieval_threshold', 0.18)),
            'direct_candidates': direct_candidates,
            'entity_candidates': entity_candidates,
            'selected_candidates': retrieval_candidates,
        },
        'route': {
            'source': route.source,
            'retrieval_intent': route.retrieval_intent,
            'retrieval_question': route.retrieval_question,
            'entity_label': route.entity_label,
            'explanation': route_explanation,
            'static_preview': static_preview,
            'final_response': route.response,
        },
    }
