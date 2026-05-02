from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from chatbot.deployment.ssl_utils import certificate_status


def _relative_to_project(path: Path, project_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_root.resolve())).replace('\\', '/')
    except ValueError:
        return str(path.resolve())


def _safe_isoformat(path: Path) -> str:
    if not path.exists():
        return ''
    return datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec='seconds')


def _count_jsonl_rows(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open('r', encoding='utf-8') as handle:
        for line in handle:
            if line.strip():
                count += 1
    return count


def _count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open('r', encoding='utf-8') as handle:
        rows = sum(1 for _ in handle)
    return max(0, rows - 1)


def _file_snapshot(path: Path, *, row_counter: str | None = None) -> dict[str, Any]:
    if row_counter == 'jsonl':
        row_count = _count_jsonl_rows(path)
    elif row_counter == 'csv':
        row_count = _count_csv_rows(path)
    else:
        row_count = None
    return {
        'path': str(path),
        'exists': path.exists(),
        'modified_at': _safe_isoformat(path),
        'size_bytes': path.stat().st_size if path.exists() else 0,
        'row_count': row_count,
    }


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open('r', encoding='utf-8') as handle:
        return json.load(handle)


def build_pipeline_snapshot(cfg: dict[str, Any], model_registry: dict[str, Any]) -> dict[str, Any]:
    package_root = Path(cfg['logging']['log_file']).resolve().parents[1]
    project_root = package_root.parent
    data_dir = package_root / 'data'
    labeled_dir = data_dir / 'labeled'
    responses_path = Path(cfg['responses']['knowledge_path']).resolve()

    labeled_files = []
    total_labeled_rows = 0
    for path in sorted(labeled_dir.glob('*')):
        if path.suffix.lower() not in {'.csv', '.jsonl'}:
            continue
        counter = 'csv' if path.suffix.lower() == '.csv' else 'jsonl'
        snapshot = _file_snapshot(path, row_counter=counter)
        labeled_files.append({'name': path.name, **snapshot})
        total_labeled_rows += int(snapshot['row_count'] or 0)

    datasets: dict[str, Any] = {
        'master': _file_snapshot(Path(cfg['data']['dataset_path']).resolve(), row_counter='jsonl'),
        'knowledge_base': _file_snapshot(responses_path, row_counter='jsonl'),
    }
    versions: list[dict[str, Any]] = []
    split_models: list[dict[str, Any]] = []
    model_artifacts: list[dict[str, Any]] = []

    for model_key, entry in model_registry.items():
        model_path = Path(entry['path']).resolve() if isinstance(entry, dict) else Path(entry).resolve()
        dataset_path = Path(cfg['data']['model_profiles'][model_key]['dataset_path']).resolve()
        split_dir = Path(cfg['data']['split_dir']).resolve() / model_key
        split_metadata_path = split_dir / 'metadata.json'
        split_metadata = _load_json(split_metadata_path)
        training_history = _load_json(model_path / 'training_history.json')
        model_metadata = _load_json(model_path / 'model_metadata.json')

        datasets[model_key] = _file_snapshot(dataset_path, row_counter='jsonl')
        versions.extend(
            [
                {
                    'component': f'{model_key} dataset',
                    'version': datasets[model_key]['modified_at'] or 'missing',
                    'path': datasets[model_key]['path'],
                },
                {
                    'component': f'{model_key} model',
                    'version': entry.get('version', '') if isinstance(entry, dict) else '',
                    'path': str(model_path),
                },
                {
                    'component': f'{model_key} split metadata',
                    'version': _safe_isoformat(split_metadata_path) or 'missing',
                    'path': str(split_metadata_path),
                },
            ]
        )

        split_models.append(
            {
                'model_key': model_key,
                'split_dir': str(split_dir),
                'ratios': split_metadata.get('ratios', {}),
                'counts': split_metadata.get('counts', {}),
                'modified_at': _safe_isoformat(split_metadata_path),
            }
        )
        model_artifacts.append(
            {
                'model_key': model_key,
                'version': entry.get('version', '') if isinstance(entry, dict) else '',
                'path': str(model_path),
                'modified_at': _safe_isoformat(model_path / 'model.pt'),
                'best_epoch': training_history.get('best_epoch'),
                'best_f1': training_history.get('best_f1'),
                'architecture': model_metadata.get('architecture', cfg['model'].get('architecture', 'bilstm')),
                'train_size': training_history.get('train_size'),
                'validation_size': training_history.get('validation_size'),
            }
        )

    versions.extend(
        [
            {
                'component': 'master dataset',
                'version': datasets['master']['modified_at'] or 'missing',
                'path': datasets['master']['path'],
            },
            {
                'component': 'knowledge base',
                'version': datasets['knowledge_base']['modified_at'] or 'missing',
                'path': datasets['knowledge_base']['path'],
            },
            {
                'component': 'config',
                'version': _safe_isoformat(package_root / 'config.yaml') or 'missing',
                'path': str(package_root / 'config.yaml'),
            },
        ]
    )

    snapshot = {
        'ingestion': {
            'labeled_file_count': len(labeled_files),
            'total_labeled_rows': total_labeled_rows,
            'labeled_files': labeled_files[-12:],
            'datasets': datasets,
        },
        'versioning': {
            'default_model_key': cfg.get('model_default_key', ''),
            'fallback_threshold': cfg['inference'].get('threshold'),
            'split_dir': str(Path(cfg['data']['split_dir']).resolve()),
            'knowledge_path': str(responses_path),
            'certificate': certificate_status(cfg),
            'components': versions,
        },
        'splits': {
            'policy': {
                'train_ratio': cfg['data'].get('train_ratio'),
                'validation_ratio': cfg['data'].get('validation_ratio'),
                'test_ratio': cfg['data'].get('test_ratio'),
                'seed': cfg['training'].get('seed'),
            },
            'models': split_models,
        },
        'models': model_artifacts,
    }
    for dataset_entry in snapshot['ingestion']['datasets'].values():
        dataset_entry['display_path'] = _relative_to_project(Path(dataset_entry['path']), project_root)

    for labeled_entry in snapshot['ingestion']['labeled_files']:
        labeled_entry['display_path'] = _relative_to_project(Path(labeled_entry['path']), project_root)

    for component in snapshot['versioning']['components']:
        component['display_path'] = _relative_to_project(Path(component['path']), project_root)

    for split_entry in snapshot['splits']['models']:
        split_entry['display_path'] = _relative_to_project(Path(split_entry['split_dir']), project_root)

    for model_entry in snapshot['models']:
        model_entry['display_path'] = _relative_to_project(Path(model_entry['path']), project_root)

    snapshot['versioning']['knowledge_display_path'] = _relative_to_project(responses_path, project_root)
    snapshot['versioning']['split_display_path'] = _relative_to_project(Path(cfg['data']['split_dir']).resolve(), project_root)
    certificate = snapshot['versioning']['certificate']
    if certificate.get('certfile'):
        certificate['certfile_display_path'] = _relative_to_project(Path(certificate['certfile']), project_root)
    if certificate.get('keyfile'):
        certificate['keyfile_display_path'] = _relative_to_project(Path(certificate['keyfile']), project_root)
    return snapshot
