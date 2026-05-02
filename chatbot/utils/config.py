from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import yaml


def _resolve_path(base_dir: Path, value: str) -> str:
    path = Path(value)
    if not path.is_absolute():
        path = base_dir / path
    return str(path.resolve())


def _env_override(current: Any, env_name: str) -> Any:
    return os.getenv(env_name, current)


def resolve_model_settings(cfg: Dict[str, Any], model_key: str | None = None) -> Dict[str, Any]:
    registry = cfg.get('model_registry', {})
    default_key = cfg.get('model_default_key')
    resolved_key = model_key or default_key

    if not resolved_key:
        if not registry:
            raise ValueError('No model registry is configured.')
        resolved_key = next(iter(registry.keys()))

    if resolved_key not in registry:
        raise ValueError(f'Unknown model_key: {resolved_key}')

    entry = registry[resolved_key]
    if isinstance(entry, dict):
        output_dir = entry.get('path', cfg.get('training', {}).get('output_dir'))
        version = entry.get('version', '')
    else:
        output_dir = entry
        version = ''

    data_cfg = cfg.get('data', {})
    profiles = data_cfg.get('model_profiles', {})
    profile = profiles.get(resolved_key, {})
    dataset_path = profile.get('dataset_path', data_cfg.get('dataset_path'))
    intents = list(profile.get('intents', []))
    split_dir_root = data_cfg.get('split_dir')
    split_dir = str(Path(split_dir_root) / resolved_key) if split_dir_root else ''
    split_paths = {
        'train': str(Path(split_dir) / 'train.jsonl') if split_dir else '',
        'validation': str(Path(split_dir) / 'validation.jsonl') if split_dir else '',
        'test': str(Path(split_dir) / 'test.jsonl') if split_dir else '',
        'metadata': str(Path(split_dir) / 'metadata.json') if split_dir else '',
    }

    return {
        'model_key': resolved_key,
        'output_dir': output_dir,
        'dataset_path': dataset_path,
        'version': str(version),
        'intents': intents,
        'split_dir': split_dir,
        'split_paths': split_paths,
    }


def load_config(path: str | Path) -> Dict[str, Any]:
    config_path = Path(path).resolve()
    with config_path.open('r', encoding='utf-8') as f:
        cfg: Dict[str, Any] = yaml.safe_load(f)

    base_dir = config_path.parent

    data_cfg = cfg.get('data', {})
    if 'dataset_path' in data_cfg:
        data_cfg['dataset_path'] = _resolve_path(base_dir, data_cfg['dataset_path'])
    if 'split_dir' in data_cfg:
        data_cfg['split_dir'] = _resolve_path(base_dir, data_cfg['split_dir'])
    model_profiles = data_cfg.get('model_profiles', {})
    if isinstance(model_profiles, dict):
        resolved_profiles: Dict[str, Any] = {}
        for key, value in model_profiles.items():
            if not isinstance(value, dict):
                resolved_profiles[key] = value
                continue
            entry = dict(value)
            if 'dataset_path' in entry and isinstance(entry['dataset_path'], str):
                entry['dataset_path'] = _resolve_path(base_dir, entry['dataset_path'])
            resolved_profiles[key] = entry
        data_cfg['model_profiles'] = resolved_profiles

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
    storage_cfg['backend'] = _env_override(storage_cfg.get('backend', 'postgresql'), 'CHATBOT_DB_BACKEND')

    postgres_cfg = dict(storage_cfg.get('postgres', {}))
    postgres_cfg['host'] = _env_override(postgres_cfg.get('host', 'localhost'), 'POSTGRES_HOST')
    postgres_cfg['port'] = int(_env_override(postgres_cfg.get('port', 5432), 'POSTGRES_PORT'))
    postgres_cfg['database'] = _env_override(postgres_cfg.get('database', 'chatbot'), 'POSTGRES_DB')
    postgres_cfg['user'] = _env_override(postgres_cfg.get('user', 'postgres'), 'POSTGRES_USER')
    postgres_cfg['password'] = _env_override(postgres_cfg.get('password', 'P@ssw0rd'), 'POSTGRES_PASSWORD')
    postgres_cfg['sslmode'] = _env_override(postgres_cfg.get('sslmode', 'prefer'), 'POSTGRES_SSLMODE')
    storage_cfg['postgres'] = postgres_cfg

    if 'chat_db_path' in storage_cfg:
        storage_cfg['chat_db_path'] = _resolve_path(base_dir, storage_cfg['chat_db_path'])

    admin_cfg = cfg.get('admin', {})
    admin_cfg['default_recent_limit'] = int(_env_override(admin_cfg.get('default_recent_limit', 50), 'ADMIN_RECENT_LIMIT'))
    admin_cfg['low_confidence_threshold'] = float(_env_override(admin_cfg.get('low_confidence_threshold', 0.55), 'ADMIN_LOW_CONFIDENCE_THRESHOLD'))

    deployment_cfg = dict(cfg.get('deployment', {}))
    deployment_cfg['host'] = _env_override(deployment_cfg.get('host', '0.0.0.0'), 'CHATBOT_HOST')
    deployment_cfg['port'] = int(_env_override(deployment_cfg.get('port', 8000), 'CHATBOT_PORT'))
    deployment_cfg['reload'] = str(_env_override(deployment_cfg.get('reload', False), 'CHATBOT_RELOAD')).lower() in {'1', 'true', 'yes', 'on'}
    redirect_cfg = dict(deployment_cfg.get('http_redirect', {}))
    redirect_cfg['enabled'] = str(_env_override(redirect_cfg.get('enabled', True), 'CHATBOT_HTTP_REDIRECT_ENABLED')).lower() in {'1', 'true', 'yes', 'on'}
    redirect_cfg['port'] = int(_env_override(redirect_cfg.get('port', 8000), 'CHATBOT_HTTP_REDIRECT_PORT'))
    deployment_cfg['http_redirect'] = redirect_cfg
    ssl_cfg = dict(deployment_cfg.get('ssl', {}))
    ssl_cfg['enabled'] = str(_env_override(ssl_cfg.get('enabled', False), 'CHATBOT_HTTPS_ENABLED')).lower() in {'1', 'true', 'yes', 'on'}
    ssl_cfg['auto_generate'] = str(_env_override(ssl_cfg.get('auto_generate', True), 'CHATBOT_SSL_AUTO_GENERATE')).lower() in {'1', 'true', 'yes', 'on'}
    ssl_cfg['common_name'] = _env_override(ssl_cfg.get('common_name', 'localhost'), 'CHATBOT_SSL_COMMON_NAME')
    if 'certfile' in ssl_cfg:
        ssl_cfg['certfile'] = _resolve_path(base_dir, _env_override(ssl_cfg.get('certfile', 'certs/server.crt'), 'CHATBOT_SSL_CERTFILE'))
    if 'keyfile' in ssl_cfg:
        ssl_cfg['keyfile'] = _resolve_path(base_dir, _env_override(ssl_cfg.get('keyfile', 'certs/server.key'), 'CHATBOT_SSL_KEYFILE'))
    deployment_cfg['ssl'] = ssl_cfg

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
    cfg['admin'] = admin_cfg
    cfg['deployment'] = deployment_cfg

    return cfg
