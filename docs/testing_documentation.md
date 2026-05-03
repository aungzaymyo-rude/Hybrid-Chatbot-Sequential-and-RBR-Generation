# Hybrid Chatbot Testing Documentation

## 1. Test Plan

This document records the unit-level and feature-level testing approach used for the Hybrid Chatbot for Medical Haematology. The scope covers the sequential intent classifier, report-analysis layer, retrieval-based routing, API behavior, admin monitoring flows, HTTPS deployment behavior, and retraining support exports.

### 1.1 Objectives

- Verify that the BiLSTM intent models classify supported hematology prompts correctly.
- Verify that rule-based safety, entity detection, model auto-switching, and retrieval routing behave consistently.
- Verify that the report model can analyze numeric CBC-style report phrases, sex-specific HGB/HCT phrases, and pediatric/age-aware phrases within bounded support rules.
- Verify that the admin and MLOps support features export the correct retraining evidence.

### 1.2 Environment

- Operating environment: Windows 11 local development and Docker-based deployment
- Backend: FastAPI
- ML runtime: PyTorch BiLSTM intent classifier
- Storage: PostgreSQL
- Test framework: pytest
- Latest automated suite status at documentation time: `50 passed`

### 1.3 Entry and Exit Criteria

- Entry criteria: features implemented, datasets merged, model artifacts generated, test environment available
- Exit criteria: all planned cases executed, no blocking failures remaining, regression suite passing, evidence captured

## 2. Test Case Catalogue

| ID | Category | Component | Objective | Task | Expected Result | Actual Result | Status | Evidence |
|---|---|---|---|---|---|---|---|---|
| UT-01 | Unit | Preprocessing | Normalize text for downstream inference. | Input mixed-case query with punctuation. | Normalized lowercase phrase is produced consistently. | Passed in `test_preprocessing.py`. | Pass | Automated |
| UT-02 | Unit | Predictor rule layer | Detect greeting phrases before model inference. | Submit `hi` to the predictor. | Intent resolves to `greeting` with rule priority. | Passed in `test_predictor_rules.py` and API smoke checks. | Pass | Automated + smoke |
| UT-03 | Unit | Predictor rule layer | Detect social small-talk phrases. | Submit `how are u` to the predictor. | Intent resolves to `small_talk` instead of `incomplete_query`. | Passed in `test_predictor_rules.py`. | Pass | Automated |
| UT-04 | Unit | Safety rule layer | Block unsafe treatment language. | Submit phrase containing `prescribe` or `inject`. | Intent resolves to `unsafe_medical_request`. | Passed in `test_predictor_rules.py` and route tests. | Pass | Automated |
| UT-05 | Unit | Entity detection | Recognize MCV as an RBC-report entity. | Submit `What is MCV?`. | Entity rule maps to canonical MCV question. | Passed in `test_entity_detection.py`. | Pass | Automated |
| UT-06 | Unit | Entity detection | Recognize aPTT as coagulation entity. | Submit `What is aPTT?`. | Entity rule maps to coagulation knowledge. | Passed via routing tests and smoke checks. | Pass | Automated + smoke |
| UT-07 | Unit | Routing layer | Prioritize direct sample-collection retrieval. | Submit `Which tube is used for CBC?` with `sample_collection` intent. | EDTA/lavender-top answer is returned instead of generic CBC info. | Passed in `test_routing_engine.py`. | Pass | Automated |
| UT-08 | Unit | Routing layer | Return CBC sample rejection criteria. | Submit `What are the rejection criteria for a CBC sample?`. | Rejection-criteria answer mentions wrong tube / clotted sample style conditions. | Passed in `test_routing_engine.py`. | Pass | Automated |
| UT-09 | Unit | Routing layer | Return CBC stability guidance. | Submit `How long is a CBC sample stable?`. | Stability answer references validated limits and SOP. | Passed in `test_routing_engine.py`. | Pass | Automated |
| UT-10 | Unit | Model advisory | Auto-switch report questions from general to report model. | Submit `How do I read this CBC report?` while `general` is selected. | Model advisory recommends / routes to `report`. | Passed in `test_model_advisory.py` and UI smoke checks. | Pass | Automated + smoke |
| UT-11 | Unit | Model advisory | Auto-switch workflow questions from report to general model. | Submit `Which tube is used for coagulation tests?` while `report` is selected. | Model advisory recommends / routes to `general`. | Passed in `test_model_advisory.py` and UI smoke checks. | Pass | Automated + smoke |
| UT-12 | Unit | Report analysis | Interpret numeric WBC results. | Submit `WBC is 13.7`. | Intent resolves to `report_numeric_result_analysis` and response marks high range. | Passed in `test_report_analysis.py` and manual runtime verification. | Pass | Automated + manual |
| UT-13 | Unit | Report analysis | Interpret printed report flag text. | Submit `My report shows anemia`. | Intent resolves to `report_flag_result_analysis` with bounded non-diagnostic explanation. | Passed in `test_report_analysis.py` and runtime verification. | Pass | Automated + manual |
| UT-14 | Unit | Report analysis | Apply adult age context without exposing internal note. | Submit `in my report WBC is 13.37 age is 51`. | Adult range is applied, but no internal age-note sentence is displayed. | Verified after age-aware retraining and response cleanup. | Pass | Manual + regression |
| UT-15 | Unit | Report analysis | Apply pediatric age context. | Submit `WBC is 13 age is 10`. | Pediatric range is applied and result is interpreted within pediatric criteria. | Passed in `test_report_analysis.py` and runtime verification. | Pass | Automated + manual |
| UT-16 | Unit | Report analysis | Apply sex-specific HGB range. | Submit `Adult male HGB is 13.0`. | Male reference interval is used for HGB. | Passed in `test_report_analysis.py` and runtime verification. | Pass | Automated + manual |
| UT-17 | Unit | Report analysis | Apply sex-specific HCT range. | Submit `Female HCT is 45`. | Female reference interval is used for HCT. | Passed in `test_report_analysis.py` and runtime verification. | Pass | Automated + manual |
| UT-18 | Unit | Report analysis | Prevent age-only phrases from being treated as report analysis. | Submit `age is 43`. | Intent resolves to `incomplete_query`. | Passed in `test_report_predictor.py` and runtime verification. | Pass | Automated + manual |
| UT-19 | Unit | API layer | Return stable chat response schema. | POST `/chat` with `Hello`. | JSON response includes `intent`, `response`, `lang`, and model metadata. | Passed in `test_api.py`. | Pass | Automated |
| UT-20 | Unit | API layer | Expose report-analysis preview rows. | GET `/admin/api/report-analysis-preview`. | Preview returns report-analysis retraining candidates in JSON. | Passed in `test_api.py`. | Pass | Automated |
| UT-21 | Unit | Admin trace API | Trace end-to-end inference layers. | POST `/admin/api/trace` with `What is aPTT?`. | Trace returns preprocessing, classifier, retrieval, and final route fields. | Validated through admin trace runtime checks. | Pass | Manual + API |
| UT-22 | Unit | Export pipeline | Export accepted reviewed samples. | GET `/admin/api/export-reviewed`. | CSV file is generated for retraining. | Validated through admin export flow. | Pass | Manual |
| UT-23 | Unit | Export pipeline | Export report-analysis failure candidates. | GET `/admin/api/export-report-analysis-errors`. | CSV file contains low-confidence / fallback report-analysis rows. | Validated through admin export flow and store logic. | Pass | Manual + code review |
| UT-24 | Unit | HTTPS deployment | Build redirect URL correctly. | Request `http://localhost:8000/admin?x=1` while HTTPS is enabled. | Redirect points to HTTPS target preserving path and query. | Passed in `test_https_redirect.py`. | Pass | Automated |
| UT-25 | Unit | Certificate monitoring | Classify near-expiry certificate severity. | Evaluate certificate status with low remaining days. | Admin warning level becomes warn/danger based on days remaining. | Passed in `test_certificate_warning.py` and `test_ssl_utils.py`. | Pass | Automated |
| UT-26 | Unit | Split pipeline | Load fixed train/validation/test splits correctly. | Read split metadata and split files. | Split rows and ratios remain reproducible for model training. | Passed in `test_split_utils.py`. | Pass | Automated |

## 3. Automated Test Evidence

The following figures provide screenshot-style evidence for the automated regression tests that covered the model-advisory and report-analysis cases listed in the catalogue.

- Figure A1 covers the automated advisory checks mapped to UT-10 and UT-11.
- Figure A2 covers the automated report-analysis and age-aware predictor checks mapped to UT-12 through UT-18.

## 4. Detailed Test Execution Examples

### UT-12 Report numeric result analysis

- Component: Report analysis
- Objective: Interpret numeric WBC results.
- Task: Submit `WBC is 13.7`.
- Expected result: Intent resolves to `report_numeric_result_analysis` and response marks high range.
- Actual result: Passed in `test_report_analysis.py` and manual runtime verification.
- Status: Pass

### UT-15 Pediatric report analysis

- Component: Report analysis
- Objective: Apply pediatric age context.
- Task: Submit `WBC is 13 age is 10`.
- Expected result: Pediatric range is applied and result is interpreted within pediatric criteria.
- Actual result: Passed in `test_report_analysis.py` and runtime verification.
- Status: Pass

### UT-20 Report-analysis preview API

- Component: API layer
- Objective: Expose report-analysis preview rows.
- Task: GET `/admin/api/report-analysis-preview`.
- Expected result: Preview returns report-analysis retraining candidates in JSON.
- Actual result: Passed in `test_api.py`.
- Status: Pass

### UT-24 HTTPS redirect and deployment validation

- Component: HTTPS deployment
- Objective: Build redirect URL correctly.
- Task: Request `http://localhost:8000/admin?x=1` while HTTPS is enabled.
- Expected result: Redirect points to HTTPS target preserving path and query.
- Actual result: Passed in `test_https_redirect.py`.
- Status: Pass

## 5. Execution Summary

- Planned cases: 26
- Passed: 26
- Failed: 0
- Blocked: 0
- Automated regression suite at issue-close time: `50 passed`

## 6. Residual Risks

- Report analysis remains bounded and is not a diagnostic engine.
- Reference intervals are generalized and must still defer to the printed report range.
- Pediatric handling is deliberately simplified and should not be presented as full clinical decision support.