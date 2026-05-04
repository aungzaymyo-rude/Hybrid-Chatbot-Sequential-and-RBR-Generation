from __future__ import annotations

import re
from dataclasses import dataclass

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
class NumericObservation:
    parameter: NumericParameter
    value: float
    status: str
    criteria: str
    range_label: str


@dataclass(frozen=True)
class ReportAnalysisResult:
    analysis_type: str
    intent: str
    label: str
    response: str
    support_note: str | None = None
    status: str | None = None
    value: float | None = None
    criteria: str | None = None
    demographic_hint: str | None = None
    age_years: int | None = None
    observation_count: int = 0


_SUPPORT_NOTE = (
    'Interpretation support only. Confirm the printed report range and local laboratory policy before any final interpretation. '
    'No diagnosis or treatment advice is provided.'
)

_NUMERIC_PARAMETERS: tuple[NumericParameter, ...] = (
    NumericParameter('wbc', 'WBC', 4.0, 11.0, 'x10^3/uL', 'commonly reported as leukocytosis when high and leukopenia when low', 'within a common adult WBC reference interval'),
    NumericParameter('rbc', 'RBC', 4.0, 6.2, 'x10^6/uL', 'suggestive of a reduced red-cell count pattern when low and an increased red-cell count pattern when high', 'within a common adult RBC reference interval'),
    NumericParameter('hgb', 'HGB', 12.0, 16.5, 'g/dL', 'supportive of an anemia-pattern review when low and an increased hemoglobin pattern when high', 'within a common adult hemoglobin reference interval'),
    NumericParameter('hct', 'HCT', 36.0, 48.0, '%', 'supportive of an anemia-pattern review when low and an increased hematocrit pattern when high', 'within a common adult hematocrit reference interval'),
    NumericParameter('mcv', 'MCV', 80.0, 100.0, 'fL', 'consistent with a microcytic pattern when low and a macrocytic pattern when high', 'within a common adult MCV reference interval and usually described as normocytic'),
    NumericParameter('mch', 'MCH', 27.0, 33.0, 'pg', 'suggestive of reduced hemoglobin per red cell when low and increased hemoglobin content per red cell when high', 'within a common adult MCH reference interval'),
    NumericParameter('mchc', 'MCHC', 32.0, 36.0, 'g/dL', 'supportive of a hypochromic pattern when low', 'within a common adult MCHC reference interval'),
    NumericParameter('rdw', 'RDW', 11.5, 14.5, '%', 'indicative of increased red-cell size variation when high', 'within a common adult RDW reference interval'),
    NumericParameter('plt', 'PLT', 150.0, 400.0, 'x10^3/uL', 'commonly reported as thrombocytopenia when low and thrombocytosis when high', 'within a common adult platelet reference interval'),
    NumericParameter('mpv', 'MPV', 7.5, 12.5, 'fL', 'best reviewed with platelet count and smear findings when abnormal', 'within a common adult MPV reference interval'),
)

_PARAMETER_ALIASES: dict[str, NumericParameter] = {}
for param in _NUMERIC_PARAMETERS:
    aliases = {param.label, param.canonical.lower()}
    if param.label == 'hgb':
        aliases.update({'hb', 'hemoglobin'})
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

_FLAG_RESPONSES: dict[str, str] = {
    'anemia': 'A report flag for anemia usually means hemoglobin and/or hematocrit is below the laboratory reference range. It should be reviewed together with RBC count, MCV, RDW, and smear findings. This is a report pattern rather than a diagnosis.',
    'thrombocytopenia': 'A report flag for thrombocytopenia means the platelet count is below the laboratory reference range. Confirm the count against the printed range and review smear findings such as platelet clumping according to SOP. This is a report pattern rather than a diagnosis.',
    'thrombocytosis': 'A report flag for thrombocytosis means the platelet count is above the laboratory reference range. It should be reviewed together with CBC context and laboratory follow-up rules. This is a report pattern rather than a diagnosis.',
    'neutrophilia': 'A report flag for neutrophilia means the neutrophil count or percentage is above the reference range. It should be reviewed with the total WBC count and clinical context. This is a report pattern rather than a diagnosis.',
    'leukocytosis': 'A report flag for leukocytosis means the total white-cell count is above the laboratory reference range. It should be reviewed together with the differential and the printed report range. This is a report pattern rather than a diagnosis.',
    'leucocytosis': 'A report flag for leukocytosis means the total white-cell count is above the laboratory reference range. It should be reviewed together with the differential and the printed report range. This is a report pattern rather than a diagnosis.',
    'leukopenia': 'A report flag for leukopenia means the total white-cell count is below the laboratory reference range. It should be reviewed together with the differential and the printed report range. This is a report pattern rather than a diagnosis.',
    'microcytosis': 'A report flag for microcytosis means the red cells are smaller than the usual reference pattern, often associated with a low MCV. Confirm the printed range and review RBC indices and smear findings. This is a report pattern rather than a diagnosis.',
    'macrocytosis': 'A report flag for macrocytosis means the red cells are larger than the usual reference pattern, often associated with a high MCV. Confirm the printed range and review RBC indices and smear findings. This is a report pattern rather than a diagnosis.',
    'hypochromia': 'A report flag for hypochromia means the red cells appear to have reduced hemoglobinization, often reviewed with MCH, MCHC, MCV, and smear findings. This is a report pattern rather than a diagnosis.',
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


def extract_numeric_results(text: str) -> list[tuple[NumericParameter, float]]:
    normalized = normalize_text(text)
    results: list[tuple[NumericParameter, float]] = []
    for match in _NUMERIC_PATTERN.finditer(normalized):
        raw_label = match.group('label').strip().lower()
        if raw_label == 'hb':
            raw_label = 'hgb'
        if raw_label == 'platelet count':
            raw_label = 'platelet'
        parameter = _PARAMETER_ALIASES.get(raw_label)
        if not parameter:
            continue
        try:
            value = float(match.group('value'))
        except ValueError:
            continue
        results.append((parameter, value))
    return results


def extract_numeric_result(text: str) -> tuple[NumericParameter, float] | None:
    results = extract_numeric_results(text)
    return results[0] if results else None


def extract_report_flag(text: str) -> str | None:
    normalized = normalize_text(text)
    match = _REPORT_FLAG_PATTERN.search(normalized)
    if match:
        return match.group(1).lower()
    for flag in _FLAG_RESPONSES:
        if flag in normalized and any(token in normalized for token in ('report', 'flag', 'shows', 'show', 'say', 'stated')):
            return flag
    return None


def _classify_numeric(parameter: NumericParameter, value: float, demographic_hint: str | None) -> NumericObservation:
    range_low, range_high, range_label = resolve_reference_interval(parameter, demographic_hint)
    if value < range_low:
        status = 'low'
    elif value > range_high:
        status = 'high'
    else:
        status = 'within_range'
    return NumericObservation(
        parameter=parameter,
        value=value,
        status=status,
        criteria=f'{range_low:g}-{range_high:g} {parameter.unit}',
        range_label=range_label,
    )


def _format_observation_clause(observation: NumericObservation) -> str:
    parameter = observation.parameter
    criteria = observation.criteria
    if observation.status == 'low':
        return f'{parameter.canonical} {observation.value:g} ({criteria}) is below range and is {parameter.abnormal_note}.'
    if observation.status == 'high':
        return f'{parameter.canonical} {observation.value:g} ({criteria}) is above range and is {parameter.abnormal_note}.'
    return f'{parameter.canonical} {observation.value:g} ({criteria}) is within range and is {parameter.normal_note}.'


def _build_numeric_response(observations: list[NumericObservation]) -> str:
    if not observations:
        return ''
    if len(observations) == 1:
        observation = observations[0]
        opener = (
            f'Using the assistant\'s {observation.range_label} for {observation.parameter.canonical}, '
            f'{observation.parameter.canonical} {observation.value:g} ({observation.criteria}) '
        )
        if observation.status == 'low':
            return opener + f'is below range and is {observation.parameter.abnormal_note}.'
        if observation.status == 'high':
            return opener + f'is above range and is {observation.parameter.abnormal_note}.'
        return opener + f'is within range and is {observation.parameter.normal_note}.'

    range_label = observations[0].range_label
    clauses = [_format_observation_clause(observation) for observation in observations]
    return f'Using the assistant\'s {range_label}, report review summary: ' + ' '.join(clauses)


def analyze_report_input(text: str) -> ReportAnalysisResult | None:
    numeric_results = extract_numeric_results(text)
    if numeric_results:
        age_years = extract_age_years(text)
        demographic_hint = detect_demographic_hint(text)
        observations = [_classify_numeric(parameter, value, demographic_hint) for parameter, value in numeric_results]
        response = _build_numeric_response(observations)
        joined_labels = ', '.join(observation.parameter.canonical for observation in observations)
        joined_criteria = '; '.join(
            f'{observation.parameter.canonical}: {observation.criteria}' for observation in observations
        )
        primary = observations[0]
        return ReportAnalysisResult(
            analysis_type='numeric_result',
            intent='report_numeric_result_analysis',
            label=joined_labels,
            response=response,
            support_note=_SUPPORT_NOTE,
            status=primary.status,
            value=primary.value,
            criteria=joined_criteria,
            demographic_hint=demographic_hint,
            age_years=age_years,
            observation_count=len(observations),
        )

    report_flag = extract_report_flag(text)
    if report_flag:
        return ReportAnalysisResult(
            analysis_type='report_flag',
            intent='report_flag_result_analysis',
            label=report_flag,
            response=_FLAG_RESPONSES[report_flag],
            support_note=_SUPPORT_NOTE,
        )

    return None
