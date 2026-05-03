from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict

from chatbot.utils.preprocessing import normalize_text


@dataclass(frozen=True)
class NumericParameter:
    label: str
    canonical: str
    low: float
    high: float
    unit: str
    abnormal_note: str
    normal_note: str


@dataclass(frozen=True)
class ReportAnalysisResult:
    analysis_type: str
    intent: str
    label: str
    response: str
    status: str | None = None
    value: float | None = None
    criteria: str | None = None
    demographic_hint: str | None = None
    age_years: int | None = None


_NUMERIC_PARAMETERS: tuple[NumericParameter, ...] = (
    NumericParameter('wbc', 'WBC', 4.0, 11.0, 'x10^3/uL', 'A value above range is commonly reported as leukocytosis, while a value below range is commonly reported as leukopenia.', 'This falls within a common adult WBC reference interval.'),
    NumericParameter('rbc', 'RBC', 4.0, 6.2, 'x10^6/uL', 'A value below range suggests a reduced red-cell count pattern, while a value above range suggests an increased red-cell count pattern. RBC interpretation should be reviewed with hemoglobin, hematocrit, and indices.', 'This falls within a common adult RBC reference interval.'),
    NumericParameter('hgb', 'HGB', 12.0, 16.5, 'g/dL', 'A value below range supports an anemia-pattern review, while a value above range suggests an increased hemoglobin pattern. Hemoglobin ranges vary by sex, age, and laboratory.', 'This falls within a common adult hemoglobin reference interval.'),
    NumericParameter('hct', 'HCT', 36.0, 48.0, '%', 'A value below range supports an anemia-pattern review, while a value above range suggests an increased hematocrit pattern. Hematocrit ranges vary by sex, age, and laboratory.', 'This falls within a common adult hematocrit reference interval.'),
    NumericParameter('mcv', 'MCV', 80.0, 100.0, 'fL', 'A low value fits a microcytic pattern, while a high value fits a macrocytic pattern. Interpret MCV with MCH, MCHC, RDW, and smear findings.', 'This falls within a common adult MCV reference interval and is usually described as normocytic.'),
    NumericParameter('mch', 'MCH', 27.0, 33.0, 'pg', 'A low value suggests reduced hemoglobin per red cell, while a high value suggests increased hemoglobin content per red cell. Interpret with MCV and MCHC.', 'This falls within a common adult MCH reference interval.'),
    NumericParameter('mchc', 'MCHC', 32.0, 36.0, 'g/dL', 'A low value supports a hypochromic pattern. Interpret with MCV, MCH, and smear findings.', 'This falls within a common adult MCHC reference interval.'),
    NumericParameter('rdw', 'RDW', 11.5, 14.5, '%', 'A high value indicates increased red-cell size variation. RDW should be interpreted with MCV and smear findings.', 'This falls within a common adult RDW reference interval.'),
    NumericParameter('plt', 'PLT', 150.0, 400.0, 'x10^3/uL', 'A value below range is commonly reported as thrombocytopenia, while a value above range is commonly reported as thrombocytosis.', 'This falls within a common adult platelet reference interval.'),
    NumericParameter('mpv', 'MPV', 7.5, 12.5, 'fL', 'An abnormal MPV should be interpreted with the platelet count and smear review rather than alone.', 'This falls within a common adult MPV reference interval.'),
)

_PARAMETER_ALIASES: dict[str, NumericParameter] = {}
for param in _NUMERIC_PARAMETERS:
    aliases = {param.label, param.canonical.lower()}
    if param.label == 'hgb':
        aliases.add('hemoglobin')
    elif param.label == 'hct':
        aliases.add('hematocrit')
    elif param.label == 'plt':
        aliases.update({'platelet', 'platelets', 'platelet count'})
    elif param.label == 'wbc':
        aliases.update({'white blood cell', 'white blood cells'})
    elif param.label == 'rbc':
        aliases.update({'red blood cell', 'red blood cells'})
    elif param.label == 'mcv':
        aliases.add('mean corpuscular volume')
    elif param.label == 'mch':
        aliases.add('mean corpuscular hemoglobin')
    elif param.label == 'mchc':
        aliases.add('mean corpuscular hemoglobin concentration')
    elif param.label == 'rdw':
        aliases.add('red cell distribution width')
    for alias in aliases:
        _PARAMETER_ALIASES[alias] = param

_FLAG_RESPONSES: Dict[str, str] = {
    'anemia': 'A report flag for anemia usually means hemoglobin and/or hematocrit is below the laboratory reference range. It should be reviewed together with RBC count, indices such as MCV, RDW, and smear findings. This is a report pattern, not a diagnosis by itself.',
    'thrombocytopenia': 'A report flag for thrombocytopenia means the platelet count is below the laboratory reference range. Confirm the count against the printed range and review smear findings such as platelet clumping according to SOP. This is a report pattern, not a diagnosis by itself.',
    'thrombocytosis': 'A report flag for thrombocytosis means the platelet count is above the laboratory reference range. It should be reviewed together with CBC context and laboratory or clinical follow-up rules. This is a report pattern, not a diagnosis by itself.',
    'neutrophilia': 'A report flag for neutrophilia means the neutrophil count or percentage is above the reference range. It is a report pattern and should be reviewed with the total WBC count and the clinical context. It is not a diagnosis by itself.',
    'leukocytosis': 'A report flag for leukocytosis means the total white-cell count is above the laboratory reference range. It should be reviewed together with the differential and the printed reference range. It is not a diagnosis by itself.',
    'leucocytosis': 'A report flag for leukocytosis means the total white-cell count is above the laboratory reference range. It should be reviewed together with the differential and the printed reference range. It is not a diagnosis by itself.',
    'leukopenia': 'A report flag for leukopenia means the total white-cell count is below the laboratory reference range. It should be reviewed together with the differential and the printed reference range. It is not a diagnosis by itself.',
    'microcytosis': 'A report flag for microcytosis means the red cells are smaller than the usual reference pattern, often associated with a low MCV. Confirm the printed range and review RBC indices and smear findings. It is not a diagnosis by itself.',
    'macrocytosis': 'A report flag for macrocytosis means the red cells are larger than the usual reference pattern, often associated with a high MCV. Confirm the printed range and review RBC indices and smear findings. It is not a diagnosis by itself.',
    'hypochromia': 'A report flag for hypochromia means the red cells appear to have reduced hemoglobinization, often reviewed with MCH, MCHC, MCV, and smear findings. It is a report pattern, not a diagnosis by itself.',
}

_NUMERIC_PATTERN = re.compile(
    r'\b(?P<label>wbc|rbc|hgb|hb|hemoglobin|hct|hematocrit|mcv|mch|mchc|rdw|plt|platelet(?: count)?|mpv)\b[^\d]{0,16}(?P<value>\d+(?:\.\d+)?)',
    re.IGNORECASE,
)

_REPORT_FLAG_PATTERN = re.compile(
    r'\b(?:my report(?: shows?| say[s]?)?|report(?: shows?| say[s]?)|flag(?:ged)? as|shows?)\b.*\b(anemia|thrombocytopenia|thrombocytosis|neutrophilia|leukocytosis|leucocytosis|leukopenia|microcytosis|macrocytosis|hypochromia)\b',
    re.IGNORECASE,
)
_MALE_PATTERN = re.compile(r'\b(male|man|men|adult male)\b', re.IGNORECASE)
_FEMALE_PATTERN = re.compile(r'\b(female|woman|women|adult female)\b', re.IGNORECASE)
_PEDIATRIC_PATTERN = re.compile(r'\b(child|children|pediatric|paediatric|kid|school-age|school age)\b', re.IGNORECASE)
_AGE_PATTERN = re.compile(r'\bage(?:\s*(?:is|=|:))?\s*(?P<age>\d{1,3})\b', re.IGNORECASE)
_YEARS_OLD_PATTERN = re.compile(r'\b(?P<age>\d{1,3})\s*(?:years?|yrs?)\s*old\b', re.IGNORECASE)


def extract_age_years(text: str) -> int | None:
    normalized = normalize_text(text)
    match = _AGE_PATTERN.search(normalized) or _YEARS_OLD_PATTERN.search(normalized)
    if not match:
        return None
    try:
        age = int(match.group('age'))
    except ValueError:
        return None
    if age < 0 or age > 120:
        return None
    return age


def detect_demographic_hint(text: str) -> str | None:
    normalized = normalize_text(text)
    age_years = extract_age_years(normalized)
    has_pediatric = bool(_PEDIATRIC_PATTERN.search(normalized))
    has_male = bool(_MALE_PATTERN.search(normalized))
    has_female = bool(_FEMALE_PATTERN.search(normalized))
    if age_years is not None and age_years < 18:
        return 'pediatric'
    if has_pediatric:
        return 'pediatric'
    if age_years is not None and age_years >= 18:
        if has_male and not has_female:
            return 'male'
        if has_female and not has_male:
            return 'female'
        return 'adult'
    if has_male and not has_female:
        return 'male'
    if has_female and not has_male:
        return 'female'
    return None


def resolve_reference_interval(parameter: NumericParameter, demographic_hint: str | None) -> tuple[float, float, str]:
    if demographic_hint == 'pediatric':
        pediatric_ranges = {
            'wbc': (5.0, 14.5, 'common pediatric range'),
            'rbc': (4.0, 5.2, 'common pediatric range'),
            'hgb': (11.0, 14.5, 'common pediatric range'),
            'hct': (35.0, 44.0, 'common pediatric range'),
            'mcv': (77.0, 95.0, 'common pediatric range'),
            'plt': (150.0, 450.0, 'common pediatric range'),
        }
        if parameter.label in pediatric_ranges:
            return pediatric_ranges[parameter.label]
    if parameter.label == 'hgb':
        if demographic_hint == 'male':
            return 13.5, 17.5, 'common adult male range'
        if demographic_hint == 'female':
            return 12.0, 15.5, 'common adult female range'
    if parameter.label == 'hct':
        if demographic_hint == 'male':
            return 41.0, 53.0, 'common adult male range'
        if demographic_hint == 'female':
            return 36.0, 46.0, 'common adult female range'
    return parameter.low, parameter.high, 'common adult range'


def adjust_reference_note(note: str, demographic_hint: str | None) -> str:
    if demographic_hint == 'pediatric':
        return note.replace('common adult', 'common pediatric')
    if demographic_hint == 'adult':
        return note.replace('common adult', 'common adult')
    if demographic_hint == 'male':
        return note.replace('common adult', 'common adult male')
    if demographic_hint == 'female':
        return note.replace('common adult', 'common adult female')
    return note


def extract_numeric_result(text: str) -> tuple[NumericParameter, float] | None:
    normalized = normalize_text(text)
    match = _NUMERIC_PATTERN.search(normalized)
    if not match:
        return None
    raw_label = match.group('label').strip().lower()
    if raw_label == 'hb':
        raw_label = 'hgb'
    if raw_label == 'platelet count':
        raw_label = 'platelet'
    parameter = _PARAMETER_ALIASES.get(raw_label)
    if not parameter:
        return None
    try:
        value = float(match.group('value'))
    except ValueError:
        return None
    return parameter, value


def extract_report_flag(text: str) -> str | None:
    normalized = normalize_text(text)
    match = _REPORT_FLAG_PATTERN.search(normalized)
    if match:
        return match.group(1).lower()
    for flag in _FLAG_RESPONSES:
        if flag in normalized and any(token in normalized for token in ('report', 'flag', 'shows', 'show', 'say', 'stated')):
            return flag
    return None


def analyze_report_input(text: str) -> ReportAnalysisResult | None:
    numeric = extract_numeric_result(text)
    if numeric:
        parameter, value = numeric
        age_years = extract_age_years(text)
        demographic_hint = detect_demographic_hint(text)
        range_low, range_high, range_label = resolve_reference_interval(parameter, demographic_hint)
        if value < range_low:
            status = 'low'
            interpretation = f'Using the assistant\'s {range_label} for {parameter.canonical} ({range_low:g}-{range_high:g} {parameter.unit}), a value of {value:g} is below range.'
        elif value > range_high:
            status = 'high'
            interpretation = f'Using the assistant\'s {range_label} for {parameter.canonical} ({range_low:g}-{range_high:g} {parameter.unit}), a value of {value:g} is above range.'
        else:
            status = 'within_range'
            interpretation = f'Using the assistant\'s {range_label} for {parameter.canonical} ({range_low:g}-{range_high:g} {parameter.unit}), a value of {value:g} is within range.'

        follow_up = adjust_reference_note(parameter.normal_note, demographic_hint) if status == 'within_range' else parameter.abnormal_note
        response_parts = [
            interpretation,
            follow_up,
        ]
        response_parts.append(
            'Reference ranges vary by laboratory, age, and clinical setting, so the printed range on the actual report should be confirmed before any final interpretation.'
        )
        response_parts.append('This assistant provides report support, not diagnosis or treatment advice.')
        response = ' '.join(response_parts)
        return ReportAnalysisResult(
            analysis_type='numeric_result',
            intent='report_numeric_result_analysis',
            label=parameter.canonical,
            response=response,
            status=status,
            value=value,
            criteria=f'{range_low:g}-{range_high:g} {parameter.unit}',
            demographic_hint=demographic_hint,
            age_years=age_years,
        )

    report_flag = extract_report_flag(text)
    if report_flag:
        response = _FLAG_RESPONSES[report_flag]
        return ReportAnalysisResult(
            analysis_type='report_flag',
            intent='report_flag_result_analysis',
            label=report_flag,
            response=response,
        )

    return None
