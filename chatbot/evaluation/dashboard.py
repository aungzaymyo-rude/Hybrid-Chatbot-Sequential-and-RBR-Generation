from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

RUNS_DIR = Path(__file__).resolve().parent / 'runs'

st.set_page_config(page_title='Evaluation Dashboard', layout='wide')
st.title('Evaluation Dashboard')

if not RUNS_DIR.exists():
    st.info('No evaluation runs found. Run: python chatbot/evaluation/evaluate.py')
    st.stop()


def _load_run(run_dir: Path) -> dict | None:
    metrics_path = run_dir / 'metrics.json'
    if not metrics_path.exists():
        return None
    with metrics_path.open('r', encoding='utf-8') as handle:
        return json.load(handle)


run_dirs = sorted([path for path in RUNS_DIR.iterdir() if path.is_dir()], reverse=True)
runs = {run.name: _load_run(run) for run in run_dirs}
runs = {name: payload for name, payload in runs.items() if payload is not None}

if not runs:
    st.info('No evaluation runs found. Run: python chatbot/evaluation/evaluate.py')
    st.stop()

selected_run = st.sidebar.selectbox('Select Run', list(runs.keys()))
selected = runs[selected_run]
metadata = selected.get('metadata', {})
metrics = selected.get('metrics', {})
dataset_profile = selected.get('dataset_profile', {})
per_class = selected.get('per_class', {})
confusion_matrix = selected.get('confusion_matrix', [])
misclassifications = selected.get('misclassifications', [])
paper_summary = selected.get('paper_summary', {})

summary_cols = st.columns(6)
summary_cols[0].metric('Accuracy', f"{metrics.get('accuracy', 0):.4f}")
summary_cols[1].metric('F1 Macro', f"{metrics.get('f1_macro', 0):.4f}")
summary_cols[2].metric('F1 Weighted', f"{metrics.get('f1_weighted', 0):.4f}")
summary_cols[3].metric('Precision Macro', f"{metrics.get('precision_macro', 0):.4f}")
summary_cols[4].metric('Recall Macro', f"{metrics.get('recall_macro', 0):.4f}")
summary_cols[5].metric('Avg Confidence', f"{metrics.get('avg_confidence', 0):.4f}")

tab_overview, tab_dataset, tab_classes, tab_errors, tab_history = st.tabs(
    ['Overview', 'Dataset Profile', 'Per-Class', 'Errors', 'Run History']
)

with tab_overview:
    st.subheader('Paper Summary')
    st.dataframe(pd.DataFrame([paper_summary]), use_container_width=True)

    st.subheader('Run Metadata')
    st.dataframe(pd.DataFrame([metadata]), use_container_width=True)

    if confusion_matrix and per_class:
        st.subheader('Confusion Matrix')
        labels = list(per_class.keys())
        cm_df = pd.DataFrame(confusion_matrix, columns=labels, index=labels)
        fig = px.imshow(cm_df, text_auto=True, aspect='auto', color_continuous_scale='Blues')
        fig.update_layout(xaxis_title='Predicted', yaxis_title='True')
        st.plotly_chart(fig, use_container_width=True)

with tab_dataset:
    st.subheader('Dataset Summary')
    profile_cols = st.columns(5)
    profile_cols[0].metric('Total Samples', f"{dataset_profile.get('total_samples', 0)}")
    profile_cols[1].metric('Eval Samples', f"{dataset_profile.get('eval_samples', 0)}")
    profile_cols[2].metric('Num Intents', f"{dataset_profile.get('num_intents', 0)}")
    profile_cols[3].metric('Vocabulary Size', f"{dataset_profile.get('vocabulary_size', 0)}")
    profile_cols[4].metric('Imbalance Ratio', f"{dataset_profile.get('imbalance_ratio', 0):.2f}")

    detail_cols = st.columns(4)
    detail_cols[0].metric('Avg Tokens', f"{dataset_profile.get('avg_tokens', 0):.2f}")
    detail_cols[1].metric('Median Tokens', f"{dataset_profile.get('median_tokens', 0):.2f}")
    detail_cols[2].metric('Duplicate Rows', f"{dataset_profile.get('duplicate_rows', 0)}")
    detail_cols[3].metric('Duplicate Ratio', f"{dataset_profile.get('duplicate_ratio', 0):.4f}")

    intent_counts = dataset_profile.get('intent_counts', {})
    eval_counts = dataset_profile.get('eval_intent_counts', {})
    if intent_counts:
        dist_df = pd.DataFrame(
            [
                {'intent': intent, 'dataset_count': count, 'eval_count': eval_counts.get(intent, 0)}
                for intent, count in sorted(intent_counts.items())
            ]
        )
        st.subheader('Intent Distribution')
        st.dataframe(dist_df, use_container_width=True)
        fig_dist = px.bar(dist_df, x='intent', y=['dataset_count', 'eval_count'], barmode='group')
        st.plotly_chart(fig_dist, use_container_width=True)

with tab_classes:
    st.subheader('Per-Class Metrics')
    if per_class:
        per_class_df = pd.DataFrame(per_class).T.reset_index().rename(columns={'index': 'intent'})
        st.dataframe(per_class_df, use_container_width=True)

        fig_f1 = px.bar(per_class_df, x='intent', y='f1-score', title='Per-Intent F1 Score')
        st.plotly_chart(fig_f1, use_container_width=True)

        fig_support = px.bar(per_class_df, x='intent', y='support', title='Per-Intent Support')
        st.plotly_chart(fig_support, use_container_width=True)
    else:
        st.info('No per-class metrics found in this run.')

with tab_errors:
    st.subheader('Misclassifications')
    if misclassifications:
        errors_df = pd.DataFrame(misclassifications).sort_values('confidence', ascending=False)
        st.dataframe(errors_df, use_container_width=True)
    else:
        st.success('No misclassifications recorded for this run.')

with tab_history:
    rows = []
    for run_name, payload in runs.items():
        meta = payload.get('metadata', {})
        row = {
            'run_name': run_name,
            'timestamp': meta.get('timestamp'),
            'architecture': meta.get('model_architecture'),
            'accuracy': payload.get('metrics', {}).get('accuracy'),
            'f1_macro': payload.get('metrics', {}).get('f1_macro'),
            'f1_weighted': payload.get('metrics', {}).get('f1_weighted'),
            'avg_confidence': payload.get('metrics', {}).get('avg_confidence'),
            'dataset_samples': payload.get('dataset_profile', {}).get('total_samples'),
            'vocabulary_size': payload.get('dataset_profile', {}).get('vocabulary_size'),
            'batch_size': meta.get('batch_size'),
            'epochs': meta.get('epochs'),
            'learning_rate': meta.get('learning_rate'),
        }
        rows.append(row)

    hist_df = pd.DataFrame(rows).sort_values('timestamp')
    st.dataframe(hist_df, use_container_width=True)
    metric_choice = st.selectbox('History Metric', ['f1_macro', 'f1_weighted', 'accuracy', 'avg_confidence'])
    fig_history = px.line(hist_df, x='timestamp', y=metric_choice, color='architecture', markers=True)
    st.plotly_chart(fig_history, use_container_width=True)
