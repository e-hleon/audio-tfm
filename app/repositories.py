"""Operaciones de persistencia sin lógica HTTP."""
from datetime import date, datetime
import hashlib
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DailySummary, Interaction
from app.time_utils import ensure_aware, to_utc


def create_interaction(session: Session, **values) -> Interaction:
    values["recorded_at"] = to_utc(values["recorded_at"])
    interaction = Interaction(**values)
    session.add(interaction)
    session.flush()
    return interaction


def get_interaction(session: Session, interaction_id: uuid.UUID) -> Interaction | None:
    return session.get(Interaction, interaction_id)


def list_interactions(
    session: Session,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[Interaction]:
    statement = select(Interaction)
    if start is not None:
        statement = statement.where(Interaction.recorded_at >= to_utc(start))
    if end is not None:
        statement = statement.where(Interaction.recorded_at < to_utc(end))
    statement = statement.order_by(Interaction.recorded_at, Interaction.id).offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    return list(session.scalars(statement))


def upsert_daily_summary(
    session: Session,
    *,
    day: date,
    timezone: str,
    result: dict,
    source_fingerprint: str,
    generated_at: datetime,
    llm_model: str | None = None,
) -> DailySummary:
    summary = session.scalar(select(DailySummary).where(DailySummary.day == day))
    values = {
        "timezone": timezone,
        "result": result,
        "source_fingerprint": source_fingerprint,
        "generated_at": to_utc(generated_at),
        "llm_model": llm_model,
    }
    if summary is None:
        summary = DailySummary(day=day, **values)
        session.add(summary)
    else:
        for key, value in values.items():
            setattr(summary, key, value)
    session.flush()
    return summary


def get_daily_summary(session: Session, day: date) -> DailySummary | None:
    return session.scalar(select(DailySummary).where(DailySummary.day == day))


def interactions_fingerprint(interactions: list[Interaction]) -> str:
    entries = sorted(
        f"{interaction.id}:{to_utc(ensure_aware(interaction.updated_at)).isoformat()}"
        for interaction in interactions
    )
    return hashlib.sha256("\n".join(entries).encode("utf-8")).hexdigest()
