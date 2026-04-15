# Hematology Lab Assistant (English-Only)

Hybrid chatbot system using a BiLSTM sequential intent classifier, medical term detection, response retrieval, safety rules, PostgreSQL logging, and an admin monitoring panel for hematology lab workflows. Current intents:
- `greeting`
- `help`
- `cbc_info`
- `sample_collection`
- `rbc_term`
- `wbc_term`
- `coag_test`
- `blood_smear`
- `capability_query`
- `thanks`
- `goodbye`
- `clarification`
- `out_of_scope`
- `unsafe_medical_request`
- `incomplete_query`
- `fallback`

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

## Build Training Dataset
Training uses one final file:
`chatbot/data/train/intent_dataset.jsonl`

Build that file once, then train from it.

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

Do not run all build commands one after another with `--overwrite` to the same file unless that is exactly the dataset you want. Pick one build path and produce one final dataset file.

`generate_dataset.py` can now generate only new rows and optionally combine them with an existing dataset.
`merge_dataset.py` merges all labeled files from a folder.
`generate_dataset_from_file.py` merges one specific labeled file.

## Train
The current backend is a BiLSTM sequential model with vocabulary building, tokenization, embedding lookup, and padded sequence batching.
```bash
python chatbot/training/train_intent.py --config chatbot/config.yaml
```
Artifacts are saved in `chatbot/models/intent/` as `model.pt`, `vocab.json`, `label_map.json`, and `model_metadata.json`.

## Evaluate
```bash
python chatbot/evaluation/evaluate.py --config chatbot/config.yaml
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

## Inference (CLI)
```bash
python chatbot/inference/run_inference.py --text "What is a CBC?" --config chatbot/config.yaml
```

## Response Layer
Intent classification is handled by the BiLSTM model. Responses for `cbc_info`, `sample_collection`, and `help` use a lightweight TF-IDF retrieval layer backed by:
`chatbot/data/knowledge/hematology_responses.jsonl`

Before retrieval, the chatbot runs a lightweight entity detector for hematology terms such as `RBC`, `WBC`, `MCV`, `PT`, and `aPTT`. This lets broad intents like `cbc_info`, `help`, `clarification`, or even `fallback` route to the most relevant hematology answer.

Communication and safety intents such as `capability_query`, `thanks`, `goodbye`, `out_of_scope`, `unsafe_medical_request`, and `incomplete_query` bypass retrieval and return controlled responses from the response layer. `clarification` can still route into a medical answer when the question includes a clear hematology term.

That means you can widen answer scope by adding curated question-answer entries for medical intents without retraining the classifier, while still keeping non-medical and unsafe requests under strict control.

## Chatbot Features
- Hematology-focused assistant UI with scope and safety panels
- Quick prompt shortcuts for common hematology questions
- Local browser conversation persistence
- Export chat transcript as JSON
- Structured answer cards for CBC, coagulation, smear, and QC replies
- Suggested next-question chips after each assistant answer
- Per-message intent, confidence, and category display
- Controlled guardrail responses for unsafe or out-of-scope requests
- Query logging to PostgreSQL for future tuning and monitoring
- Admin monitoring panel for fallback, guardrail, confidence, and review workflow

## API
```bash
uvicorn chatbot.api.main:app --host 0.0.0.0 --port 8000
```

Open the chat UI:
```text
http://localhost:8000/
```

Open the admin monitoring panel:
```text
http://localhost:8000/admin
```

User questions, fallback traffic, review status, and model metadata are logged in PostgreSQL.

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
- retrain the BiLSTM model
- run evaluation unless `--skip-eval` is passed

Useful options:
```bash
.\chatbot\.venv\Scripts\python.exe chatbot/training/retrain_from_reviews.py --config chatbot/config.yaml --export-only
.\chatbot\.venv\Scripts\python.exe chatbot/training/retrain_from_reviews.py --config chatbot/config.yaml --skip-eval
```

## Production Redeploy
After retraining, rebuild and restart the production containers so the new model artifacts are loaded:
```bash
docker compose up --build -d
```
Use this after any change to:
- model artifacts in `chatbot/models/intent/`
- Python application code
- admin/review workflow code

## Model Selection
Configure models in `chatbot/config.yaml` and choose at runtime:
```yaml
model_default_key: v1
model_registry:
  v1:
    path: models/intent_v1
    version: v1
  v2_large:
    path: models/intent_v2_large
    version: v2.large
```

CLI:
```bash
python chatbot/inference/run_inference.py --text "What is a CBC?" --model-key v1
```

API:
```bash
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d "{\"text\": \"What is a CBC?\", \"model_key\": \"v2_large\"}"
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
