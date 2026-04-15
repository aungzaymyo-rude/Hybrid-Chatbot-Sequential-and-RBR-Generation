from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from chatbot.utils.preprocessing import normalize_text


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
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                for obj in _iter_json_objects(line):
                    yield obj


def _load_csv(path: Path) -> Iterable[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            yield row


def _iter_external_files(folder: Path) -> Iterable[Path]:
    for path in folder.rglob("*"):
        if path.suffix.lower() in {".jsonl", ".csv"}:
            yield path


def _normalize_row(row: Dict[str, str], source: str, allowed_intents: set[str] | None) -> Dict[str, str] | None:
    text = (row.get("text") or row.get("utterance") or "").strip()
    intent = (row.get("intent") or row.get("label") or "").strip()
    lang = (row.get("lang") or row.get("language") or "en").strip().lower()

    if not text or not intent:
        return None
    if allowed_intents and intent not in allowed_intents:
        return None
    if lang != "en":
        return None

    return {"text": text, "intent": intent, "lang": "en", "source": source}


def _load_rows(path: Path, allowed_intents: set[str] | None) -> List[Dict[str, str]]:
    source = str(path)
    rows: List[Dict[str, str]] = []
    loader = _load_jsonl if path.suffix.lower() == ".jsonl" else _load_csv
    for row in loader(path):
        normalized = _normalize_row(row, source, allowed_intents)
        if normalized:
            rows.append(normalized)
    return rows


def _dedupe(rows: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    seen: Set[Tuple[str, str]] = set()
    output: List[Dict[str, str]] = []
    for row in rows:
        key = (normalize_text(row["text"]), row["intent"])
        if key in seen:
            continue
        seen.add(key)
        output.append({"text": row["text"], "intent": row["intent"], "lang": "en"})
    return output


def _parse_allowed_intents(raw: str | None) -> set[str] | None:
    if not raw:
        return None
    values = {item.strip() for item in raw.split(",") if item.strip()}
    return values or None


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge external labeled data into intent dataset")
    parser.add_argument(
        "--base",
        type=str,
        default=str(Path(__file__).resolve().parent / "train" / "intent_dataset.jsonl"),
        help="Base dataset JSONL path",
    )
    parser.add_argument(
        "--external-dir",
        type=str,
        default=str(Path(__file__).resolve().parent / "labeled"),
        help="Folder containing external .jsonl/.csv files",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(Path(__file__).resolve().parent / "train" / "intent_dataset.jsonl"),
        help="Output JSONL path",
    )
    parser.add_argument(
        "--allowed-intents",
        type=str,
        default=None,
        help="Optional comma-separated allowlist of intents. Default keeps every intent found in the input files.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite output file if it exists",
    )
    args = parser.parse_args()

    base_path = Path(args.base).resolve()
    external_dir = Path(args.external_dir).resolve()
    output_path = Path(args.output).resolve()
    allowed_intents = _parse_allowed_intents(args.allowed_intents)
    if output_path.exists() and not args.overwrite:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_path = output_path.with_name(f"{output_path.stem}_merged_{timestamp}{output_path.suffix}")

    base_rows: List[Dict[str, str]] = []
    if base_path.exists():
        base_rows = list(_load_jsonl(base_path))

    external_rows: List[Dict[str, str]] = []
    if external_dir.exists():
        for file_path in _iter_external_files(external_dir):
            external_rows.extend(_load_rows(file_path, allowed_intents))

    merged = _dedupe(base_rows + external_rows)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in merged:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Base rows: {len(base_rows)}")
    print(f"External rows: {len(external_rows)}")
    print(f"Written: {len(merged)} -> {output_path}")


if __name__ == "__main__":
    main()
