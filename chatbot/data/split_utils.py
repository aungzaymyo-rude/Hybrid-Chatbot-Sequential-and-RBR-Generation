from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List

from sklearn.model_selection import train_test_split


def load_jsonl_rows(path: str | Path) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    with Path(path).open('r', encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def write_jsonl_rows(path: str | Path, rows: Iterable[Dict[str, object]]) -> int:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with target.open('w', encoding='utf-8') as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + '\n')
            count += 1
    return count


def summarize_rows(rows: List[Dict[str, object]]) -> Dict[str, int]:
    return dict(sorted(Counter(str(row.get('intent', '')) for row in rows).items()))


def build_stratified_splits(
    rows: List[Dict[str, object]],
    train_ratio: float,
    validation_ratio: float,
    test_ratio: float,
    seed: int,
) -> Dict[str, List[Dict[str, object]]]:
    total_ratio = train_ratio + validation_ratio + test_ratio
    if abs(total_ratio - 1.0) > 1e-6:
        raise ValueError(f'Split ratios must sum to 1.0. Got {total_ratio:.4f}.')
    if not rows:
        raise ValueError('Cannot split an empty dataset.')

    labels = [str(row.get('intent', '')) for row in rows]
    train_val_rows, test_rows = train_test_split(
        rows,
        test_size=test_ratio,
        random_state=seed,
        stratify=labels,
    )

    validation_share_of_train_val = validation_ratio / (train_ratio + validation_ratio)
    train_val_labels = [str(row.get('intent', '')) for row in train_val_rows]
    train_rows, validation_rows = train_test_split(
        train_val_rows,
        test_size=validation_share_of_train_val,
        random_state=seed,
        stratify=train_val_labels,
    )

    return {
        'train': list(train_rows),
        'validation': list(validation_rows),
        'test': list(test_rows),
    }


def load_split_rows(split_paths: Dict[str, str]) -> Dict[str, List[Dict[str, object]]]:
    required = ('train', 'validation', 'test')
    missing = [name for name in required if not Path(split_paths[name]).exists()]
    if missing:
        missing_paths = ', '.join(f'{name}={split_paths[name]}' for name in missing)
        raise FileNotFoundError(
            f'Missing split files: {missing_paths}. Run chatbot/data/create_splits.py first.'
        )
    return {name: load_jsonl_rows(split_paths[name]) for name in required}
