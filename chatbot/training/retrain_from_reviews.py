from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from chatbot.utils.chat_store import ChatHistoryStore
from chatbot.utils.config import load_config


def run_step(command: list[str], cwd: Path) -> None:
    print(f"Running: {' '.join(command)}")
    subprocess.run(command, cwd=str(cwd), check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description='Export reviewed queries, merge them, retrain, and optionally evaluate.')
    parser.add_argument(
        '--config',
        type=str,
        default=str(Path(__file__).resolve().parents[1] / 'config.yaml'),
        help='Path to config file',
    )
    parser.add_argument('--export-only', action='store_true', help='Only export reviewed queries to CSV.')
    parser.add_argument('--skip-eval', action='store_true', help='Skip evaluation after training.')
    parser.add_argument('--limit', type=int, default=None, help='Optional maximum number of reviewed rows to export.')
    args = parser.parse_args()

    cfg = load_config(args.config)
    store = ChatHistoryStore(cfg['storage']['postgres'])

    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    export_path = Path(__file__).resolve().parents[1] / 'data' / 'labeled' / f'reviewed_queries_{timestamp}.csv'
    written = store.export_reviewed_to_csv(export_path, limit=args.limit)
    print(f'Exported reviewed queries to {written}')

    if args.export_only:
        return

    project_root = Path(__file__).resolve().parents[2]
    run_step(
        [
            sys.executable,
            'chatbot/data/merge_dataset.py',
            '--base',
            'chatbot/data/train/intent_dataset.jsonl',
            '--external-dir',
            'chatbot/data/labeled',
            '--output',
            'chatbot/data/train/intent_dataset.jsonl',
            '--overwrite',
        ],
        cwd=project_root,
    )
    run_step(
        [sys.executable, 'chatbot/training/train_intent.py', '--config', str(Path(args.config).resolve())],
        cwd=project_root,
    )
    if not args.skip_eval:
        run_step(
            [sys.executable, 'chatbot/evaluation/evaluate.py', '--config', str(Path(args.config).resolve())],
            cwd=project_root,
        )


if __name__ == '__main__':
    main()
