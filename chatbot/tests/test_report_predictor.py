from __future__ import annotations

from pathlib import Path

from chatbot.inference.predictor import IntentPredictor


CONFIG_PATH = str(Path(__file__).resolve().parents[1] / 'config.yaml')
REPORT_MODEL_DIR = str(Path(__file__).resolve().parents[1] / 'models' / 'intent_report')


def test_report_predictor_handles_numeric_result_phrase():
    predictor = IntentPredictor(model_dir=REPORT_MODEL_DIR, config_path=CONFIG_PATH)
    prediction = predictor.predict('PLT is 365')
    assert prediction.intent == 'report_numeric_result_analysis'
    assert prediction.confidence >= 0.8


def test_report_predictor_handles_report_flag_phrase():
    predictor = IntentPredictor(model_dir=REPORT_MODEL_DIR, config_path=CONFIG_PATH)
    prediction = predictor.predict('My report shows anemia')
    assert prediction.intent == 'report_flag_result_analysis'
    assert prediction.confidence >= 0.8


def test_report_predictor_does_not_treat_age_only_as_report_analysis():
    predictor = IntentPredictor(model_dir=REPORT_MODEL_DIR, config_path=CONFIG_PATH)
    prediction = predictor.predict('age is 43')
    assert prediction.intent == 'incomplete_query'
