from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    text: str = Field(..., min_length=1)
    lang: str | None = None
    model_key: str | None = None
    model_dir: str | None = None
    session_id: str | None = Field(default=None, max_length=128)


class ChatResponse(BaseModel):
    text: str
    lang: str
    intent: str
    confidence: float
    response: str


class AdminReviewRequest(BaseModel):
    review_status: str = Field(..., min_length=1, max_length=32)
    corrected_intent: str | None = Field(default=None, max_length=80)
    admin_notes: str | None = Field(default=None, max_length=4000)
