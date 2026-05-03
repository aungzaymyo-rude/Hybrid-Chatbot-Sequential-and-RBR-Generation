from __future__ import annotations

import asyncio
import importlib
from pathlib import Path
import sys
from threading import Thread

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from chatbot.utils.config import load_config
from chatbot.deployment.ssl_utils import ensure_https_material


CONFIG_PATH = Path(__file__).resolve().parents[1] / 'config.yaml'


def configure_event_loop_policy() -> None:
    # Python 3.14 deprecates manual event-loop policy changes. Keep the Windows
    # selector workaround only on older runtimes where it still reduces HTTPS
    # socket-noise without emitting startup warnings.
    if sys.version_info >= (3, 14):
        return
    if sys.platform == 'win32' and hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def preflight_import_app() -> None:
    try:
        importlib.import_module('chatbot.api.main')
    except ModuleNotFoundError as exc:
        if exc.name == 'torch':
            raise SystemExit(
                'PyTorch is not installed in this Python environment. Start the server with the project virtual environment '
                '(for example: .\\chatbot\\.venv\\Scripts\\python.exe -m chatbot.deployment.run_server) or install the '
                'requirements into the current interpreter with `pip install -r requirements.txt`.'
            ) from exc
        raise


def build_https_redirect_url(request: Request, https_port: int) -> str:
    host = request.headers.get('host', 'localhost')
    hostname = host.split(':', 1)[0]
    netloc = hostname if https_port == 443 else f'{hostname}:{https_port}'
    query = f'?{request.url.query}' if request.url.query else ''
    return f'https://{netloc}{request.url.path}{query}'


def create_http_redirect_app(https_port: int) -> FastAPI:
    redirect_app = FastAPI(title='Hematology Chatbot HTTP Redirect')

    @redirect_app.api_route('/{path:path}', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'])
    async def redirect_all(request: Request, path: str) -> RedirectResponse:
        return RedirectResponse(url=build_https_redirect_url(request, https_port), status_code=307)

    return redirect_app


def start_http_redirect_server(host: str, port: int, https_port: int) -> Thread:
    redirect_app = create_http_redirect_app(https_port)

    def _serve() -> None:
        uvicorn.run(redirect_app, host=host, port=port, reload=False)

    thread = Thread(target=_serve, daemon=True, name='http-redirect-server')
    thread.start()
    return thread


def main() -> None:
    configure_event_loop_policy()
    preflight_import_app()
    cfg = load_config(CONFIG_PATH)
    deploy_cfg = cfg.get('deployment', {})
    host = str(deploy_cfg.get('host', '0.0.0.0'))
    port = int(deploy_cfg.get('port', 8000))
    reload_enabled = bool(deploy_cfg.get('reload', False))
    redirect_cfg = deploy_cfg.get('http_redirect', {})
    ssl_cfg = deploy_cfg.get('ssl', {})

    certfile, keyfile = ensure_https_material(cfg)

    if ssl_cfg.get('enabled') and redirect_cfg.get('enabled'):
        redirect_port = int(redirect_cfg.get('port', 8000))
        if redirect_port != port:
            start_http_redirect_server(host, redirect_port, port)

    uvicorn.run(
        'chatbot.api.main:app',
        host=host,
        port=port,
        reload=reload_enabled,
        ssl_certfile=certfile,
        ssl_keyfile=keyfile,
    )


if __name__ == '__main__':
    main()
