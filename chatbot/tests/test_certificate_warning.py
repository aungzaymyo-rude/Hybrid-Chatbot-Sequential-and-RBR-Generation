from pathlib import Path
from chatbot.deployment.ssl_utils import certificate_status, generate_self_signed_certificate


def test_certificate_status_warns_when_expiry_is_near(tmp_path: Path):
    cert = tmp_path / 'server.crt'
    key = tmp_path / 'server.key'
    generate_self_signed_certificate(cert, key, common_name='localhost', valid_days=1)
    status = certificate_status(
        {
            'deployment': {
                'port': 8443,
                'http_redirect': {'enabled': True, 'port': 8000},
                'ssl': {
                    'enabled': True,
                    'certfile': str(cert),
                    'keyfile': str(key),
                    'auto_generate': True,
                    'common_name': 'localhost',
                },
            }
        }
    )
    assert status['warning_level'] in {'warn', 'danger'}
