from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect as sqlalchemy_inspect, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.db import make_engine
from app.models import DailySummary, Interaction
from app.repositories import (
    create_interaction,
    get_daily_summary,
    get_interaction,
    interactions_fingerprint,
    list_interactions,
    upsert_daily_summary,
)
from app.settings import Settings
from app.time_utils import day_interval, ensure_aware, to_utc
from app.main import create_app
from app.schemas import AnalysisResult


def test_settings_validate_timezone(monkeypatch):
    monkeypatch.delenv("APP_TIMEZONE", raising=False)
    assert Settings.from_env().app_timezone == "UTC"
    monkeypatch.setenv("APP_TIMEZONE", "Europe/Madrid")
    assert Settings.from_env().app_timezone == "Europe/Madrid"
    monkeypatch.setenv("APP_TIMEZONE", "Not/AZone")
    with pytest.raises(ValueError, match="zona IANA"):
        Settings.from_env()


@pytest.fixture(scope="session")
def db_engine():
    settings = Settings.from_env()
    engine = make_engine(settings)
    try:
        with engine.connect():
            pass
    except OperationalError as exc:
        engine.dispose()
        pytest.skip(f"PostgreSQL no disponible: {exc}")
    yield engine
    engine.dispose()


@pytest.fixture
def session(db_engine):
    with Session(db_engine) as session:
        session.execute(Interaction.__table__.delete())
        session.execute(DailySummary.__table__.delete())
        session.commit()
        yield session
        session.rollback()
        session.execute(Interaction.__table__.delete())
        session.execute(DailySummary.__table__.delete())
        session.commit()


def interaction_values(recorded_at):
    return {
        "recorded_at": recorded_at,
        "transcription": "Texto sintético",
        "language": "es",
        "transcription_model": "base",
        "transcription_device": "cuda",
        "transcription_compute_type": "int8_float16",
        "analysis": {"summary": "Resumen", "topics": ["prueba"], "decisions": [], "tasks": [], "reminders": []},
        "analysis_model": "test-model",
    }


class HttpFakeTranscriber:
    def details(self):
        return {"model": "fake", "device": "cuda", "compute_type": "int8_float16"}

    def transcribe(self, file):
        return {"text": "Texto persistido", "language": "es", **self.details()}


class HttpFakeAnalyzer:
    model = "fake-llm"

    def available(self):
        return True

    def analyze(self, text):
        return AnalysisResult(summary="Resumen persistido", topics=["persistencia"], decisions=[], tasks=[], reminders=[])


def test_migration_created_expected_tables(db_engine):
    inspector = sqlalchemy_inspect(db_engine)
    assert {"interactions", "daily_summaries", "alembic_version"}.issubset(inspector.get_table_names())
    columns = {column["name"] for column in inspector.get_columns("interactions")}
    assert "audio" not in columns
    assert "filename" not in columns


def test_create_get_jsonb_and_timezone_aware(session):
    item = create_interaction(session, **interaction_values(datetime(2026, 9, 5, 10, tzinfo=timezone.utc)))
    session.commit()
    found = get_interaction(session, item.id)
    assert found is not None
    assert found.analysis["summary"] == "Resumen"
    assert found.analysis["topics"] == ["prueba"]
    assert found.recorded_at.tzinfo is not None
    assert found.created_at.tzinfo is not None
    assert found.updated_at.tzinfo is not None


def test_list_is_chronological_and_filters_half_open_interval(session):
    late = create_interaction(session, **interaction_values(datetime(2026, 9, 5, 12, tzinfo=timezone.utc)))
    early = create_interaction(session, **interaction_values(datetime(2026, 9, 5, 8, tzinfo=timezone.utc)))
    session.commit()
    assert [item.id for item in list_interactions(session)] == [early.id, late.id]
    result = list_interactions(
        session,
        datetime(2026, 9, 5, 9, tzinfo=timezone.utc),
        datetime(2026, 9, 5, 13, tzinfo=timezone.utc),
    )
    assert [item.id for item in result] == [late.id]


def test_daily_summary_unique_and_upsert(session):
    day = date(2026, 9, 5)
    summary = upsert_daily_summary(
        session,
        day=day,
        timezone="UTC",
        result={"summary": "Uno", "topics": []},
        source_fingerprint="a" * 64,
        generated_at=datetime.now(timezone.utc),
    )
    session.commit()
    updated = upsert_daily_summary(
        session,
        day=day,
        timezone="UTC",
        result={"summary": "Dos", "topics": ["tema"]},
        source_fingerprint="b" * 64,
        generated_at=datetime.now(timezone.utc),
    )
    session.commit()
    assert updated.id == summary.id
    assert get_daily_summary(session, day).result["summary"] == "Dos"


def test_duplicate_daily_summary_rolls_back_without_losing_original(session):
    day = date(2026, 9, 5)
    upsert_daily_summary(session, day=day, timezone="UTC", result={"summary": "Uno", "topics": []},
                         source_fingerprint="a" * 64, generated_at=datetime.now(timezone.utc))
    session.commit()
    duplicate = DailySummary(day=day, timezone="UTC", result={"summary": "Dos", "topics": []},
                             source_fingerprint="b" * 64, generated_at=datetime.now(timezone.utc))
    session.add(duplicate)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
    assert get_daily_summary(session, day).result["summary"] == "Uno"


def test_fingerprint_is_order_independent_and_changes_on_add_or_update(session):
    first = create_interaction(session, **interaction_values(datetime(2026, 9, 5, 8, tzinfo=timezone.utc)))
    second = create_interaction(session, **interaction_values(datetime(2026, 9, 5, 9, tzinfo=timezone.utc)))
    session.commit()
    original = interactions_fingerprint([first, second])
    assert interactions_fingerprint([second, first]) == original
    third = create_interaction(session, **interaction_values(datetime(2026, 9, 5, 10, tzinfo=timezone.utc)))
    session.commit()
    assert interactions_fingerprint([first, second, third]) != original
    first.updated_at = first.updated_at + timedelta(seconds=1)
    assert interactions_fingerprint([first, second]) != original


def test_temporal_utilities_reject_naive_and_handle_utc_midnight():
    naive = datetime(2026, 9, 5, 12)
    with pytest.raises(ValueError):
        ensure_aware(naive)
    assert to_utc(datetime(2026, 9, 5, 12, tzinfo=timezone(timedelta(hours=2)))) == datetime(2026, 9, 5, 10, tzinfo=timezone.utc)
    start, end = day_interval("2026-09-05", "UTC")
    assert start == datetime(2026, 9, 5, tzinfo=timezone.utc)
    assert end == datetime(2026, 9, 6, tzinfo=timezone.utc)


def test_europe_madrid_midnight_and_dst():
    start, end = day_interval("2026-03-29", "Europe/Madrid")
    assert start.hour == 23 and start.day == 28
    assert end - start == timedelta(hours=23)
    start, end = day_interval("2026-10-25", "Europe/Madrid")
    assert end - start == timedelta(hours=25)


def test_interaction_model_has_no_audio_fields():
    columns = set(Interaction.__table__.columns.keys())
    assert not columns.intersection({"audio", "audio_path", "filename", "prompt"})


def test_http_process_and_history_against_postgresql(db_engine, session):
    with TestClient(create_app(HttpFakeTranscriber, HttpFakeAnalyzer, lambda: Session(db_engine))) as client:
        first = client.post(
            "/process",
            files={"file": ("ignored.wav", b"synthetic")},
            data={"recorded_at": "2026-09-05T10:00:00+00:00"},
        )
        assert first.status_code == 200
        body = first.json()
        assert body["transcription"]["text"] == "Texto persistido"
        assert body["analysis"]["summary"] == "Resumen persistido"
        interaction_id = body["interaction_id"]

        detail = client.get(f"/interactions/{interaction_id}")
        assert detail.status_code == 200
        assert detail.json()["analysis_model"] == "fake-llm"
        assert detail.json()["transcription"]["model"] == "fake"

        history = client.get("/interactions", params={"from": "2026-09-05T10:00:00Z", "to": "2026-09-05T11:00:00Z"})
        assert history.status_code == 200
        assert len(history.json()) == 1
        assert client.get("/interactions/00000000-0000-0000-0000-000000000000").status_code == 404
        assert client.get("/interactions/not-a-uuid").status_code == 422


def test_http_history_limit_offset_and_timezone_filters(db_engine, session):
    for hour in (8, 9, 10):
        create_interaction(session, **interaction_values(datetime(2026, 9, 5, hour, tzinfo=timezone.utc)))
    session.commit()
    with TestClient(create_app(HttpFakeTranscriber, HttpFakeAnalyzer, lambda: Session(db_engine))) as client:
        limited = client.get("/interactions", params={"limit": 1, "offset": 1})
        assert limited.status_code == 200
        assert limited.json()[0]["recorded_at"].startswith("2026-09-05T09:00:00")
        semi_open = client.get(
            "/interactions",
            params={"from": "2026-09-05T09:00:00+02:00", "to": "2026-09-05T12:00:00+02:00"},
        )
        assert semi_open.status_code == 200
        assert len(semi_open.json()) == 2
        assert client.get("/interactions", params={"from": "2026-09-05T12:00:00"}).status_code == 422
