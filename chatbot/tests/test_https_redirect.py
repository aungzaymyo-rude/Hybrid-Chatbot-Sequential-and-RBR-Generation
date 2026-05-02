from fastapi import Request
from chatbot.deployment.run_server import build_https_redirect_url


def test_build_https_redirect_url_preserves_path_and_query():
    scope = {
        'type': 'http',
        'method': 'GET',
        'path': '/admin/api/summary',
        'query_string': b'model_key=general&limit=10',
        'headers': [(b'host', b'localhost:8000')],
        'client': ('127.0.0.1', 12345),
        'server': ('localhost', 8000),
        'scheme': 'http',
    }
    request = Request(scope)
    url = build_https_redirect_url(request, 8443)
    assert url == 'https://localhost:8443/admin/api/summary?model_key=general&limit=10'
