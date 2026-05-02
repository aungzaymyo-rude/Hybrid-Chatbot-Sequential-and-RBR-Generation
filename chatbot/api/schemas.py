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
    model_key: str | None = None
    model_version: str | None = None
    requested_model_key: str | None = None
    auto_switched: bool = False
    advisory_message: str | None = None
    suggested_model_key: str | None = None


class AdminReviewRequest(BaseModel):
    review_status: str = Field(..., min_length=1, max_length=32)
    corrected_intent: str | None = Field(default=None, max_length=80)
    admin_notes: str | None = Field(default=None, max_length=4000)


class TraceRequest(BaseModel):
    text: str = Field(..., min_length=1, examples=['What is aPTT?'])
    model_key: str | None = Field(default=None, examples=['general'])
