from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
import datetime as dt
import ipaddress


def generate_self_signed_certificate(
    cert_path: str | Path,
    key_path: str | Path,
    common_name: str = 'localhost',
    valid_days: int = 365,
) -> tuple[Path, Path]:
    cert_file = Path(cert_path).resolve()
    key_file = Path(key_path).resolve()
    cert_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.parent.mkdir(parents=True, exist_ok=True)

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, 'MM'),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'Hybrid Haematology Chatbot'),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ]
    )

    alt_names: list[x509.GeneralName] = [x509.DNSName(common_name), x509.DNSName('localhost')]
    for value in ('127.0.0.1', '0.0.0.0'):
        try:
            alt_names.append(x509.IPAddress(ipaddress.ip_address(value)))
        except ValueError:
            continue

    now = dt.datetime.now(dt.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=5))
        .not_valid_after(now + dt.timedelta(days=valid_days))
        .add_extension(x509.SubjectAlternativeName(alt_names), critical=False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(private_key=key, algorithm=hashes.SHA256())
    )

    key_file.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    cert_file.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return cert_file, key_file


def ensure_https_material(cfg: Dict[str, Any]) -> tuple[str | None, str | None]:
    deploy_cfg = cfg.get('deployment', {})
    ssl_cfg = deploy_cfg.get('ssl', {})
    enabled = bool(ssl_cfg.get('enabled', False))
    if not enabled:
        return None, None

    cert_path = Path(str(ssl_cfg.get('certfile', ''))).resolve()
    key_path = Path(str(ssl_cfg.get('keyfile', ''))).resolve()

    if cert_path.exists() and key_path.exists():
        return str(cert_path), str(key_path)

    if not bool(ssl_cfg.get('auto_generate', True)):
        missing = []
        if not cert_path.exists():
            missing.append(str(cert_path))
        if not key_path.exists():
            missing.append(str(key_path))
        raise FileNotFoundError(f'HTTPS is enabled but certificate files are missing: {", ".join(missing)}')

    common_name = str(ssl_cfg.get('common_name', 'localhost'))
    generate_self_signed_certificate(cert_path, key_path, common_name=common_name)
    return str(cert_path), str(key_path)


def certificate_status(cfg: Dict[str, Any]) -> Dict[str, Any]:
    deploy_cfg = cfg.get('deployment', {})
    ssl_cfg = deploy_cfg.get('ssl', {})
    redirect_cfg = deploy_cfg.get('http_redirect', {})
    cert_path = Path(str(ssl_cfg.get('certfile', ''))).resolve() if ssl_cfg.get('certfile') else None
    key_path = Path(str(ssl_cfg.get('keyfile', ''))).resolve() if ssl_cfg.get('keyfile') else None

    status: Dict[str, Any] = {
        'https_enabled': bool(ssl_cfg.get('enabled', False)),
        'https_port': int(deploy_cfg.get('port', 8000)),
        'http_redirect_enabled': bool(redirect_cfg.get('enabled', False)),
        'http_redirect_port': int(redirect_cfg.get('port', 8000)),
        'auto_generate': bool(ssl_cfg.get('auto_generate', True)),
        'common_name': str(ssl_cfg.get('common_name', 'localhost')),
        'certfile': str(cert_path) if cert_path else '',
        'keyfile': str(key_path) if key_path else '',
        'cert_exists': bool(cert_path and cert_path.exists()),
        'key_exists': bool(key_path and key_path.exists()),
        'is_self_signed': None,
        'subject': '',
        'issuer': '',
        'not_before': '',
        'not_after': '',
        'days_remaining': None,
        'status': 'disabled' if not bool(ssl_cfg.get('enabled', False)) else 'missing',
        'warning_level': 'neutral',
    }

    if not status['https_enabled']:
        return status

    if not status['cert_exists'] or not status['key_exists']:
        status['warning_level'] = 'danger'
        return status

    try:
        cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
        subject = cert.subject.rfc4514_string()
        issuer = cert.issuer.rfc4514_string()
        not_before = cert.not_valid_before_utc
        not_after = cert.not_valid_after_utc
        now = dt.datetime.now(dt.timezone.utc)
        remaining = not_after - now
        status.update(
            {
                'subject': subject,
                'issuer': issuer,
                'not_before': not_before.isoformat(),
                'not_after': not_after.isoformat(),
                'days_remaining': max(0, remaining.days),
                'is_self_signed': subject == issuer,
                'status': 'active',
            }
        )
        if remaining.days <= 7:
            status['warning_level'] = 'danger'
        elif remaining.days <= 30:
            status['warning_level'] = 'warn'
        else:
            status['warning_level'] = 'success'
    except Exception as exc:
        status['status'] = 'invalid'
        status['error'] = str(exc)
        status['warning_level'] = 'danger'

    return status
