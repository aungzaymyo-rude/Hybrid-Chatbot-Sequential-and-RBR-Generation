from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import Dict, List

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


def evaluate(
    model_dir: Path,
    records: List[Dict[str, str]],
    label2id: Dict[str, int],
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

    with torch.no_grad():
        for input_ids, lengths, labels in loader:
            input_ids = input_ids.to(device)
            lengths = lengths.to(device)
            labels = labels.to(device)
            logits = model(input_ids, lengths)
            preds = torch.argmax(logits, dim=-1)
            all_preds.extend(preds.cpu().tolist())
            all_labels.extend(labels.cpu().tolist())
            all_conf.extend(_compute_confidence(logits).tolist())

    report = classification_report(all_labels, all_preds, output_dict=True, zero_division=0)
    cm = confusion_matrix(all_labels, all_preds)

    metrics = {
        'accuracy': accuracy_score(all_labels, all_preds),
        'f1_macro': report['macro avg']['f1-score'],
        'f1_weighted': report['weighted avg']['f1-score'],
        'precision_macro': report['macro avg']['precision'],
        'recall_macro': report['macro avg']['recall'],
        'precision_weighted': report['weighted avg']['precision'],
        'recall_weighted': report['weighted avg']['recall'],
        'avg_confidence': float(np.mean(all_conf)) if all_conf else 0.0,
    }

    per_class = {k: v for k, v in report.items() if k.isdigit()}
    return {
        'metrics': metrics,
        'report': report,
        'per_class': per_class,
        'confusion_matrix': cm.tolist(),
        'model_metadata': metadata,
    }


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
    eval_records = [dict(row) for row in split['test']]

    batch_size = args.batch_size or cfg['training'].get('eval_batch_size', 32)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    result = evaluate(model_dir=model_dir, records=eval_records, label2id=label2id, batch_size=batch_size, device=device)

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

    with (run_dir / 'metrics.json').open('w', encoding='utf-8') as handle:
        json.dump({'metadata': metadata, **result}, handle, ensure_ascii=False, indent=2)

    with (run_dir / 'confusion_matrix.csv').open('w', encoding='utf-8') as handle:
        handle.write(','.join([id2label[i] for i in range(len(id2label))]) + '\n')
        for row in result['confusion_matrix']:
            handle.write(','.join(str(value) for value in row) + '\n')

    with (run_dir / 'per_class.json').open('w', encoding='utf-8') as handle:
        json.dump(result['per_class'], handle, ensure_ascii=False, indent=2)

    print(f'Evaluation saved to: {run_dir}')


if __name__ == '__main__':
    main()
