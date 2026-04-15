from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    text: str = Field(..., min_length=1)
    lang: str | None = None
    model_key: str | None = None
    model_dir: str | None = None


class ChatResponse(BaseModel):
    text: str
    lang: str
    intent: str
    confidence: float
    response: str
