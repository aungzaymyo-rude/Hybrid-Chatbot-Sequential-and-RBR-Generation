from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from chatbot.api.schemas import AdminReviewRequest, ChatRequest, ChatResponse, TraceRequest
from chatbot.inference.registry import ModelRegistry
from chatbot.utils.admin_pipeline import build_pipeline_snapshot
from chatbot.utils.chat_store import ChatHistoryStore
from chatbot.utils.config import load_config
from chatbot.utils.logging import setup_logging
from chatbot.utils.model_advisory import recommend_model_switch
from chatbot.utils.routing_engine import STATIC_INTENTS, resolve_route
from chatbot.utils.trace_pipeline import build_trace

CONFIG_PATH = str(Path(__file__).resolve().parents[1] / 'config.yaml')
UI_DIR = Path(__file__).resolve().parents[1] / 'ui'

app = FastAPI(title='Multilingual Chatbot API', version='1.0.0')
app.mount('/ui', StaticFiles(directory=str(UI_DIR)), name='ui')


@lru_cache
def get_config() -> dict:
    return load_config(CONFIG_PATH)


@lru_cache
def get_registry() -> ModelRegistry:
    cfg = get_config()
    setup_logging(cfg['logging']['log_file'], cfg['logging'].get('level', 'INFO'))
    return ModelRegistry(CONFIG_PATH)


@lru_cache
def get_chat_store() -> ChatHistoryStore:
    cfg = get_config()
    return ChatHistoryStore(cfg['storage']['postgres'])


@app.get('/health')
def health() -> dict:
    cfg = get_config()
    return {'status': 'ok', 'database_backend': cfg['storage'].get('backend', 'postgresql')}


@app.get('/')
def index() -> FileResponse:
    return FileResponse(UI_DIR / 'index.html')


@app.get('/admin')
def admin_index() -> FileResponse:
    return FileResponse(UI_DIR / 'admin.html')


@app.get('/models')
def list_models(registry: ModelRegistry = Depends(get_registry)) -> dict:
    return {
        'default': registry.config.get('model_default_key'),
        'models': registry.list_models(),
    }


@app.get('/admin/api/pipeline')
def admin_pipeline(registry: ModelRegistry = Depends(get_registry)) -> dict:
    cfg = get_config()
    return build_pipeline_snapshot(cfg, registry.list_models())


@app.post('/admin/api/trace')
def admin_trace(request: TraceRequest) -> dict:
    try:
        return build_trace(request.text, model_key=request.model_key, config_path=CONFIG_PATH)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get('/admin/api/summary')
def admin_summary(
    model_key: str | None = Query(default=None),
    chat_store: ChatHistoryStore = Depends(get_chat_store),
) -> dict:
    cfg = get_config()
    threshold = float(cfg['admin'].get('low_confidence_threshold', 0.55))
    return {
        'summary': chat_store.fetch_summary(low_confidence_threshold=threshold, model_key=model_key),
        'intent_breakdown': chat_store.fetch_intent_breakdown(limit=20, model_key=model_key),
        'flagged_phrases': chat_store.fetch_flagged_phrases(low_confidence_threshold=threshold, limit=15, model_key=model_key),
        'model_breakdown': chat_store.fetch_model_breakdown(low_confidence_threshold=threshold),
    }


@app.get('/admin/api/logs')
def admin_logs(
    limit: int = Query(default=50, ge=1, le=200),
    flagged_only: bool = Query(default=False),
    review_status: str | None = Query(default=None),
    model_key: str | None = Query(default=None),
    chat_store: ChatHistoryStore = Depends(get_chat_store),
) -> dict:
    cfg = get_config()
    threshold = float(cfg['admin'].get('low_confidence_threshold', 0.55))
    return {
        'logs': chat_store.fetch_recent_logs(
            limit=limit,
            flagged_only=flagged_only,
            review_status=review_status,
            model_key=model_key,
            low_confidence_threshold=threshold,
        )
    }


@app.post('/admin/api/logs/{log_id}/review')
def admin_review_log(
    log_id: int,
    request: AdminReviewRequest,
    chat_store: ChatHistoryStore = Depends(get_chat_store),
) -> dict:
    chat_store.update_review(
        log_id=log_id,
        review_status=request.review_status,
        corrected_intent=request.corrected_intent,
        admin_notes=request.admin_notes,
    )
    return {'status': 'updated', 'log_id': log_id}


@app.get('/admin/api/export-reviewed')
def admin_export_reviewed(chat_store: ChatHistoryStore = Depends(get_chat_store)) -> FileResponse:
    export_path = Path(get_config()['logging']['log_file']).resolve().parents[1] / 'review_exports' / 'reviewed_queries.csv'
    written = chat_store.export_reviewed_to_csv(export_path)
    return FileResponse(written, media_type='text/csv', filename=written.name)


@app.get('/admin/api/export-logs')
def admin_export_logs(chat_store: ChatHistoryStore = Depends(get_chat_store)) -> FileResponse:
    export_path = Path(get_config()['logging']['log_file']).resolve().parents[1] / 'review_exports' / 'recent_logs.csv'
    written = chat_store.export_logs_to_csv(export_path)
    return FileResponse(written, media_type='text/csv', filename=written.name)


@app.get('/admin/api/export-report-analysis-errors')
def admin_export_report_analysis_errors(chat_store: ChatHistoryStore = Depends(get_chat_store)) -> FileResponse:
    cfg = get_config()
    export_path = Path(cfg['logging']['log_file']).resolve().parents[1] / 'review_exports' / 'report_analysis_errors.csv'
    written = chat_store.export_report_analysis_errors_to_csv(
        export_path,
        limit=1500,
        low_confidence_threshold=float(cfg['admin'].get('low_confidence_threshold', 0.55)),
    )
    return FileResponse(written, media_type='text/csv', filename=written.name)


@app.get('/admin/api/report-analysis-preview')
def admin_report_analysis_preview(chat_store: ChatHistoryStore = Depends(get_chat_store)) -> dict:
    cfg = get_config()
    rows = chat_store.fetch_report_analysis_error_preview(
        limit=25,
        low_confidence_threshold=float(cfg['admin'].get('low_confidence_threshold', 0.55)),
    )
    return {'rows': rows}


@app.post('/chat', response_model=ChatResponse)
def chat(
    request: ChatRequest,
    registry: ModelRegistry = Depends(get_registry),
    chat_store: ChatHistoryStore = Depends(get_chat_store),
) -> ChatResponse:
    requested_model_key = request.model_key or registry.config.get('model_default_key')
    suggested_model_key = None
    advisory_message = None
    effective_model_key = requested_model_key
    if not request.model_dir:
        suggested_model_key, advisory_message = recommend_model_switch(request.text, requested_model_key)
        if suggested_model_key:
            effective_model_key = suggested_model_key

    try:
        predictor = registry.get_predictor(model_key=effective_model_key, model_dir=request.model_dir)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    prediction = predictor.predict(request.text, lang=request.lang)
    route = resolve_route(
        prediction.intent,
        prediction.language,
        text=prediction.text,
        config_path=CONFIG_PATH,
    )
    model_info = registry.resolve_model_info(effective_model_key, request.model_dir)
    auto_switched = bool(suggested_model_key and suggested_model_key != requested_model_key)
    try:
        chat_store.log_chat(
            session_id=request.session_id,
            user_text=prediction.text,
            detected_lang=prediction.language,
            intent=prediction.intent,
            confidence=prediction.confidence,
            response=route.response,
            response_source=route.source,
            retrieval_intent=route.retrieval_intent,
            retrieval_question=route.retrieval_question,
            entity_label=route.entity_label,
            is_fallback=prediction.intent == 'fallback',
            is_guardrail=prediction.intent in STATIC_INTENTS,
            model_key=effective_model_key,
            requested_model_key=requested_model_key,
            auto_switched=auto_switched,
            model_path=model_info['path'],
            model_version=model_info.get('version') or None,
        )
    except Exception:
        pass
    return ChatResponse(
        text=prediction.text,
        lang=prediction.language,
        intent=prediction.intent,
        confidence=prediction.confidence,
        response=route.response,
        model_key=effective_model_key,
        model_version=model_info.get('version') or None,
        requested_model_key=requested_model_key,
        auto_switched=auto_switched,
        advisory_message=advisory_message if auto_switched else None,
        suggested_model_key=suggested_model_key if auto_switched else None,
    )
