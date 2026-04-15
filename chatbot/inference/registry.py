from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from chatbot.inference.predictor import IntentPredictor
from chatbot.utils.config import load_config


class ModelRegistry:
    def __init__(self, config_path: str) -> None:
        self.config_path = config_path
        self.config = load_config(config_path)
        self._cache: Dict[str, IntentPredictor] = {}

    def resolve_model_dir(self, model_key: Optional[str], model_dir: Optional[str]) -> str:
        if model_dir:
            return str(Path(model_dir).resolve())

        registry = self.config.get('model_registry', {})
        default_key = self.config.get('model_default_key')

        key = model_key or default_key
        if key:
            if key not in registry:
                raise ValueError(f'Unknown model_key: {key}')
            entry = registry[key]
            if isinstance(entry, dict):
                return entry.get('path', '')
            return entry

        if registry:
            first_key = next(iter(registry.keys()))
            entry = registry[first_key]
            if isinstance(entry, dict):
                return entry.get('path', '')
            return entry

        return self.config['training']['output_dir']

    def resolve_model_info(self, model_key: Optional[str], model_dir: Optional[str]) -> Dict[str, str]:
        if model_dir:
            resolved = str(Path(model_dir).resolve())
            return {'model_key': model_key or '', 'path': resolved, 'version': ''}

        registry = self.config.get('model_registry', {})
        default_key = self.config.get('model_default_key')
        key = model_key or default_key
        if key and key in registry:
            entry = registry[key]
            if isinstance(entry, dict):
                return {
                    'model_key': key,
                    'path': entry.get('path', ''),
                    'version': str(entry.get('version', '')),
                }
            return {'model_key': key, 'path': str(entry), 'version': ''}

        resolved = self.resolve_model_dir(model_key, model_dir)
        return {'model_key': key or '', 'path': resolved, 'version': ''}

    def get_predictor(self, model_key: Optional[str] = None, model_dir: Optional[str] = None) -> IntentPredictor:
        resolved = self.resolve_model_dir(model_key, model_dir)
        if resolved not in self._cache:
            self._cache[resolved] = IntentPredictor(model_dir=resolved, config_path=self.config_path)
        return self._cache[resolved]

    def list_models(self) -> Dict[str, Dict[str, str]]:
        registry = self.config.get('model_registry', {})
        models: Dict[str, Dict[str, str]] = {}
        for key, entry in registry.items():
            if isinstance(entry, dict):
                models[key] = {
                    'path': entry.get('path', ''),
                    'version': str(entry.get('version', '')),
                }
            else:
                models[key] = {'path': str(entry), 'version': ''}
        return models
