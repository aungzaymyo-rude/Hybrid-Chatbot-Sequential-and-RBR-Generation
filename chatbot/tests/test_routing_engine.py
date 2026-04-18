from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from chatbot.utils.chat_store import ChatHistoryStore
from chatbot.utils.routing_engine import route_intent


CONFIG_PATH = str(Path(__file__).resolve().parents[1] / 'config.yaml')


def test_route_intent_uses_retrieval_for_cbc_question():
    response = route_intent(
        'cbc_info',
        'en',
        text='What is RBC count?',
        config_path=CONFIG_PATH,
    )
    assert 'red blood cells' in response.lower()


def test_route_intent_uses_static_response_for_capability_query():
    response = route_intent(
        'capability_query',
        'en',
        text='What can you do?',
        config_path=CONFIG_PATH,
    )
    assert 'hematology lab questions' in response.lower()


def test_route_intent_uses_static_response_for_unsafe_request():
    response = route_intent(
        'unsafe_medical_request',
        'en',
        text='How do I inject a patient?',
        config_path=CONFIG_PATH,
    )
    assert 'cannot provide treatment' in response.lower()


def test_route_intent_uses_entity_detection_to_refine_cbc_answer():
    response = route_intent(
        'cbc_info',
        'en',
        text='What is MCV?',
        config_path=CONFIG_PATH,
    )
    assert 'mean corpuscular volume' in response.lower()


def test_route_intent_uses_entity_detection_for_help_question():
    response = route_intent(
        'help',
        'en',
        text='Can you explain aPTT?',
        config_path=CONFIG_PATH,
    )
    assert 'activated partial thromboplastin time' in response.lower()


def test_route_intent_prioritizes_sample_collection_for_cbc_tube_question():
    response = route_intent(
        'sample_collection',
        'en',
        text='Which tube is used for CBC?',
        config_path=CONFIG_PATH,
    )
    assert 'edta' in response.lower()


def test_route_intent_returns_rejection_criteria_for_cbc_sample_question():
    response = route_intent(
        'sample_collection',
        'en',
        text='What are the rejection criteria for a CBC sample?',
        config_path=CONFIG_PATH,
    )
    assert 'rejection criteria' in response.lower()
    assert 'wrong tube' in response.lower()


def test_route_intent_returns_clotted_sample_guidance():
    response = route_intent(
        'sample_collection',
        'en',
        text='What should I do with a clotted EDTA sample?',
        config_path=CONFIG_PATH,
    )
    assert 'clotted edta sample' in response.lower() or 'clotted' in response.lower()
    assert 'recollect' in response.lower() or 'request recollection' in response.lower()


def test_route_intent_returns_cbc_stability_guidance():
    response = route_intent(
        'sample_collection',
        'en',
        text='How long is a CBC sample stable?',
        config_path=CONFIG_PATH,
    )
    assert 'stability' in response.lower()
    assert 'validated' in response.lower() or 'sop' in response.lower()


def test_chat_store_logs_records():
    db_path = Path(__file__).resolve().parent / f'chat_history_test_{uuid4().hex}.db'
    store = ChatHistoryStore(str(db_path))
    store.log_chat(
        user_text='What is a CBC?',
        detected_lang='en',
        intent='cbc_info',
        confidence=0.9,
        response='A CBC is a routine hematology test.',
        model_key='default',
        model_path='models/intent',
        model_version='v1',
    )
    assert db_path.exists()
