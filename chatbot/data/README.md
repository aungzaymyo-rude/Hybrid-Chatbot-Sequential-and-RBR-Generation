# Data Framework

## Folder Layout
- `raw/`      : Unprocessed source material (PDFs, notes, exports)
- `labeled/`  : Human-labeled Q/A samples (`.jsonl` or `.csv`)
- `train/`    : Final training dataset used by the model
- `reports/`  : Data quality and audit outputs (optional)

## Labeled File Format
Use `.jsonl` or `.csv` with these fields:
- `text` (or `utterance`)
- `intent` (or `label`)
- `lang` (optional, defaults to `en`)

Allowed intents:
- `greeting`
- `help`
- `cbc_info`
- `sample_collection`
- `fallback`

## Build Training Dataset
Training reads one final file:
`train/intent_dataset.jsonl`

Build that file once before training.

Option A: real labeled data only
```bash
python chatbot/data/merge_dataset.py --external-dir chatbot/data/labeled --output chatbot/data/train/intent_dataset.jsonl --overwrite
```

Option B: synthetic baseline + labeled data
1. Create a baseline file:
```bash
python chatbot/data/generate_dataset.py --per-intent 120 --fallback-count 30 --output chatbot/data/train/base_300_plus.jsonl --overwrite
```

2. Merge labeled data onto that base:
```bash
python chatbot/data/merge_dataset.py --base chatbot/data/train/base_300_plus.jsonl --external-dir chatbot/data/labeled --output chatbot/data/train/intent_dataset.jsonl --overwrite
```

Option C: merge one specific labeled file
```bash
python chatbot/data/generate_dataset_from_file.py --file chatbot/data/labeled/extra.csv --output chatbot/data/train/intent_dataset.jsonl --overwrite
```

Do not run all options in sequence with `--overwrite` to the same file. The last command replaces the previous result.
