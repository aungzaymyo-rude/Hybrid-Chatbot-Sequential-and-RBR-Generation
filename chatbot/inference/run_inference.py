from __future__ import annotations

import argparse
from pathlib import Path

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from chatbot.inference.registry import ModelRegistry
from chatbot.utils.routing_engine import route_intent


def main() -> None:
    parser = argparse.ArgumentParser(description='Run intent inference')
    parser.add_argument('--text', type=str, required=True, help='Input text')
    parser.add_argument(
        '--config',
        type=str,
        default=str(Path(__file__).resolve().parents[1] / 'config.yaml'),
        help='Path to config file',
    )
    parser.add_argument('--model-key', type=str, default=None, help='Model key from config registry')
    parser.add_argument('--model-dir', type=str, default=None, help='Direct path to model directory')
    parser.add_argument('--lang', type=str, default=None, help='Override detected language')
    args = parser.parse_args()

    registry = ModelRegistry(args.config)
    predictor = registry.get_predictor(model_key=args.model_key, model_dir=args.model_dir)
    prediction = predictor.predict(args.text, lang=args.lang)
    response = route_intent(
        prediction.intent,
        prediction.language,
        text=prediction.text,
        config_path=args.config,
    )

    print('Text:', prediction.text)
    print('Language:', prediction.language)
    print('Intent:', prediction.intent)
    print('Confidence:', f'{prediction.confidence:.4f}')
    print('Response:', response)


if __name__ == '__main__':
    main()
