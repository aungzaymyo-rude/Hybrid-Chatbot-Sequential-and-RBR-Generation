from __future__ import annotations

import argparse
import json
import random
import sys
from functools import partial
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import torch
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from torch import nn
from torch.utils.data import DataLoader

from chatbot.data.split_utils import load_split_rows
from chatbot.models.sequential_intent import (
    IntentTextDataset,
    SequentialIntentClassifier,
    build_vocab,
    collate_batch,
)
from chatbot.training.dataset import build_label_maps, load_intent_dataset
from chatbot.utils.config import load_config, resolve_model_settings
from chatbot.utils.logging import setup_logging
from chatbot.utils.preprocessing import normalize_text


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def compute_metrics(labels: List[int], preds: List[int]) -> Dict[str, float]:
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels,
        preds,
        average='weighted',
        zero_division=0,
    )
    return {
        'accuracy': accuracy_score(labels, preds),
        'f1': f1,
        'precision': precision,
        'recall': recall,
    }


def save_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def evaluate(model, loader, device) -> tuple[float, List[int], List[int]]:
    model.eval()
    loss_fn = nn.CrossEntropyLoss()
    total_loss = 0.0
    labels_all: List[int] = []
    preds_all: List[int] = []
    with torch.no_grad():
        for input_ids, lengths, labels in loader:
            input_ids = input_ids.to(device)
            lengths = lengths.to(device)
            labels = labels.to(device)
            logits = model(input_ids, lengths)
            loss = loss_fn(logits, labels)
            total_loss += loss.item() * labels.size(0)
            preds = torch.argmax(logits, dim=1)
            labels_all.extend(labels.cpu().tolist())
            preds_all.extend(preds.cpu().tolist())
    avg_loss = total_loss / max(1, len(labels_all))
    return avg_loss, labels_all, preds_all


def main() -> None:
    parser = argparse.ArgumentParser(description='Train BiLSTM intent classifier')
    parser.add_argument(
        '--config',
        type=str,
        default=str(Path(__file__).resolve().parents[1] / 'config.yaml'),
        help='Path to config file',
    )
    parser.add_argument(
        '--model-key',
        type=str,
        default=None,
        help='Configured model key to train (for example: general or report).',
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    model_settings = resolve_model_settings(cfg, args.model_key)
    logger = setup_logging(cfg['logging']['log_file'], cfg['logging'].get('level', 'INFO'))
    seed = int(cfg['training'].get('seed', 42))
    set_seed(seed)

    dataset = load_intent_dataset(model_settings['dataset_path'])
    label2id, id2label = build_label_maps(dataset)
    split_rows = load_split_rows(model_settings['split_paths'])
    train_records = [
        {
            'text': normalize_text(str(row['text'])),
            'intent': str(row['intent']),
            'lang': str(row.get('lang', 'en')),
        }
        for row in split_rows['train']
    ]
    validation_records = [
        {
            'text': normalize_text(str(row['text'])),
            'intent': str(row['intent']),
            'lang': str(row.get('lang', 'en')),
        }
        for row in split_rows['validation']
    ]

    model_cfg = cfg['model']
    training_cfg = cfg['training']
    max_length = int(model_cfg.get('max_length', 64))
    vocab = build_vocab(
        (row['text'] for row in train_records),
        min_freq=int(model_cfg.get('min_freq', 1)),
        max_vocab_size=int(model_cfg.get('max_vocab_size', 10000)),
        max_length=max_length,
    )

    train_dataset = IntentTextDataset(train_records, vocab=vocab, label2id=label2id)
    validation_dataset = IntentTextDataset(validation_records, vocab=vocab, label2id=label2id)
    collate = partial(collate_batch, pad_id=vocab.pad_id)

    train_loader = DataLoader(
        train_dataset,
        batch_size=int(training_cfg['batch_size']),
        shuffle=True,
        collate_fn=collate,
    )
    validation_loader = DataLoader(
        validation_dataset,
        batch_size=int(training_cfg['eval_batch_size']),
        shuffle=False,
        collate_fn=collate,
    )

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = SequentialIntentClassifier(
        vocab_size=len(vocab.itos),
        embedding_dim=int(model_cfg.get('embedding_dim', 128)),
        hidden_dim=int(model_cfg.get('hidden_dim', 128)),
        num_classes=len(label2id),
        architecture=str(model_cfg.get('architecture', 'bilstm')),
        num_layers=int(model_cfg.get('num_layers', 1)),
        dropout=float(model_cfg.get('dropout', 0.2)),
        padding_idx=vocab.pad_id,
    ).to(device)

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(training_cfg['learning_rate']),
        weight_decay=float(training_cfg['weight_decay']),
    )
    loss_fn = nn.CrossEntropyLoss()

    best_state = None
    best_f1 = -1.0
    best_epoch = 0
    history: List[Dict[str, float]] = []

    logger.info(
        'Starting %s training with dataset=%s split_dir=%s output_dir=%s',
        model_settings['model_key'],
        model_settings['dataset_path'],
        model_settings['split_dir'],
        model_settings['output_dir'],
    )
    for epoch in range(1, int(training_cfg['epochs']) + 1):
        model.train()
        running_loss = 0.0
        seen = 0
        for input_ids, lengths, labels in train_loader:
            input_ids = input_ids.to(device)
            lengths = lengths.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()
            logits = model(input_ids, lengths)
            loss = loss_fn(logits, labels)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            running_loss += loss.item() * labels.size(0)
            seen += labels.size(0)

        train_loss = running_loss / max(1, seen)
        validation_loss, validation_labels, validation_preds = evaluate(model, validation_loader, device)
        metrics = compute_metrics(validation_labels, validation_preds)
        epoch_record = {'epoch': float(epoch), 'train_loss': train_loss, 'validation_loss': validation_loss, **metrics}
        history.append(epoch_record)
        logger.info('Epoch %s metrics: %s', epoch, epoch_record)

        if metrics['f1'] > best_f1:
            best_f1 = metrics['f1']
            best_epoch = epoch
            best_state = {key: value.cpu() for key, value in model.state_dict().items()}

    if best_state is not None:
        model.load_state_dict(best_state)

    final_validation_loss, final_labels, final_preds = evaluate(model, validation_loader, device)
    final_metrics = compute_metrics(final_labels, final_preds)
    final_metrics['validation_loss'] = final_validation_loss
    logger.info('Validation metrics: %s', final_metrics)

    output_dir = Path(model_settings['output_dir'])
    output_dir.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), output_dir / 'model.pt')
    save_json(output_dir / 'label_map.json', label2id)
    save_json(output_dir / 'vocab.json', {'itos': vocab.itos})
    save_json(
        output_dir / 'model_metadata.json',
        {
            'model_type': 'sequential',
            'architecture': model_cfg.get('architecture', 'bilstm'),
            'embedding_dim': int(model_cfg.get('embedding_dim', 128)),
            'hidden_dim': int(model_cfg.get('hidden_dim', 128)),
            'num_layers': int(model_cfg.get('num_layers', 1)),
            'dropout': float(model_cfg.get('dropout', 0.2)),
            'max_length': max_length,
            'min_freq': int(model_cfg.get('min_freq', 1)),
            'max_vocab_size': int(model_cfg.get('max_vocab_size', 10000)),
            'num_labels': len(label2id),
            'pad_id': vocab.pad_id,
            'unk_id': vocab.unk_id,
            'model_key': model_settings['model_key'],
            'dataset_path': model_settings['dataset_path'],
            'split_dir': model_settings['split_dir'],
            'version': model_settings['version'],
        },
    )
    save_json(
        output_dir / 'training_history.json',
        {
            'epochs': history,
            'best_f1': best_f1,
            'best_epoch': best_epoch,
            'split_paths': model_settings['split_paths'],
            'train_size': len(train_records),
            'validation_size': len(validation_records),
            'seed': seed,
        },
    )

    logger.info('Model saved to %s', output_dir)


if __name__ == '__main__':
    main()
