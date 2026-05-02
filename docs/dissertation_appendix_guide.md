# Dissertation Appendix and Screenshot Guide

This file maps the implemented project artefacts to the appendices and figures referenced in `/D:/Multilingual Chatbot Design/docs/dissertation_draft.md`.

## Recommended Figure Set for Main Body

### Figure 3.1 Hybrid haematology chatbot architecture
Suggested content:
- Chat UI
- FastAPI backend
- model registry
- `general` and `report` BiLSTM models
- entity detection
- TF-IDF retrieval layer
- PostgreSQL logging
- admin monitoring console
- retraining pipeline

Suggested source:
- Draw manually in Word, Visio, Draw.io, or Mermaid using the system design described in Chapter 3.

### Figure 4.1 Automated test execution summary
Suggested evidence:
- terminal screenshot showing:
  - `26 passed in 15.95s`

Suggested command:
```powershell
.\chatbot\.venv\Scripts\python.exe -m pytest -q
```

### Figure 4.2 General model evaluation summary
Suggested evidence:
- screenshot of:
  - `/D:/Multilingual Chatbot Design/chatbot/evaluation/runs/general_model_eval_split_701515/paper_summary.json`
- or Streamlit evaluation dashboard view for the `general` run

### Figure 4.3 Report model evaluation summary
Suggested evidence:
- screenshot of:
  - `/D:/Multilingual Chatbot Design/chatbot/evaluation/runs/report_model_eval_split_701515/paper_summary.json`
- or Streamlit evaluation dashboard view for the `report` run

### Figure 4.4 Admin inference trace
Suggested evidence:
- screenshot from `http://localhost:8000/admin`
- open sidebar item `Inference Trace`
- trace a phrase such as:
  - `What is aPTT?`
  - `What are the rejection criteria for a CBC sample?`

## Recommended Appendix Mapping

### Appendix A: Programme Route / Schedule
Suggested contents:
- Gantt chart
- milestone table
- weekly or sprint plan
- high-level delivery timeline

### Appendix B: Ethics Documentation
Suggested contents:
- project scope statement
- confirmation that no patient-level diagnosis or treatment was provided
- any university ethics forms if required

### Appendix C: Supervision and Control Documentation
Suggested contents:
- supervision notes
- issue-resolution notes
- selected entries from:
  - `/D:/Multilingual Chatbot Design/issues/issue_log.jsonl`

### Appendix D: Data and Split Documentation
Suggested files:
- `/D:/Multilingual Chatbot Design/chatbot/config.yaml`
- `/D:/Multilingual Chatbot Design/chatbot/data/splits/general/metadata.json`
- `/D:/Multilingual Chatbot Design/chatbot/data/splits/report/metadata.json`
- `/D:/Multilingual Chatbot Design/chatbot/data/train/intent_dataset_general.jsonl`
- `/D:/Multilingual Chatbot Design/chatbot/data/train/intent_dataset_report.jsonl`

Suggested summary points:
- master dataset count: `3250`
- `general` dataset count: `2670`
- `report` dataset count: `2636`
- split ratio: `70/15/15`

### Appendix E: UI and Admin Screenshots
Suggested screenshots:
- main chat UI
- admin `Overview`
- admin `Data Preprocessing`
- admin `Inference Trace`
- admin `Review Queue`

### Appendix F: Testing Documentation
Suggested contents:
- pytest screenshot showing `26 passed`
- short table of test modules:
  - `test_api.py`
  - `test_entity_detection.py`
  - `test_inference_postprocess.py`
  - `test_model_advisory.py`
  - `test_predictor_rules.py`
  - `test_preprocessing.py`
  - `test_routing_engine.py`
  - `test_split_utils.py`

### Appendix G: Evaluation Documentation
Suggested files:
- `/D:/Multilingual Chatbot Design/chatbot/evaluation/runs/general_model_eval_split_701515/paper_summary.json`
- `/D:/Multilingual Chatbot Design/chatbot/evaluation/runs/report_model_eval_split_701515/paper_summary.json`
- corresponding:
  - `confusion_matrix.csv`
  - `per_class.json`
  - `misclassifications.csv`
  - `dataset_profile.json`

### Appendix H: User and Deployment Guide
Suggested contents:
- local setup
- PostgreSQL configuration
- Docker Compose deployment
- retraining steps from reviewed logs

## Useful Commands for Documentation Evidence

### Start the API
```powershell
.\chatbot\.venv\Scripts\python.exe -m uvicorn chatbot.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Open evaluation dashboard
```powershell
streamlit run chatbot/evaluation/dashboard.py
```

### Retrain both models after reviewed log export
```powershell
.\chatbot\.venv\Scripts\python.exe chatbot/training/retrain_from_reviews.py --config chatbot/config.yaml
```

### Rebuild datasets and splits
```powershell
python chatbot/data/build_model_datasets.py --config chatbot/config.yaml --overwrite
python chatbot/data/create_splits.py --config chatbot/config.yaml --overwrite
```
