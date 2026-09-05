from datetime import date, datetime, timedelta, timezone

import pytest
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
        "analysis": {"summary": "Resumen", "topics": ["prueba"]},
        "analysis_model": "test-model",
    }


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
    assert found.analysis == {"summary": "Resumen", "topics": ["prueba"]}
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
