from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from chatbot.data.split_utils import build_stratified_splits, load_jsonl_rows, summarize_rows, write_jsonl_rows
from chatbot.utils.config import load_config, resolve_model_settings


def split_metadata(
    model_key: str,
    dataset_path: str,
    split_dir: str,
    split_counts: Dict[str, Dict[str, int]],
    train_ratio: float,
    validation_ratio: float,
    test_ratio: float,
    seed: int,
) -> Dict[str, object]:
    return {
        'model_key': model_key,
        'dataset_path': dataset_path,
        'split_dir': split_dir,
        'ratios': {
            'train': train_ratio,
            'validation': validation_ratio,
            'test': test_ratio,
        },
        'seed': seed,
        'counts': split_counts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Create fixed train/validation/test split files for each model dataset.')
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
        help='Specific model key(s) to split. Defaults to all configured model profiles.',
    )
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing split files.')
    args = parser.parse_args()

    cfg = load_config(args.config)
    train_ratio = float(cfg['data'].get('train_ratio', 0.70))
    validation_ratio = float(cfg['data'].get('validation_ratio', 0.15))
    test_ratio = float(cfg['data'].get('test_ratio', 0.15))
    seed = int(cfg['training'].get('seed', 42))

    configured_keys = list(cfg.get('data', {}).get('model_profiles', {}).keys())
    model_keys = args.model_keys or configured_keys
    if not model_keys:
        raise ValueError('No model profiles are configured under data.model_profiles.')

    for model_key in model_keys:
        settings = resolve_model_settings(cfg, model_key)
        split_paths = settings['split_paths']
        split_dir = Path(settings['split_dir']).resolve()
        dataset_path = Path(settings['dataset_path']).resolve()
        rows = load_jsonl_rows(dataset_path)
        splits = build_stratified_splits(
            rows=rows,
            train_ratio=train_ratio,
            validation_ratio=validation_ratio,
            test_ratio=test_ratio,
            seed=seed,
        )

        existing = [Path(path) for path in split_paths.values() if path and Path(path).exists()]
        if existing and not args.overwrite:
            raise FileExistsError(
                f'Split files already exist for {model_key} in {split_dir}. Use --overwrite to replace them.'
            )

        counts = {}
        for split_name in ('train', 'validation', 'test'):
            rows_written = write_jsonl_rows(split_paths[split_name], splits[split_name])
            counts[split_name] = {
                'rows': rows_written,
                'intent_counts': summarize_rows(splits[split_name]),
            }

        metadata = split_metadata(
            model_key=model_key,
            dataset_path=str(dataset_path),
            split_dir=str(split_dir),
            split_counts=counts,
            train_ratio=train_ratio,
            validation_ratio=validation_ratio,
            test_ratio=test_ratio,
            seed=seed,
        )
        Path(split_paths['metadata']).parent.mkdir(parents=True, exist_ok=True)
        with Path(split_paths['metadata']).open('w', encoding='utf-8') as handle:
            json.dump(metadata, handle, ensure_ascii=False, indent=2)

        print(f'[{model_key}] splits written to {split_dir}')
        for split_name in ('train', 'validation', 'test'):
            print(f"  {split_name}: {counts[split_name]['rows']} rows")


if __name__ == '__main__':
    main()
