from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from chatbot.utils.preprocessing import normalize_text

ALLOWED_INTENTS = {
    'greeting',
    'help',
    'cbc_info',
    'sample_collection',
    'fallback',
}



def _iter_json_objects(line: str) -> Iterable[Dict[str, str]]:
    decoder = json.JSONDecoder()
    idx = 0
    length = len(line)
    while idx < length:
        while idx < length and line[idx].isspace():
            idx += 1
        if idx >= length:
            break
        try:
            obj, end = decoder.raw_decode(line, idx)
        except json.JSONDecodeError:
            break
        if isinstance(obj, dict):
            yield obj
        idx = end

def _load_jsonl(path: Path) -> Iterable[Dict[str, str]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                for obj in _iter_json_objects(line):
                    yield obj

def _load_csv(path: Path) -> Iterable[Dict[str, str]]:
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row


def _normalize_row(row: Dict[str, str]) -> Dict[str, str] | None:
    text = (row.get('text') or row.get('utterance') or '').strip()
    intent = (row.get('intent') or row.get('label') or '').strip()
    lang = (row.get('lang') or row.get('language') or 'en').strip().lower()

    if not text or not intent:
        return None
    if intent not in ALLOWED_INTENTS:
        return None
    if lang != 'en':
        return None

    return {'text': text, 'intent': intent, 'lang': 'en'}


def _load_rows(path: Path) -> List[Dict[str, str]]:
    if path.suffix.lower() == '.jsonl':
        rows = _load_jsonl(path)
    elif path.suffix.lower() == '.csv':
        rows = _load_csv(path)
    else:
        return []

    output: List[Dict[str, str]] = []
    for row in rows:
        normalized = _normalize_row(row)
        if normalized:
            output.append(normalized)
    return output


def _dedupe(rows: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    seen: Set[Tuple[str, str]] = set()
    output: List[Dict[str, str]] = []
    for row in rows:
        key = (normalize_text(row['text']), row['intent'])
        if key in seen:
            continue
        seen.add(key)
        output.append(row)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description='Merge labeled samples from files into dataset')
    parser.add_argument(
        '--file',
        action='append',
        required=True,
        help='Path to a .csv or .jsonl file (repeatable)',
    )
    parser.add_argument(
        '--base',
        type=str,
        default=str(Path(__file__).resolve().parent / 'train' / 'intent_dataset.jsonl'),
        help='Base dataset JSONL path',
    )
    parser.add_argument(
        '--output',
        type=str,
        default=str(Path(__file__).resolve().parent / 'train' / 'intent_dataset.jsonl'),
        help='Output JSONL path',
    )
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Overwrite output file if it exists',
    )
    args = parser.parse_args()

    base_path = Path(args.base).resolve()
    output_path = Path(args.output).resolve()
    if output_path.exists() and not args.overwrite:
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        output_path = output_path.with_name(f'{output_path.stem}_merged_{timestamp}{output_path.suffix}')

    base_rows: List[Dict[str, str]] = []
    if base_path.exists():
        base_rows = list(_load_jsonl(base_path))

    file_paths = [Path(p).resolve() for p in args.file]
    new_rows: List[Dict[str, str]] = []
    for file_path in file_paths:
        if not file_path.exists():
            print(f'Skipping missing file: {file_path}')
            continue
        new_rows.extend(_load_rows(file_path))

    merged = _dedupe(base_rows + new_rows)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w', encoding='utf-8') as f:
        for row in merged:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')

    print(f'Base rows: {len(base_rows)}')
    print(f'New rows: {len(new_rows)}')
    print(f'Written: {len(merged)} -> {output_path}')


if __name__ == '__main__':
    main()
