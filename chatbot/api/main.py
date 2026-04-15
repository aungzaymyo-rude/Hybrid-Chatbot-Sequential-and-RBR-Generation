from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from chatbot.api.schemas import ChatRequest, ChatResponse
from chatbot.inference.registry import ModelRegistry
from chatbot.utils.chat_store import ChatHistoryStore
from chatbot.utils.config import load_config
from chatbot.utils.logging import setup_logging
from chatbot.utils.routing_engine import route_intent

CONFIG_PATH = str(Path(__file__).resolve().parents[1] / 'config.yaml')
UI_DIR = Path(__file__).resolve().parents[1] / 'ui'

app = FastAPI(title='Multilingual Chatbot API', version='1.0.0')
app.mount('/ui', StaticFiles(directory=str(UI_DIR)), name='ui')


@lru_cache
def get_registry() -> ModelRegistry:
    cfg = load_config(CONFIG_PATH)
    setup_logging(cfg['logging']['log_file'], cfg['logging'].get('level', 'INFO'))
    return ModelRegistry(CONFIG_PATH)


@lru_cache
def get_chat_store() -> ChatHistoryStore:
    cfg = load_config(CONFIG_PATH)
    return ChatHistoryStore(cfg['storage']['chat_db_path'])


@app.get('/health')
def health() -> dict:
    return {'status': 'ok'}


@app.get('/')
def index() -> FileResponse:
    return FileResponse(UI_DIR / 'index.html')

@app.get('/models')
def list_models(registry: ModelRegistry = Depends(get_registry)) -> dict:
    return {
        'default': registry.config.get('model_default_key'),
        'models': registry.list_models(),
    }


@app.post('/chat', response_model=ChatResponse)
def chat(
    request: ChatRequest,
    registry: ModelRegistry = Depends(get_registry),
    chat_store: ChatHistoryStore = Depends(get_chat_store),
) -> ChatResponse:
    try:
        predictor = registry.get_predictor(model_key=request.model_key, model_dir=request.model_dir)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    prediction = predictor.predict(request.text, lang=request.lang)
    response_text = route_intent(
        prediction.intent,
        prediction.language,
        text=prediction.text,
        config_path=CONFIG_PATH,
    )
    model_info = registry.resolve_model_info(request.model_key, request.model_dir)
    try:
        chat_store.log_chat(
            user_text=prediction.text,
            detected_lang=prediction.language,
            intent=prediction.intent,
            confidence=prediction.confidence,
            response=response_text,
            model_key=model_info.get('model_key') or None,
            model_path=model_info['path'],
            model_version=model_info.get('version') or None,
        )
    except Exception:
        # Logging should not break the user-facing chat path.
        pass
    return ChatResponse(
        text=prediction.text,
        lang=prediction.language,
        intent=prediction.intent,
        confidence=prediction.confidence,
        response=response_text,
    )
