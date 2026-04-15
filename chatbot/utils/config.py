from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml


def _resolve_path(base_dir: Path, value: str) -> str:
    path = Path(value)
    if not path.is_absolute():
        path = base_dir / path
    return str(path.resolve())


def load_config(path: str | Path) -> Dict[str, Any]:
    config_path = Path(path).resolve()
    with config_path.open('r', encoding='utf-8') as f:
        cfg: Dict[str, Any] = yaml.safe_load(f)

    base_dir = config_path.parent

    data_cfg = cfg.get('data', {})
    if 'dataset_path' in data_cfg:
        data_cfg['dataset_path'] = _resolve_path(base_dir, data_cfg['dataset_path'])

    training_cfg = cfg.get('training', {})
    if 'output_dir' in training_cfg:
        training_cfg['output_dir'] = _resolve_path(base_dir, training_cfg['output_dir'])

    logging_cfg = cfg.get('logging', {})
    if 'log_file' in logging_cfg:
        logging_cfg['log_file'] = _resolve_path(base_dir, logging_cfg['log_file'])

    responses_cfg = cfg.get('responses', {})
    if 'knowledge_path' in responses_cfg:
        responses_cfg['knowledge_path'] = _resolve_path(base_dir, responses_cfg['knowledge_path'])

    storage_cfg = cfg.get('storage', {})
    if 'chat_db_path' in storage_cfg:
        storage_cfg['chat_db_path'] = _resolve_path(base_dir, storage_cfg['chat_db_path'])

    model_registry = cfg.get('model_registry', {})
    if isinstance(model_registry, dict):
        resolved_registry: Dict[str, Any] = {}
        for key, value in model_registry.items():
            if isinstance(value, str):
                resolved_registry[key] = _resolve_path(base_dir, value)
                continue
            if isinstance(value, dict):
                entry = dict(value)
                if 'path' in entry and isinstance(entry['path'], str):
                    entry['path'] = _resolve_path(base_dir, entry['path'])
                resolved_registry[key] = entry
                continue
            resolved_registry[key] = value
        cfg['model_registry'] = resolved_registry

    cfg['data'] = data_cfg
    cfg['training'] = training_cfg
    cfg['logging'] = logging_cfg
    cfg['responses'] = responses_cfg
    cfg['storage'] = storage_cfg

    return cfg
