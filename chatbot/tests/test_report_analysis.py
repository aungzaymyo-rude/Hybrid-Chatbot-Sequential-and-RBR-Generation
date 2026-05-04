from __future__ import annotations

from chatbot.utils.report_analysis import analyze_report_input


def test_analyze_report_input_marks_high_wbc():
    result = analyze_report_input("WBC is 13.7")
    assert result is not None
    assert result.intent == "report_numeric_result_analysis"
    assert result.label == "WBC"
    assert result.status == "high"
    assert "above range" in result.response.lower()
    assert result.support_note
    assert "diagnosis or treatment advice" in result.support_note.lower()
    assert "diagnosis or treatment advice" not in result.response.lower()


def test_analyze_report_input_marks_low_mcv():
    result = analyze_report_input("MCV is 72")
    assert result is not None
    assert result.intent == "report_numeric_result_analysis"
    assert result.label == "MCV"
    assert result.status == "low"
    assert "microcytic pattern" in result.response.lower()


def test_analyze_report_input_handles_report_flag():
    result = analyze_report_input("My report shows anemia")
    assert result is not None
    assert result.intent == "report_flag_result_analysis"
    assert result.label == "anemia"
    assert "hemoglobin" in result.response.lower()
    assert result.support_note


def test_analyze_report_input_uses_male_hgb_range_when_present():
    result = analyze_report_input("Adult male HGB is 13.0")
    assert result is not None
    assert result.intent == "report_numeric_result_analysis"
    assert result.label == "HGB"
    assert result.status == "low"
    assert result.demographic_hint == "male"
    assert "adult male range" in result.response.lower()


def test_analyze_report_input_uses_female_hct_range_when_present():
    result = analyze_report_input("Female HCT is 45")
    assert result is not None
    assert result.intent == "report_numeric_result_analysis"
    assert result.label == "HCT"
    assert result.status == "within_range"
    assert result.demographic_hint == "female"
    assert "adult female range" in result.response.lower()


def test_analyze_report_input_uses_pediatric_hgb_range_when_present():
    result = analyze_report_input("Child HGB is 10.5")
    assert result is not None
    assert result.intent == "report_numeric_result_analysis"
    assert result.label == "HGB"
    assert result.status == "low"
    assert result.demographic_hint == "pediatric"
    assert "pediatric range" in result.response.lower()


def test_analyze_report_input_uses_pediatric_wbc_range_when_present():
    result = analyze_report_input("Pediatric WBC is 13.0")
    assert result is not None
    assert result.intent == "report_numeric_result_analysis"
    assert result.label == "WBC"
    assert result.status == "within_range"
    assert result.demographic_hint == "pediatric"


def test_analyze_report_input_uses_age_as_adult_context():
    result = analyze_report_input("in my report WBC is 13.37 age is 51")
    assert result is not None
    assert result.intent == "report_numeric_result_analysis"
    assert result.label == "WBC"
    assert result.age_years == 51
    assert result.demographic_hint == "adult"
    assert "adult range" in result.response.lower()
    assert "age 51" not in result.response.lower()


def test_analyze_report_input_uses_age_as_pediatric_context():
    result = analyze_report_input("WBC is 13.0 age is 10")
    assert result is not None
    assert result.intent == "report_numeric_result_analysis"
    assert result.label == "WBC"
    assert result.age_years == 10
    assert result.demographic_hint == "pediatric"
    assert "pediatric range" in result.response.lower()
    assert "age 10" not in result.response.lower()


def test_analyze_report_input_handles_multiple_numeric_values():
    result = analyze_report_input("Age is 50 WBC is 13 MCV is 73 PLT is 1")
    assert result is not None
    assert result.intent == "report_numeric_result_analysis"
    assert result.observation_count == 3
    assert result.demographic_hint == "adult"
    assert "report review summary" in result.response.lower()
    assert "wbc 13" in result.response.lower()
    assert "mcv 73" in result.response.lower()
    assert "plt 1" in result.response.lower()
