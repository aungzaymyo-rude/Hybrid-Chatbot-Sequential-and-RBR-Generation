from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

RUNS_DIR = Path(__file__).resolve().parent / 'runs'

st.set_page_config(page_title='Evaluation Dashboard', layout='wide')

st.title('Model Evaluation Dashboard')

if not RUNS_DIR.exists():
    st.info('No evaluation runs found. Run: python chatbot/evaluation/evaluate.py')
    st.stop()

run_dirs = sorted([p for p in RUNS_DIR.iterdir() if p.is_dir()], reverse=True)
run_names = [p.name for p in run_dirs]

selected = st.sidebar.selectbox('Select Run', run_names)
selected_dir = RUNS_DIR / selected
metrics_path = selected_dir / 'metrics.json'

if not metrics_path.exists():
    st.error('metrics.json not found in selected run')
    st.stop()

with metrics_path.open('r', encoding='utf-8') as f:
    data = json.load(f)

metadata = data.get('metadata', {})
metrics = data.get('metrics', {})
per_class = data.get('per_class', {})
confusion_matrix = data.get('confusion_matrix', [])

col1, col2, col3 = st.columns(3)
col1.metric('Accuracy', f"{metrics.get('accuracy', 0):.4f}")
col2.metric('F1 (Macro)', f"{metrics.get('f1_macro', 0):.4f}")
col3.metric('F1 (Weighted)', f"{metrics.get('f1_weighted', 0):.4f}")

st.subheader('Training / Run Metadata')
meta_df = pd.DataFrame([metadata])
st.dataframe(meta_df, use_container_width=True)

st.subheader('Per-Class Metrics')
if per_class:
    per_class_df = pd.DataFrame(per_class).T
    st.dataframe(per_class_df, use_container_width=True)

st.subheader('Confusion Matrix')
if confusion_matrix:
    labels = list(per_class.keys())
    cm_df = pd.DataFrame(confusion_matrix, columns=labels, index=labels)
    fig = px.imshow(cm_df, text_auto=True, aspect='auto', color_continuous_scale='Blues')
    st.plotly_chart(fig, use_container_width=True)

st.subheader('Run History')
rows = []
for run in run_dirs:
    mp = run / 'metrics.json'
    if not mp.exists():
        continue
    with mp.open('r', encoding='utf-8') as f:
        payload = json.load(f)
    rows.append({
        'run_name': run.name,
        'timestamp': payload.get('metadata', {}).get('timestamp'),
        'accuracy': payload.get('metrics', {}).get('accuracy'),
        'f1_macro': payload.get('metrics', {}).get('f1_macro'),
        'f1_weighted': payload.get('metrics', {}).get('f1_weighted'),
        'learning_rate': payload.get('metadata', {}).get('learning_rate'),
        'batch_size': payload.get('metadata', {}).get('batch_size'),
        'warmup_ratio': payload.get('metadata', {}).get('warmup_ratio'),
    })

if rows:
    hist_df = pd.DataFrame(rows).sort_values('timestamp')
    st.dataframe(hist_df, use_container_width=True)
    fig2 = px.line(hist_df, x='timestamp', y=['f1_macro', 'accuracy'], markers=True)
    st.plotly_chart(fig2, use_container_width=True)
