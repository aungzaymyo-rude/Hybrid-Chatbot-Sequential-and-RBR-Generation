# Evaluation

This folder contains reusable evaluation tooling and a browser-based dashboard.

## Run Evaluation
```bash
python chatbot/evaluation/evaluate.py --config chatbot/config.yaml
```
This writes a timestamped run to:
```
chatbot/evaluation/runs/<timestamp>/
```

Artifacts:
- `metrics.json` (all metrics + metadata)
- `confusion_matrix.csv`
- `per_class.json`

## Dashboard (Browser)
```bash
streamlit run chatbot/evaluation/dashboard.py
```
The dashboard shows:
- Accuracy, F1 (macro/weighted), avg confidence
- Per-class precision/recall/F1
- Confusion matrix heatmap
- Run history with hyperparameters (batch size, lr, warmup)

## Tips
- Re-run evaluation after each training/tuning run to log a new run.
- Use `--run-name` to label experiments (e.g. `xlmr_base_lr2e5`).
