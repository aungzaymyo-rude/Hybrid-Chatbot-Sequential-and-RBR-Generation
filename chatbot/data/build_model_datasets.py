from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from chatbot.utils.config import load_config, resolve_model_settings


def load_jsonl(path: Path) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    with path.open('r', encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: Iterable[Dict[str, object]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open('w', encoding='utf-8') as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + '\n')
            count += 1
    return count


def build_dataset_rows(source_rows: List[Dict[str, object]], intents: List[str]) -> List[Dict[str, object]]:
    allowed = set(intents)
    return [row for row in source_rows if str(row.get('intent', '')) in allowed]


def summarize(rows: List[Dict[str, object]]) -> Dict[str, int]:
    return dict(sorted(Counter(str(row.get('intent', '')) for row in rows).items()))


def main() -> None:
    parser = argparse.ArgumentParser(description='Build model-specific training datasets from the master dataset.')
    parser.add_argument(
        '--config',
        type=str,
        default=str(Path(__file__).resolve().parents[1] / 'config.yaml'),
        help='Path to config file.',
    )
    parser.add_argument(
        '--model-key',
        action='append',
        dest='model_keys',
        default=None,
        help='Specific model key(s) to build. Defaults to every configured model profile.',
    )
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing model dataset files.')
    args = parser.parse_args()

    cfg = load_config(args.config)
    master_path = Path(cfg['data']['dataset_path']).resolve()
    source_rows = load_jsonl(master_path)

    configured_keys = list(cfg.get('data', {}).get('model_profiles', {}).keys())
    model_keys = args.model_keys or configured_keys
    if not model_keys:
        raise ValueError('No model profiles are configured under data.model_profiles.')

    print(f'Master dataset: {master_path}')
    print(f'Master rows: {len(source_rows)}')

    for model_key in model_keys:
        settings = resolve_model_settings(cfg, model_key)
        dataset_path = Path(settings['dataset_path']).resolve()
        intents = settings['intents']
        if not intents:
            raise ValueError(f'No intents configured for model profile: {model_key}')
        if dataset_path.exists() and not args.overwrite:
            raise FileExistsError(f'Dataset already exists: {dataset_path}. Use --overwrite to replace it.')

        model_rows = build_dataset_rows(source_rows, intents)
        written = write_jsonl(dataset_path, model_rows)
        counts = summarize(model_rows)

        print(f'[{model_key}] -> {dataset_path}')
        print(f'  rows: {written}')
        print(f'  intents: {len(counts)}')
        print(f'  counts: {counts}')


if __name__ == '__main__':
    main()
