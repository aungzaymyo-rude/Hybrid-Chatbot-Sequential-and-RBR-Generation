from __future__ import annotations

from chatbot.utils.model_advisory import recommend_model_switch


def test_general_model_suggests_report_for_report_query():
    suggested_model, message = recommend_model_switch("How do I read this CBC report?", "general")
    assert suggested_model == "report"
    assert "Report model" in message


def test_report_model_suggests_general_for_workflow_query():
    suggested_model, message = recommend_model_switch("Which tube is used for coagulation tests?", "report")
    assert suggested_model == "general"
    assert "General model" in message


def test_report_model_suggests_general_for_cbc_tube_query():
    suggested_model, message = recommend_model_switch("Which tube is used for CBC?", "report")
    assert suggested_model == "general"
    assert "General model" in message


def test_matching_model_has_no_advisory():
    suggested_model, message = recommend_model_switch("What is MCV?", "report")
    assert suggested_model is None
    assert message is None


def test_general_model_suggests_report_for_numeric_result_query():
    suggested_model, message = recommend_model_switch("WBC is 13.7", "general")
    assert suggested_model == "report"
    assert "report-result question" in message


def test_general_model_suggests_report_for_report_flag_query():
    suggested_model, message = recommend_model_switch("My report shows anemia", "general")
    assert suggested_model == "report"
    assert "report-result question" in message
