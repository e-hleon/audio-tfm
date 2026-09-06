"""Contratos validados de la API de análisis."""
from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Decision(StrictModel):
    text: str
    evidence: str


class Task(StrictModel):
    text: str
    assignee: str | None
    due_date: str | None
    evidence: str


class Reminder(StrictModel):
    text: str
    when: str | None
    evidence: str


class AnalysisResult(StrictModel):
    summary: str
    topics: list[str]
    decisions: list[Decision]
    tasks: list[Task]
    reminders: list[Reminder]


class DailySummaryResult(StrictModel):
    summary: str
    topics: list[str]


class InteractionTranscription(StrictModel):
    text: str
    language: str | None
    model: str
    device: str | None
    compute_type: str | None


class InteractionResponse(StrictModel):
    id: UUID
    capture_mode: str
    capture_session_id: UUID | None
    chunk_index: int | None
    capture_chunk_id: UUID | None
    recorded_at: datetime
    created_at: datetime
    transcription: InteractionTranscription
    analysis: AnalysisResult
    analysis_model: str | None


class DailySummaryState(StrictModel):
    status: Literal["missing", "ready", "stale"]
    result: DailySummaryResult | None
    generated_at: datetime | None
    model: str | None


class DayResponse(StrictModel):
    day: date
    timezone: str
    interactions: list[InteractionResponse]
    decisions: list[Decision]
    tasks: list[Task]
    reminders: list[Reminder]
    summary: DailySummaryState


class AnalysisRequest(StrictModel):
    # El límite acota coste y contexto sin imponer una persistencia.
    text: Annotated[str, Field(max_length=20_000)]

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El texto no puede estar vacío")
        return value
