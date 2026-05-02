from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from chatbot.deployment.ssl_utils import generate_self_signed_certificate  # noqa: E402
from chatbot.utils.config import load_config  # noqa: E402

CONFIG_PATH = Path(__file__).resolve().parents[1] / 'config.yaml'


def main() -> None:
    parser = argparse.ArgumentParser(description='Renew or generate the self-signed HTTPS certificate for the chatbot.')
    parser.add_argument('--config', default=str(CONFIG_PATH), help='Path to config.yaml')
    parser.add_argument('--certfile', default=None, help='Override certificate output path')
    parser.add_argument('--keyfile', default=None, help='Override key output path')
    parser.add_argument('--common-name', default=None, help='Override certificate common name')
    parser.add_argument('--valid-days', type=int, default=365, help='Certificate validity in days')
    args = parser.parse_args()

    cfg = load_config(args.config)
    ssl_cfg = cfg.get('deployment', {}).get('ssl', {})
    certfile = Path(args.certfile or ssl_cfg.get('certfile', PROJECT_ROOT / 'certs/server.crt')).resolve()
    keyfile = Path(args.keyfile or ssl_cfg.get('keyfile', PROJECT_ROOT / 'certs/server.key')).resolve()
    common_name = args.common_name or str(ssl_cfg.get('common_name', 'localhost'))

    out_cert, out_key = generate_self_signed_certificate(certfile, keyfile, common_name=common_name, valid_days=args.valid_days)
    print(f'Renewed self-signed certificate: {out_cert}')
    print(f'Renewed private key: {out_key}')
    print('Restart the application or container so the renewed certificate is loaded.')


if __name__ == '__main__':
    main()
