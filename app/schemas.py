"""Contratos validados de la API de análisis."""
from typing import Annotated

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


class AnalysisRequest(StrictModel):
    # El límite acota coste y contexto sin imponer una persistencia.
    text: Annotated[str, Field(max_length=20_000)]

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El texto no puede estar vacío")
        return value
