from __future__ import annotations

from typing import Optional, Tuple

from chatbot.utils.entity_detection import detect_medical_entity
from chatbot.utils.preprocessing import normalize_text

GENERAL_MODEL_KEY = 'general'
REPORT_MODEL_KEY = 'report'

REPORT_FOCUSED_INTENTS = {
    'cbc_result_parameter',
    'cbc_flag_explanation',
    'anemia_related_term',
    'platelet_abnormality',
    'differential_result_explanation',
    'report_structure_help',
}

GENERAL_WORKFLOW_INTENTS = {
    'sample_collection',
    'coag_test',
    'quality_control',
}


def recommend_model_switch(text: str, selected_model_key: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    model_key = (selected_model_key or GENERAL_MODEL_KEY).strip() or GENERAL_MODEL_KEY
    normalized = normalize_text(text)
    entity = detect_medical_entity(text)
    if entity is None:
        if model_key == REPORT_MODEL_KEY and any(
            token in normalized for token in ('tube', 'specimen', 'sample', 'collection', 'coagulation', 'qc', 'quality control')
        ):
            return (
                GENERAL_MODEL_KEY,
                'This looks like a workflow or specimen-handling question. The General model is a better fit for tube choice, coag collection, and QC workflow questions.',
            )
        return None, None

    if model_key == GENERAL_MODEL_KEY and entity.intent in REPORT_FOCUSED_INTENTS:
        return (
            REPORT_MODEL_KEY,
            'This looks like a hematology report question. The Report model is a better fit for CBC parameters, flags, and report layout questions.',
        )

    if model_key == REPORT_MODEL_KEY and entity.intent in GENERAL_WORKFLOW_INTENTS:
        return (
            GENERAL_MODEL_KEY,
            'This looks like a workflow or specimen-handling question. The General model is a better fit for tube choice, coag collection, and QC workflow questions.',
        )

    return None, None
