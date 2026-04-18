# Hematology Lab Assistant (English-Only)

Hybrid chatbot system using BiLSTM sequential intent classifiers, medical term detection, retrieval-based response generation, safety rules, PostgreSQL logging, and an admin monitoring panel for hematology lab workflows.

Configured local models:
- `general`: the main hematology assistant for workflow, CBC, coagulation, smear, QC, and communication intents
- `report`: a blood-report-focused assistant for CBC parameter, flag, abnormality, and report-structure questions

Current `general` model intents:
- `greeting`
- `small_talk`
- `help`
- `cbc_info`
- `sample_collection`
- `rbc_term`
- `wbc_term`
- `platelet_term`
- `differential_review`
- `coag_test`
- `blood_smear`
- `quality_control`
- `critical_value_reporting`
- `capability_query`
- `thanks`
- `goodbye`
- `clarification`
- `out_of_scope`
- `unsafe_medical_request`
- `incomplete_query`
- `fallback`

Current `report` model adds these report-scope intents on top of the shared communication/report-support intents:
- `cbc_result_parameter`
- `cbc_flag_explanation`
- `anemia_related_term`
- `platelet_abnormality`
- `differential_result_explanation`
- `report_structure_help`

Non-English input returns: "Only English is supported. Please ask in English."

## Setup
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

PostgreSQL defaults used by the application:
- host: `localhost`
- port: `5432`
- database: `chatbot`
- user: `postgres`
- password: `P@ssw0rd`

These values can be overridden with `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD`.

## Data Framework (Reusable)
Data moves through stable stages so you can grow the model over time:
- `chatbot/data/raw/` contains unprocessed sources (PDFs, notes, exports)
- `chatbot/data/labeled/` contains human-labeled Q/A samples (.jsonl or .csv)
- `chatbot/data/train/` contains the final dataset used by training
- `chatbot/data/reports/` contains audits and data quality outputs

Labeled file format (CSV/JSONL):
- `text` or `utterance`
- `intent` or `label`
- `lang` (optional, defaults to `en`)

Master dataset snapshot (`chatbot/data/train/intent_dataset.jsonl`):
- Total samples: `3090`
- Total intents: `27`
- Largest classes: `cbc_info=312`, `sample_collection=214`, `wbc_term=140`, `rbc_term=140`, `coag_test=140`
- Report-expansion classes merged at `100` each: `cbc_result_parameter`, `cbc_flag_explanation`, `anemia_related_term`, `platelet_abnormality`, `differential_result_explanation`
- Communication/safety examples now include: `capability_query=164`, `clarification=144`, `thanks=141`, `goodbye=136`, `greeting=106`, `small_talk=100`, `unsafe_medical_request=108`, `out_of_scope=48`, `incomplete_query=47`, `fallback=20`

Derived model datasets:
- `chatbot/data/train/intent_dataset_general.jsonl`: `2510` samples across `21` intents
- `chatbot/data/train/intent_dataset_report.jsonl`: `2636` samples across `24` intents

Two-model dataset count summary:
- `general`: includes workflow and assistant intents such as `sample_collection`, `coag_test`, `quality_control`, `cbc_info`, `rbc_term`, `wbc_term`, `blood_smear`, plus communication/safety intents
- `report`: excludes workflow-only intents such as `sample_collection`, `coag_test`, and `quality_control`, but includes report-specific intents such as `cbc_result_parameter`, `cbc_flag_explanation`, `anemia_related_term`, `platelet_abnormality`, `differential_result_explanation`, and `report_structure_help`

Conversation expansion data:
- `chatbot/data/labeled/conversation_expansion_600.csv`: `600` new labeled conversation rows
- Added `small_talk` as a dedicated intent for social phrases such as `how are you`, `how are u`, and `how is it going`

## Build Training Dataset
Training uses one master file first:
`chatbot/data/train/intent_dataset.jsonl`

Build the master dataset once, then derive the per-model datasets from it.

Option A: real labeled data only
```bash
python chatbot/data/merge_dataset.py --external-dir chatbot/data/labeled --output chatbot/data/train/intent_dataset.jsonl --overwrite
```

Option B: synthetic baseline + real labeled data
1. Generate a baseline file:
```bash
python chatbot/data/generate_dataset.py --per-intent 120 --fallback-count 30 --output chatbot/data/train/base_300_plus.jsonl --overwrite
```

2. Merge labeled data on top of that base:
```bash
python chatbot/data/merge_dataset.py --base chatbot/data/train/base_300_plus.jsonl --external-dir chatbot/data/labeled --output chatbot/data/train/intent_dataset.jsonl --overwrite
```

Option C: add only new synthetic rows and combine them with the current dataset
```bash
python chatbot/data/generate_dataset.py --base chatbot/data/train/intent_dataset.jsonl --combine --intents cbc_info,sample_collection --per-intent 40 --output chatbot/data/train/intent_dataset.jsonl --overwrite
```
This does not rebuild the old dataset. It generates new rows starting after the current sample count for each selected intent, then de-duplicates and combines them into one final dataset.

Option D: merge one specific labeled file into the final dataset
```bash
python chatbot/data/generate_dataset_from_file.py --file chatbot/data/labeled/extra.csv --output chatbot/data/train/intent_dataset.jsonl --overwrite
```

Current real-phrasing seed files include:
- `chatbot/data/labeled/cbc_real_phrases_400.csv`
- `chatbot/data/labeled/communication_safety_real_phrases.csv`

If you need broader hematology intents later, `merge_dataset.py` now accepts all intent labels by default. Use `--allowed-intents` only when you want to restrict the merge.

After the master dataset is ready, build the two model-specific datasets:
```bash
python chatbot/data/build_model_datasets.py --config chatbot/config.yaml --overwrite
```

This produces:
- `chatbot/data/train/intent_dataset_general.jsonl`
- `chatbot/data/train/intent_dataset_report.jsonl`

Do not run all build commands one after another with `--overwrite` to the same master file unless that is exactly the dataset you want. Pick one build path, produce one master dataset file, then derive the model-specific datasets from it.

`generate_dataset.py` can now generate only new rows and optionally combine them with an existing dataset.
`merge_dataset.py` merges all labeled files from a folder.
`generate_dataset_from_file.py` merges one specific labeled file.

## Train
The current backend is a BiLSTM sequential model with vocabulary building, tokenization, embedding lookup, and padded sequence batching.

Train the `general` model:
```bash
python chatbot/training/train_intent.py --config chatbot/config.yaml --model-key general
```

Train the `report` model:
```bash
python chatbot/training/train_intent.py --config chatbot/config.yaml --model-key report
```

Artifacts are saved in:
- `chatbot/models/intent_general/`
- `chatbot/models/intent_report/`

Each model directory contains `model.pt`, `vocab.json`, `label_map.json`, `model_metadata.json`, and `training_history.json`.

## Evaluate
```bash
python chatbot/evaluation/evaluate.py --config chatbot/config.yaml --model-key general --run-name general_model_eval
python chatbot/evaluation/evaluate.py --config chatbot/config.yaml --model-key report --run-name report_model_eval
streamlit run chatbot/evaluation/dashboard.py
```
Each evaluation run now exports paper-ready artifacts inside `chatbot/evaluation/runs/<run_name>/`:
- `metrics.json`
- `dataset_profile.json`
- `paper_summary.json`
- `paper_summary.csv`
- `intent_distribution.csv`
- `misclassifications.csv`
- `confusion_matrix.csv`

Latest evaluation snapshots:
- `general_model_eval_20260417_conversation`: `2510` samples, `21` intents, accuracy `0.9841`, macro F1 `0.9676`
- `report_model_eval_20260417_conversation`: `2636` samples, `24` intents, accuracy `0.9924`, macro F1 `0.9875`

## Inference (CLI)
```bash
python chatbot/inference/run_inference.py --text "What is a CBC?" --config chatbot/config.yaml --model-key general
python chatbot/inference/run_inference.py --text "How do I read this CBC report?" --config chatbot/config.yaml --model-key report
```

## Response Layer
Intent classification is handled by the BiLSTM model. Responses for `cbc_info`, `sample_collection`, and `help` use a lightweight TF-IDF retrieval layer backed by:
`chatbot/data/knowledge/hematology_responses.jsonl`

Before retrieval, the chatbot runs a lightweight entity detector for hematology terms such as `RBC`, `WBC`, `MCV`, `PT`, and `aPTT`. This lets broad intents like `cbc_info`, `help`, `clarification`, or even `fallback` route to the most relevant hematology answer.

Communication and safety intents such as `capability_query`, `thanks`, `goodbye`, `out_of_scope`, `unsafe_medical_request`, and `incomplete_query` bypass retrieval and return controlled responses from the response layer. `clarification` can still route into a medical answer when the question includes a clear hematology term.

That means you can widen answer scope by adding curated question-answer entries for medical intents without retraining the classifier, while still keeping non-medical and unsafe requests under strict control.

## Retrieval-Based Generation Knowledge
The chatbot uses retrieval-based response generation rather than free-text generation for medical answers.

Knowledge source:
- `chatbot/data/knowledge/hematology_responses.jsonl`

Knowledge record format:
```json
{
  "intent": "rbc_term",
  "question": "What is MCV?",
  "answer": "MCV is mean corpuscular volume, the average size of red blood cells..."
}
```

How retrieval works:
1. The BiLSTM predicts an intent.
2. The entity detector looks for specific hematology terms such as `HGB`, `HCT`, `RDW`, `Neu#`, `aPTT`, or `thrombocytopenia`.
3. The routing layer retrieves within the predicted intent first for specific operational intents such as `sample_collection`, `coag_test`, `quality_control`, and `critical_value_reporting`.
4. Broad intents such as `fallback`, `help`, `clarification`, and sometimes `cbc_info` may then be refined into a more specific retrieval intent through entity detection.
5. The retriever searches the knowledge base within that intent and returns the closest curated answer.
6. If no strong retrieval match exists, the chatbot falls back to the static response template for that intent.

Why this is used:
- safer than unrestricted generative output for medical content
- easy to audit and update without retraining the classifier
- supports controlled expansion by adding new curated Q/A entries

How to extend it:
1. Add new JSONL rows to `chatbot/data/knowledge/hematology_responses.jsonl`.
2. Keep the `intent` aligned with your trained intent taxonomy.
3. Add several natural question variants for each concept.
4. Retrain the classifier only when you add new intents, not when you only add more answer knowledge for existing intents.

The current knowledge base now includes more operational coverage for:
- CBC sample rejection criteria
- clotted and underfilled EDTA samples
- CBC transport delay and stability limits
- coagulation specimen rejection and delay handling
- QC shifts, failed controls, expired controls, and documentation
- critical-value escalation, repeat verification, and documentation

## Chatbot Features
- Hematology-focused assistant UI with scope and safety panels
- Quick prompt shortcuts for common hematology questions
- Model selector for switching between the `general` and `report` local intent models
- Local browser conversation persistence
- Export chat transcript as JSON
- Suggested next-question chips after each assistant answer
- Automatic model switching when a question fits the other model better
- Per-message intent, confidence, and category display
- Controlled guardrail responses for unsafe or out-of-scope requests
- Query logging to PostgreSQL for future tuning and monitoring
- Admin monitoring panel for fallback, guardrail, confidence, review workflow, and multi-model monitoring

## API
```bash
uvicorn chatbot.api.main:app --host 0.0.0.0 --port 8000
```

Open the chat UI:
```text
http://localhost:8000/
```

The chat UI now loads the configured models from `/models`, shows a model dropdown, and sends `model_key` with each message. If the selected model is a poor fit for the question type, the backend automatically switches to the better model and the metadata line shows the switch.

Open the admin monitoring panel:
```text
http://localhost:8000/admin
```

User questions, fallback traffic, review status, and model metadata are logged in PostgreSQL.

The admin panel now supports multi-model monitoring for the current two-model setup and future additional models:
- model filter dropdown populated from `/models`
- per-model traffic, confidence, fallback, guardrail, auto-switch, and retrieval monitoring
- model-aware recent log review showing requested model vs answered model

## Production Retraining Loop
1. Open `http://localhost:8000/admin` and review fallback, guardrail, and low-confidence phrases.
2. Set `review_status` to `accepted` for phrases you want to use in retraining.
3. If the predicted intent is wrong, set `corrected_intent` in the admin panel before saving the review.
4. Use `Export current logs` in the admin panel when you want raw production traffic, or `Export reviewed CSV` when you only want accepted retraining samples.
5. Retrain from accepted reviews:
```bash
.\chatbot\.venv\Scripts\python.exe chatbot/training/retrain_from_reviews.py --config chatbot/config.yaml
```
This script will:
- export accepted reviewed queries to `chatbot/data/labeled/reviewed_queries_<timestamp>.csv`
- merge labeled data into `chatbot/data/train/intent_dataset.jsonl`
- rebuild `intent_dataset_general.jsonl` and `intent_dataset_report.jsonl`
- retrain both BiLSTM models by default
- run evaluation for both models unless `--skip-eval` is passed

Useful options:
```bash
.\chatbot\.venv\Scripts\python.exe chatbot/training/retrain_from_reviews.py --config chatbot/config.yaml --export-only
.\chatbot\.venv\Scripts\python.exe chatbot/training/retrain_from_reviews.py --config chatbot/config.yaml --skip-eval
.\chatbot\.venv\Scripts\python.exe chatbot/training/retrain_from_reviews.py --config chatbot/config.yaml --model-key report
```

## Production Redeploy
After retraining, rebuild and restart the production containers so the new model artifacts are loaded:
```bash
docker compose up --build -d
```
Use this after any change to:
- model artifacts in `chatbot/models/intent_general/`
- model artifacts in `chatbot/models/intent_report/`
- Python application code
- admin/review workflow code

## Model Selection
Configure models in `chatbot/config.yaml` and choose at runtime:
```yaml
model_default_key: general
model_registry:
  general:
    path: models/intent_general
    version: bilstm-general-v1
  report:
    path: models/intent_report
    version: bilstm-report-v1
```

CLI:
```bash
python chatbot/inference/run_inference.py --text "What is a CBC?" --model-key general
python chatbot/inference/run_inference.py --text "How do I read this CBC report?" --model-key report
```

API:
```bash
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d "{\"text\": \"What is a CBC?\", \"model_key\": \"general\"}"
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d "{\"text\": \"Explain neutrophilia in this report\", \"model_key\": \"report\"}"
```

## Docker (Production-Oriented Local Deployment)
```bash
docker compose up --build
```

This starts:
- the chatbot API on `http://localhost:8000`
- PostgreSQL on `localhost:5432` with database `chatbot`

Open API docs:
```
http://localhost:8000/docs
```
