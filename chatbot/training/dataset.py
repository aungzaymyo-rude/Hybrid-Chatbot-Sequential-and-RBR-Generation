from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

from datasets import Dataset, load_dataset


def load_intent_dataset(path: str | Path) -> Dataset:
    dataset_path = str(Path(path).resolve())
    data = load_dataset('json', data_files=dataset_path)
    return data['train']


def build_label_maps(dataset: Dataset) -> Tuple[Dict[str, int], Dict[int, str]]:
    labels = sorted(set(dataset['intent']))
    label2id = {label: idx for idx, label in enumerate(labels)}
    id2label = {idx: label for label, idx in label2id.items()}
    return label2id, id2label
