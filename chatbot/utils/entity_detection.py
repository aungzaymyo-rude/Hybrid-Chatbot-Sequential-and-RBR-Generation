from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional

from chatbot.utils.preprocessing import normalize_text


@dataclass(frozen=True)
class EntityRule:
    label: str
    intent: str
    canonical_question: str
    patterns: tuple[str, ...]


_RULES: tuple[EntityRule, ...] = (
    EntityRule(
        label='cbc_columns',
        intent='report_structure_help',
        canonical_question='How do I read the result, unit, and reference range columns?',
        patterns=(r'\bresult column\b', r'\bunit column\b', r'\breference range\b', r'\bh and l markers?\b'),
    ),
    EntityRule(
        label='cbc_report_layout',
        intent='report_structure_help',
        canonical_question='How do I read this CBC report?',
        patterns=(r'\bcbc report\b', r'\bhematology report\b', r'\bblood report\b', r'\breport layout\b'),
    ),
    EntityRule(
        label='hemoglobin_parameter',
        intent='cbc_result_parameter',
        canonical_question='What is hemoglobin?',
        patterns=(r'\bhgb\b', r'\bhemoglobin\b'),
    ),
    EntityRule(
        label='hematocrit_parameter',
        intent='cbc_result_parameter',
        canonical_question='What is hematocrit?',
        patterns=(r'\bhct\b', r'\bhematocrit\b'),
    ),
    EntityRule(
        label='rdw_parameter',
        intent='cbc_result_parameter',
        canonical_question='What is RDW?',
        patterns=(r'\brdw(?:-cv|-sd)?\b', r'\bred cell distribution width\b'),
    ),
    EntityRule(
        label='neutrophilia_flag',
        intent='cbc_flag_explanation',
        canonical_question='What is neutrophilia?',
        patterns=(r'\bneutrophilia\b',),
    ),
    EntityRule(
        label='leucocytosis_flag',
        intent='cbc_flag_explanation',
        canonical_question='What is leucocytosis?',
        patterns=(r'\bleucocytosis\b', r'\bleukocytosis\b'),
    ),
    EntityRule(
        label='abn_distribution_flag',
        intent='cbc_flag_explanation',
        canonical_question='What is RBC abnormal distribution?',
        patterns=(r'\brbc abn distribution\b', r'\babnormal distribution\b', r'\bplt abn distribution\b'),
    ),
    EntityRule(
        label='anemia_term',
        intent='anemia_related_term',
        canonical_question='What is anemia?',
        patterns=(r'\banemia\b', r'\blow hemoglobin\b', r'\blow hematocrit\b'),
    ),
    EntityRule(
        label='thrombocytopenia_term',
        intent='platelet_abnormality',
        canonical_question='What is thrombocytopenia?',
        patterns=(r'\bthrombocytopenia\b', r'\blow platelet\b', r'\blow plt\b'),
    ),
    EntityRule(
        label='diff_absolute',
        intent='differential_result_explanation',
        canonical_question='What is Neu#?',
        patterns=(r'\bneu#\b', r'\blym#\b', r'\bmon#\b', r'\beos#\b', r'\bbas#\b'),
    ),
    EntityRule(
        label='diff_percent',
        intent='differential_result_explanation',
        canonical_question='What is Neu%?',
        patterns=(r'\bneu%\b', r'\blym%\b', r'\bmon%\b', r'\beos%\b', r'\bbas%\b'),
    ),
    EntityRule(
        label='aptt',
        intent='coag_test',
        canonical_question='What is aPTT?',
        patterns=(r'\baptt\b', r'\bactivated partial thromboplastin time\b'),
    ),
    EntityRule(
        label='pt',
        intent='coag_test',
        canonical_question='What is PT test?',
        patterns=(r'\bpt\b', r'\bprothrombin time\b'),
    ),
    EntityRule(
        label='inr',
        intent='coag_test',
        canonical_question='What does INR mean?',
        patterns=(r'\binr\b', r'\binternational normalized ratio\b'),
    ),
    EntityRule(
        label='citrate_tube',
        intent='coag_test',
        canonical_question='Which tube is used for coagulation tests?',
        patterns=(r'\bcitrate\b', r'\blight blue\b', r'\bcoag(?:ulation)? tube\b'),
    ),
    EntityRule(
        label='mcv',
        intent='rbc_term',
        canonical_question='What is MCV?',
        patterns=(r'\bmcv\b', r'\bmean corpuscular volume\b'),
    ),
    EntityRule(
        label='mch',
        intent='rbc_term',
        canonical_question='What is MCH?',
        patterns=(r'\bmch\b', r'\bmean corpuscular hemoglobin\b'),
    ),
    EntityRule(
        label='mchc',
        intent='rbc_term',
        canonical_question='What is MCHC?',
        patterns=(r'\bmchc\b', r'\bmean corpuscular hemoglobin concentration\b'),
    ),
    EntityRule(
        label='rdw',
        intent='rbc_term',
        canonical_question='What is RDW?',
        patterns=(r'\brdw\b', r'\bred cell distribution width\b'),
    ),
    EntityRule(
        label='hemoglobin',
        intent='rbc_term',
        canonical_question='What is hemoglobin?',
        patterns=(r'\bhemoglobin\b', r'\bhb\b'),
    ),
    EntityRule(
        label='hematocrit',
        intent='rbc_term',
        canonical_question='What is hematocrit?',
        patterns=(r'\bhematocrit\b', r'\bhct\b'),
    ),
    EntityRule(
        label='rbc',
        intent='rbc_term',
        canonical_question='What is RBC count?',
        patterns=(r'\brbc\b', r'\bred blood cell', r'\berythrocyte'),
    ),
    EntityRule(
        label='differential',
        intent='wbc_term',
        canonical_question='What is differential white cell count?',
        patterns=(r'\bdifferential\b', r'\bwhite cell differential\b'),
    ),
    EntityRule(
        label='leukocytosis',
        intent='wbc_term',
        canonical_question='What is leukocytosis?',
        patterns=(r'\bleukocytosis\b',),
    ),
    EntityRule(
        label='leukopenia',
        intent='wbc_term',
        canonical_question='What is leukopenia?',
        patterns=(r'\bleukopenia\b',),
    ),
    EntityRule(
        label='wbc',
        intent='wbc_term',
        canonical_question='What is WBC count?',
        patterns=(r'\bwbc\b', r'\bwhite blood cell', r'\bleukocyte'),
    ),
    EntityRule(
        label='blood_smear',
        intent='blood_smear',
        canonical_question='What is a peripheral blood smear?',
        patterns=(r'\bperipheral blood smear\b', r'\bblood smear\b', r'\bblood film\b', r'\bsmear review\b'),
    ),
    EntityRule(
        label='smear_prep',
        intent='blood_smear',
        canonical_question='How do you prepare a blood film?',
        patterns=(r'\bprepare a blood film\b', r'\bwedge smear\b', r'\bfeathered edge\b'),
    ),
    EntityRule(
        label='smear_stain',
        intent='blood_smear',
        canonical_question='What stains are used for blood smear?',
        patterns=(r'\bwright\b', r'\bgiemsa\b', r'\bstain(?:ed|s)?\b'),
    ),
    EntityRule(
        label='edta_tube',
        intent='sample_collection',
        canonical_question='Which tube is used for CBC?',
        patterns=(r'\bedta\b', r'\blavender(?:-top| top)?\b'),
    ),
    EntityRule(
        label='inversions',
        intent='sample_collection',
        canonical_question='How many inversions are needed for an EDTA tube?',
        patterns=(r'\binversion', r'\bmix(?:ing)?\b'),
    ),
    EntityRule(
        label='hemolysis',
        intent='sample_collection',
        canonical_question='How can I prevent hemolysis during CBC collection?',
        patterns=(r'\bhemolysis\b', r'\bhemoly[sz]ed\b'),
    ),
    EntityRule(
        label='labeling',
        intent='sample_collection',
        canonical_question='How should I label a CBC specimen?',
        patterns=(r'\blabel\b', r'\blabelling\b', r'\blabeling\b'),
    ),
    EntityRule(
        label='cbc_tube_question',
        intent='sample_collection',
        canonical_question='Which tube is used for CBC?',
        patterns=(
            r'\bwhich tube is used for cbc\b',
            r'\bwhat tube color is used for cbc\b',
            r'\bcbc tube\b',
            r'\bcbc collection tube\b',
        ),
    ),
    EntityRule(
        label='cbc',
        intent='cbc_info',
        canonical_question='What is a CBC?',
        patterns=(r'\bcbc\b', r'\bcomplete blood count\b'),
    ),
    EntityRule(
        label='platelet',
        intent='cbc_info',
        canonical_question='What is platelet count?',
        patterns=(r'\bplatelet', r'\bplt\b'),
    ),
)


def _matches(text: str, patterns: Iterable[str]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def detect_medical_entity(text: str) -> Optional[EntityRule]:
    normalized = normalize_text(text)
    if not normalized:
        return None
    for rule in _RULES:
        if _matches(normalized, rule.patterns):
            return rule
    return None
