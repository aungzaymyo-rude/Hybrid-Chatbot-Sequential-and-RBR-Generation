from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import Dict, List, Sequence

import numpy as np
import torch
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from torch.utils.data import DataLoader

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from chatbot.models.sequential_intent import IntentTextDataset, SequentialIntentClassifier, Vocabulary, collate_batch
from chatbot.training.dataset import build_label_maps, load_intent_dataset
from chatbot.utils.config import load_config
from chatbot.utils.preprocessing import normalize_text


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _compute_confidence(logits: torch.Tensor) -> np.ndarray:
    probs = torch.softmax(logits, dim=-1)
    conf, _ = torch.max(probs, dim=-1)
    return conf.detach().cpu().numpy()


def _load_vocab(model_dir: Path, max_length: int) -> Vocabulary:
    with (model_dir / 'vocab.json').open('r', encoding='utf-8') as handle:
        payload = json.load(handle)
    itos = payload['itos']
    stoi = {token: idx for idx, token in enumerate(itos)}
    return Vocabulary(stoi=stoi, itos=itos, max_length=max_length)


def _load_metadata(model_dir: Path) -> Dict[str, object]:
    metadata_path = model_dir / 'model_metadata.json'
    if not metadata_path.exists():
        return {}
    with metadata_path.open('r', encoding='utf-8') as handle:
        return json.load(handle)


def _token_lengths(records: Sequence[Dict[str, str]]) -> List[int]:
    return [len(normalize_text(row['text']).split()) for row in records]


def _dataset_profile(
    full_records: Sequence[Dict[str, str]],
    eval_records: Sequence[Dict[str, str]],
) -> Dict[str, object]:
    full_intent_counts = Counter(row['intent'] for row in full_records)
    eval_intent_counts = Counter(row['intent'] for row in eval_records)
    normalized_pairs = [(normalize_text(row['text']), row['intent']) for row in full_records]
    duplicate_count = len(normalized_pairs) - len(set(normalized_pairs))

    token_lengths = _token_lengths(full_records)
    char_lengths = [len(normalize_text(row['text'])) for row in full_records]
    vocab = set()
    for row in full_records:
        vocab.update(normalize_text(row['text']).split())

    counts = list(full_intent_counts.values()) or [0]
    min_count = min(counts) if counts else 0
    max_count = max(counts) if counts else 0
    imbalance_ratio = float(max_count / min_count) if min_count else 0.0

    return {
        'total_samples': len(full_records),
        'eval_samples': len(eval_records),
        'num_intents': len(full_intent_counts),
        'intent_counts': dict(sorted(full_intent_counts.items())),
        'eval_intent_counts': dict(sorted(eval_intent_counts.items())),
        'vocabulary_size': len(vocab),
        'duplicate_rows': duplicate_count,
        'duplicate_ratio': float(duplicate_count / len(full_records)) if full_records else 0.0,
        'avg_tokens': float(np.mean(token_lengths)) if token_lengths else 0.0,
        'median_tokens': float(statistics.median(token_lengths)) if token_lengths else 0.0,
        'max_tokens': max(token_lengths) if token_lengths else 0,
        'avg_chars': float(np.mean(char_lengths)) if char_lengths else 0.0,
        'median_chars': float(statistics.median(char_lengths)) if char_lengths else 0.0,
        'imbalance_ratio': imbalance_ratio,
    }


def _paper_table_row(
    metadata: Dict[str, object],
    metrics: Dict[str, object],
    dataset_profile: Dict[str, object],
) -> Dict[str, object]:
    return {
        'run_name': metadata['run_name'],
        'timestamp': metadata['timestamp'],
        'architecture': metadata['model_architecture'],
        'dataset_samples': dataset_profile['total_samples'],
        'eval_samples': dataset_profile['eval_samples'],
        'num_intents': dataset_profile['num_intents'],
        'vocabulary_size': dataset_profile['vocabulary_size'],
        'imbalance_ratio': dataset_profile['imbalance_ratio'],
        'accuracy': metrics['accuracy'],
        'f1_macro': metrics['f1_macro'],
        'f1_weighted': metrics['f1_weighted'],
        'precision_macro': metrics['precision_macro'],
        'recall_macro': metrics['recall_macro'],
        'avg_confidence': metrics['avg_confidence'],
        'batch_size': metadata['batch_size'],
        'epochs': metadata['epochs'],
        'learning_rate': metadata['learning_rate'],
        'weight_decay': metadata['weight_decay'],
    }


def _evaluate_model(
    model_dir: Path,
    records: List[Dict[str, str]],
    label2id: Dict[str, int],
    id2label: Dict[int, str],
    batch_size: int,
    device: torch.device,
) -> Dict[str, object]:
    metadata = _load_metadata(model_dir)
    max_length = int(metadata.get('max_length', 64))
    vocab = _load_vocab(model_dir, max_length=max_length)
    model = SequentialIntentClassifier(
        vocab_size=len(vocab.itos),
        embedding_dim=int(metadata.get('embedding_dim', 128)),
        hidden_dim=int(metadata.get('hidden_dim', 128)),
        num_classes=len(label2id),
        architecture=str(metadata.get('architecture', 'bilstm')),
        num_layers=int(metadata.get('num_layers', 1)),
        dropout=float(metadata.get('dropout', 0.2)),
        padding_idx=vocab.pad_id,
    )
    state = torch.load(model_dir / 'model.pt', map_location='cpu')
    model.load_state_dict(state)
    model.to(device)
    model.eval()

    normalized = [{**row, 'text': normalize_text(row['text'])} for row in records]
    dataset = IntentTextDataset(normalized, vocab=vocab, label2id=label2id)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, collate_fn=partial(collate_batch, pad_id=vocab.pad_id))

    all_preds: List[int] = []
    all_labels: List[int] = []
    all_conf: List[float] = []
    all_texts: List[str] = []

    with torch.no_grad():
        offset = 0
        for input_ids, lengths, labels in loader:
            batch_texts = [normalized[idx]['text'] for idx in range(offset, offset + labels.size(0))]
            offset += labels.size(0)

            input_ids = input_ids.to(device)
            lengths = lengths.to(device)
            labels = labels.to(device)
            logits = model(input_ids, lengths)
            preds = torch.argmax(logits, dim=-1)
            all_preds.extend(preds.cpu().tolist())
            all_labels.extend(labels.cpu().tolist())
            all_conf.extend(_compute_confidence(logits).tolist())
            all_texts.extend(batch_texts)

    target_names = [id2label[idx] for idx in range(len(id2label))]
    report = classification_report(
        all_labels,
        all_preds,
        labels=list(range(len(target_names))),
        target_names=target_names,
        output_dict=True,
        zero_division=0,
    )
    cm = confusion_matrix(all_labels, all_preds, labels=list(range(len(target_names))))

    metrics = {
        'accuracy': accuracy_score(all_labels, all_preds),
        'f1_macro': report['macro avg']['f1-score'],
        'f1_weighted': report['weighted avg']['f1-score'],
        'precision_macro': report['macro avg']['precision'],
        'recall_macro': report['macro avg']['recall'],
        'precision_weighted': report['weighted avg']['precision'],
        'recall_weighted': report['weighted avg']['recall'],
        'avg_confidence': float(np.mean(all_conf)) if all_conf else 0.0,
        'median_confidence': float(statistics.median(all_conf)) if all_conf else 0.0,
        'min_confidence': float(min(all_conf)) if all_conf else 0.0,
        'max_confidence': float(max(all_conf)) if all_conf else 0.0,
    }

    misclassifications = []
    for text, true_id, pred_id, conf in zip(all_texts, all_labels, all_preds, all_conf):
        if true_id == pred_id:
            continue
        misclassifications.append(
            {
                'text': text,
                'true_intent': id2label[true_id],
                'predicted_intent': id2label[pred_id],
                'confidence': conf,
            }
        )

    per_class = {label: report[label] for label in target_names}
    return {
        'metrics': metrics,
        'report': report,
        'per_class': per_class,
        'confusion_matrix': cm.tolist(),
        'model_metadata': metadata,
        'misclassifications': misclassifications,
    }


def _write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Dict[str, object]]) -> None:
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(description='Evaluate intent model')
    parser.add_argument('--config', type=str, default=str(Path(__file__).resolve().parents[1] / 'config.yaml'))
    parser.add_argument('--model-dir', type=str, default=None)
    parser.add_argument('--run-name', type=str, default=None)
    parser.add_argument('--batch-size', type=int, default=None)
    args = parser.parse_args()

    cfg = load_config(args.config)
    model_dir = Path(args.model_dir or cfg['training']['output_dir']).resolve()

    dataset = load_intent_dataset(cfg['data']['dataset_path'])
    label2id, id2label = build_label_maps(dataset)
    split = dataset.train_test_split(test_size=cfg['data']['test_size'], seed=cfg['training'].get('seed', 42))
    full_records = [dict(row) for row in dataset]
    eval_records = [dict(row) for row in split['test']]

    batch_size = args.batch_size or cfg['training'].get('eval_batch_size', 32)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    result = _evaluate_model(
        model_dir=model_dir,
        records=eval_records,
        label2id=label2id,
        id2label=id2label,
        batch_size=batch_size,
        device=device,
    )
    dataset_profile = _dataset_profile(full_records=full_records, eval_records=eval_records)

    run_name = args.run_name or _timestamp()
    run_dir = Path(__file__).resolve().parent / 'runs' / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        'run_name': run_name,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'model_dir': str(model_dir),
        'model_architecture': result['model_metadata'].get('architecture', cfg['model'].get('architecture', 'bilstm')),
        'dataset_path': cfg['data']['dataset_path'],
        'test_size': cfg['data']['test_size'],
        'num_labels': len(label2id),
        'batch_size': batch_size,
        'epochs': cfg['training']['epochs'],
        'learning_rate': cfg['training']['learning_rate'],
        'weight_decay': cfg['training']['weight_decay'],
    }
    paper_row = _paper_table_row(metadata=metadata, metrics=result['metrics'], dataset_profile=dataset_profile)

    with (run_dir / 'metrics.json').open('w', encoding='utf-8') as handle:
        json.dump(
            {
                'metadata': metadata,
                'dataset_profile': dataset_profile,
                'paper_summary': paper_row,
                **result,
            },
            handle,
            ensure_ascii=False,
            indent=2,
        )

    labels = [id2label[i] for i in range(len(id2label))]
    with (run_dir / 'confusion_matrix.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(['label', *labels])
        for label, row in zip(labels, result['confusion_matrix']):
            writer.writerow([label, *row])

    with (run_dir / 'per_class.json').open('w', encoding='utf-8') as handle:
        json.dump(result['per_class'], handle, ensure_ascii=False, indent=2)

    with (run_dir / 'dataset_profile.json').open('w', encoding='utf-8') as handle:
        json.dump(dataset_profile, handle, ensure_ascii=False, indent=2)

    with (run_dir / 'paper_summary.json').open('w', encoding='utf-8') as handle:
        json.dump(paper_row, handle, ensure_ascii=False, indent=2)

    _write_csv(
        run_dir / 'paper_summary.csv',
        list(paper_row.keys()),
        [paper_row],
    )
    _write_csv(
        run_dir / 'misclassifications.csv',
        ['text', 'true_intent', 'predicted_intent', 'confidence'],
        result['misclassifications'],
    )
    _write_csv(
        run_dir / 'intent_distribution.csv',
        ['intent', 'train_total', 'eval_total'],
        [
            {
                'intent': intent,
                'train_total': dataset_profile['intent_counts'].get(intent, 0),
                'eval_total': dataset_profile['eval_intent_counts'].get(intent, 0),
            }
            for intent in sorted(dataset_profile['intent_counts'])
        ],
    )

    print(f'Evaluation saved to: {run_dir}')


if __name__ == '__main__':
    main()
