from __future__ import annotations

from chatbot.utils.entity_detection import detect_medical_entity


def test_detect_medical_entity_maps_rbc_terms():
    detected = detect_medical_entity('Can you explain MCV for me?')
    assert detected is not None
    assert detected.intent == 'rbc_term'
    assert detected.canonical_question == 'What is MCV?'


def test_detect_medical_entity_maps_coag_terms():
    detected = detect_medical_entity('What does aPTT mean?')
    assert detected is not None
    assert detected.intent == 'coag_test'
    assert detected.canonical_question == 'What is aPTT?'
