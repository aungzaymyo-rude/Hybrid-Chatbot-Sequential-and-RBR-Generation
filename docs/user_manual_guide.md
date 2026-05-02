# User Manual for the Hybrid Haematology Chatbot

## 1. Purpose of the Manual

This manual explains how to install, run, monitor, retrain, and deploy the hybrid haematology chatbot. It is intended for supervisors, markers, developers, or administrators who need to operate the system directly.

The chatbot is a bounded medical laboratory assistant. It supports haematology terminology, complete blood count questions, coagulation specimen handling, blood smear topics, quality control, critical value reporting, and CBC report-support questions. It does not provide diagnosis, treatment recommendations, or patient-specific clinical decisions.

## 2. System Overview

The implemented system contains the following major parts:

- FastAPI backend for chat, admin, and monitoring endpoints.
- Two BiLSTM intent models:
  - `general` for laboratory workflow, specimen, coagulation, QC, smear, and communication intents.
  - `report` for CBC parameter, flag, abnormality, and report-structure questions.
- Retrieval-based response generation using a curated haematology knowledge base.
- PostgreSQL logging for production monitoring.
- Browser-based chat UI and admin MLOps console.
- Dataset build, split, training, evaluation, and retraining scripts.
- Docker Compose for containerised deployment.

## 3. Prerequisites

### 3.1 Direct Installation

The following software is required:

- Python `3.11` or later.
- PostgreSQL running on the local machine or another reachable host.
- `pip` and `venv` support.
- Git, if the project is cloned from a repository.

### 3.2 Container Deployment

The following software is required:

- Docker Desktop or Docker Engine.
- Docker Compose support.
- At least one free application port; this project commonly uses `8000`.

## 4. Default PostgreSQL Configuration

The application is configured to use the following defaults unless environment variables override them:

- host: `localhost`
- port: `5432`
- database: `chatbot`
- user: `postgres`
- password: `P@ssw0rd`

Environment variables supported by the application:

- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`

## 5. Direct Installation and Startup

### 5.1 Clone or open the project

Example:

```powershell
git clone <repository-url>
cd "D:\Multilingual Chatbot Design"
```

### 5.2 Create and activate the virtual environment

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 5.3 Install dependencies

```powershell
pip install -r requirements.txt
```

### 5.4 Confirm PostgreSQL availability

Create the database if required and make sure the configured user can connect.

### 5.5 Start the API server

```powershell
.\chatbot\.venv\Scripts\python.exe -m uvicorn chatbot.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5.6 Open the interfaces

- Chat UI: `http://localhost:8000/`
- Admin panel: `http://localhost:8000/admin`
- OpenAPI docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

## 6. Containerised Deployment

### 6.1 Build and start the services

```powershell
docker compose up --build -d
```

This command starts:

- the chatbot API container
- the PostgreSQL container configured in `docker-compose.yml`

### 6.2 Stop the services

```powershell
docker compose down
```

### 6.3 Rebuild after code or model changes

```powershell
docker compose up --build -d
```

### 6.4 Check running containers

```powershell
docker ps
```

## 7. Using the Chatbot

### 7.1 Select a model

The UI exposes two model choices:

- `General Hematology Model`
- `Report Analysis Model`

If a question belongs more strongly to the alternative model, the backend can auto-switch to the better model before answering.

### 7.2 Example questions for the general model

- `Which tube is used for CBC?`
- `What is aPTT?`
- `What is hematology analyzer quality control?`
- `What is a peripheral blood smear?`

### 7.3 Example questions for the report model

- `How do I read this CBC report?`
- `What is HCT in this report?`
- `What does neutrophilia mean?`
- `What does thrombocytopenia mean?`

### 7.4 Scope restrictions

The chatbot should not be used for:

- treatment advice
- drug prescription
- injection guidance
- patient-specific diagnosis
- final clinical interpretation of full patient cases

## 8. Admin Panel Usage

The admin panel is organised around MLOps workflow visibility.

### 8.1 Overview

This section shows:

- total chats
- average confidence
- fallback rate
- guardrail rate
- low-confidence rate
- retrieval rate
- auto-switch rate
- recent logs and top intents

### 8.2 Inference Trace

This section allows a phrase to be analysed through the backend pipeline. It shows:

- text normalisation
- tokenisation
- vocabulary IDs
- top intent scores
- entity matches
- retrieval candidates
- final routing decision

### 8.3 Data Preprocessing

This section shows:

- labelled-source counts
- dataset counts
- split metadata
- version-relevant artefacts

### 8.4 Review Queue

This section is used to:

- inspect user queries
- mark records as reviewed
- set `accepted` or `rejected` review status
- provide `corrected_intent` values for retraining
- export reviewed training candidates

## 9. Dataset and Training Workflow

### 9.1 Build the master dataset

Option A - merge labelled files only:

```powershell
python chatbot/data/merge_dataset.py --external-dir chatbot/data/labeled --output chatbot/data/train/intent_dataset.jsonl --overwrite
```

### 9.2 Build model-specific datasets

```powershell
python chatbot/data/build_model_datasets.py --config chatbot/config.yaml --overwrite
```

### 9.3 Create fixed train/validation/test splits

```powershell
python chatbot/data/create_splits.py --config chatbot/config.yaml --overwrite
```

### 9.4 Train the models

```powershell
python chatbot/training/train_intent.py --config chatbot/config.yaml --model-key general
python chatbot/training/train_intent.py --config chatbot/config.yaml --model-key report
```

### 9.5 Evaluate the models

```powershell
python chatbot/evaluation/evaluate.py --config chatbot/config.yaml --model-key general --run-name general_model_eval
python chatbot/evaluation/evaluate.py --config chatbot/config.yaml --model-key report --run-name report_model_eval
```

### 9.6 Open the evaluation dashboard

```powershell
streamlit run chatbot/evaluation/dashboard.py
```

## 10. Retraining from Reviewed Production Logs

### 10.1 Review logs in the admin panel

Use the `Review Queue` section to:

- inspect low-confidence or incorrect predictions
- set `review_status` to `accepted`
- provide a `corrected_intent` if needed

### 10.2 Run the retraining pipeline

```powershell
.\chatbot\.venv\Scripts\python.exe chatbot/training/retrain_from_reviews.py --config chatbot/config.yaml
```

Optional modes:

```powershell
.\chatbot\.venv\Scripts\python.exe chatbot/training/retrain_from_reviews.py --config chatbot/config.yaml --export-only
.\chatbot\.venv\Scripts\python.exe chatbot/training/retrain_from_reviews.py --config chatbot/config.yaml --skip-eval
```

### 10.3 What the retraining pipeline does

The script:

- exports accepted reviewed logs to a labelled CSV file
- merges them into the master labelled dataset
- rebuilds model-specific datasets
- recreates fixed splits
- retrains the selected models
- runs evaluation unless `--skip-eval` is used

## 11. Production Redeployment

After retraining or configuration changes, redeploy the production container:

```powershell
docker compose up --build -d
```

This step ensures that the latest model artefacts, knowledge-base updates, and code changes are included in the running container.

## 12. File Locations

Important project paths:

- configuration: `chatbot/config.yaml`
- master dataset: `chatbot/data/train/intent_dataset.jsonl`
- model datasets:
  - `chatbot/data/train/intent_dataset_general.jsonl`
  - `chatbot/data/train/intent_dataset_report.jsonl`
- split files:
  - `chatbot/data/splits/general/`
  - `chatbot/data/splits/report/`
- model artefacts:
  - `chatbot/models/intent_general/`
  - `chatbot/models/intent_report/`
- retrieval knowledge base:
  - `chatbot/data/knowledge/hematology_responses.jsonl`
- evaluation outputs:
  - `chatbot/evaluation/runs/`

## 13. Troubleshooting

### 13.1 Port already in use

If `8000` is already occupied, either stop the conflicting process or run the API on another port.

### 13.2 Admin page looks stale

Use a hard refresh:

```text
Ctrl + F5
```

### 13.3 PostgreSQL connection fails

Check:

- PostgreSQL is running
- credentials match the environment variables or defaults
- the `chatbot` database exists
- firewall or host restrictions are not blocking the connection

### 13.4 Model artefact error

If an error such as `label_map.json not found` appears, retrain the missing model profile and verify that the model directory contains the required artefacts.

### 13.5 Trace or admin endpoint not found

Restart the API server. New backend routes require the Python process to reload.

## 14. Operational Good Practice

- Keep the `test` split untouched for final evaluation.
- Add new labelled data through the labelled-data pipeline rather than editing derived split files manually.
- Use the review queue to capture real user phrasing.
- Expand the retrieval knowledge base when the intent is correct but the answer is too general.
- Retrain the classifier when new intents or new intent distributions are introduced.

## 15. Summary

The chatbot can be used as a locally deployed or containerised haematology laboratory assistant. Its operation depends on correct PostgreSQL availability, model artefacts, retrieval knowledge, and an active admin review process. The safest workflow is to treat the system as a bounded assistant, monitor production logs continuously, and improve the model through controlled reviewed-data retraining.
