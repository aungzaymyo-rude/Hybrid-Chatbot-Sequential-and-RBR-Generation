from __future__ import annotations

from pathlib import Path

from chatbot.deployment.ssl_utils import certificate_status, ensure_https_material, generate_self_signed_certificate


def test_generate_self_signed_certificate(tmp_path: Path):
    cert = tmp_path / 'server.crt'
    key = tmp_path / 'server.key'
    out_cert, out_key = generate_self_signed_certificate(cert, key, common_name='localhost')
    assert out_cert.exists()
    assert out_key.exists()
    assert 'BEGIN CERTIFICATE' in out_cert.read_text(encoding='utf-8')
    assert 'BEGIN RSA PRIVATE KEY' in out_key.read_text(encoding='utf-8')


def test_ensure_https_material_auto_generates(tmp_path: Path):
    cfg = {
        'deployment': {
            'ssl': {
                'enabled': True,
                'certfile': str(tmp_path / 'auto.crt'),
                'keyfile': str(tmp_path / 'auto.key'),
                'auto_generate': True,
                'common_name': 'localhost',
            }
        }
    }
    certfile, keyfile = ensure_https_material(cfg)
    assert Path(certfile).exists()
    assert Path(keyfile).exists()


def test_ensure_https_material_disabled():
    certfile, keyfile = ensure_https_material({'deployment': {'ssl': {'enabled': False}}})
    assert certfile is None
    assert keyfile is None


def test_certificate_status_reports_active_self_signed(tmp_path: Path):
    cert = tmp_path / 'server.crt'
    key = tmp_path / 'server.key'
    generate_self_signed_certificate(cert, key, common_name='localhost')
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
    assert status['status'] == 'active'
    assert status['is_self_signed'] is True
    assert status['cert_exists'] is True
    assert status['key_exists'] is True
