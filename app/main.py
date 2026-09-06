"""API síncrona: la respuesta HTTP espera al texto final."""
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from threading import Lock
from typing import Annotated
import uuid
from zoneinfo import ZoneInfo

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from starlette.concurrency import run_in_threadpool
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.analysis import (
    AnalysisAuthenticationFailed,
    AnalysisIncomplete,
    AnalysisInvalidResponse,
    AnalysisNetworkFailed,
    AnalysisNotConfigured,
    AnalysisRateLimited,
    AnalysisTimedOut,
    OpenAIAnalyzer,
)
from app.schemas import (
    AnalysisRequest,
    AnalysisResult,
    DailySummaryResult,
    DailySummaryState,
    DayResponse,
    InteractionResponse,
)
from app.db import make_session_factory
from app.repositories import (
    create_interaction,
    get_daily_summary,
    get_interaction,
    get_interaction_by_capture_chunk_id,
    interactions_fingerprint,
    list_interactions,
    upsert_daily_summary,
)
from app.settings import get_settings
from app.time_utils import day_interval, ensure_aware, to_utc
from app.transcription import AudioTooLong, InvalidAudio, Transcriber

MAX_BYTES = 10 * 1024 * 1024


def create_app(transcriber_factory=Transcriber, analyzer_factory=OpenAIAnalyzer, session_factory=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.transcriber = transcriber_factory()
        app.state.analyzer = analyzer_factory()
        app.state.session_factory = session_factory or make_session_factory()
        app.state.settings = get_settings()
        app.state.inference_lock = Lock()
        yield
        del app.state.transcriber

    app = FastAPI(title="Audio TFM — transcripción local", lifespan=lifespan)

    @app.get("/health")
    def health():
        return {
            "status": "ready",
            "analysis_configured": app.state.analyzer.available(),
            **app.state.transcriber.details(),
        }

    async def transcribe_upload(file: UploadFile):
        acquired = False
        try:
            if not file.size:
                raise HTTPException(400, "El archivo está vacío")
            if file.size > MAX_BYTES:
                raise HTTPException(413, "El archivo supera los 10 MiB")
            acquired = app.state.inference_lock.acquire(blocking=False)
            if not acquired:
                raise HTTPException(503, "Transcriptor ocupado; inténtalo de nuevo")
            try:
                return await run_in_threadpool(app.state.transcriber.transcribe, file.file)
            except InvalidAudio as exc:
                raise HTTPException(400, str(exc)) from exc
            except AudioTooLong as exc:
                raise HTTPException(413, str(exc)) from exc
        finally:
            if acquired:
                app.state.inference_lock.release()
            # Cierra y elimina el temporal creado por el parser multipart.
            await file.close()

    @app.post("/transcriptions")
    async def transcriptions(file: Annotated[UploadFile, File()]):
        return await transcribe_upload(file)

    def analyze_text(text: str) -> AnalysisResult:
        try:
            return app.state.analyzer.analyze(text)
        except AnalysisNotConfigured as exc:
            raise HTTPException(503, "El análisis LLM no está configurado") from exc
        except AnalysisAuthenticationFailed as exc:
            raise HTTPException(502, "OpenAI rechazó las credenciales configuradas") from exc
        except AnalysisRateLimited as exc:
            raise HTTPException(
                429,
                "OpenAI no puede procesar la solicitud por límite de peticiones o cuota insuficiente",
            ) from exc
        except AnalysisTimedOut as exc:
            raise HTTPException(504, "OpenAI agotó el tiempo de espera") from exc
        except AnalysisNetworkFailed as exc:
            raise HTTPException(503, "No se pudo completar la llamada a OpenAI") from exc
        except (AnalysisInvalidResponse, AnalysisIncomplete) as exc:
            raise HTTPException(502, "OpenAI devolvió una respuesta no utilizable") from exc

    def summarize_day(derived_interactions: list[dict]):
        try:
            return app.state.analyzer.summarize_day(derived_interactions)
        except AnalysisNotConfigured as exc:
            raise HTTPException(503, "El análisis LLM no está configurado") from exc
        except AnalysisAuthenticationFailed as exc:
            raise HTTPException(502, "OpenAI rechazó las credenciales configuradas") from exc
        except AnalysisRateLimited as exc:
            raise HTTPException(
                429,
                "OpenAI no puede procesar la solicitud por límite de peticiones o cuota insuficiente",
            ) from exc
        except AnalysisTimedOut as exc:
            raise HTTPException(504, "OpenAI agotó el tiempo de espera") from exc
        except AnalysisNetworkFailed as exc:
            raise HTTPException(503, "No se pudo completar la llamada a OpenAI") from exc
        except (AnalysisInvalidResponse, AnalysisIncomplete) as exc:
            raise HTTPException(502, "OpenAI devolvió una respuesta no utilizable") from exc

    def parse_recorded_at(value: str | None, received_at: datetime) -> datetime:
        if value is None:
            return received_at
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return to_utc(ensure_aware(parsed))
        except (TypeError, ValueError) as exc:
            raise HTTPException(422, "recorded_at debe ser un ISO-8601 con zona horaria") from exc

    def persist_interaction(
        recorded_at: datetime,
        transcription: dict,
        analysis: AnalysisResult,
        *,
        capture_mode: str,
        capture_session_id: uuid.UUID | None,
        chunk_index: int | None,
        capture_chunk_id: uuid.UUID | None,
    ):
        try:
            with app.state.session_factory() as session:
                try:
                    interaction = create_interaction(
                        session,
                        recorded_at=recorded_at,
                        capture_mode=capture_mode,
                        capture_session_id=capture_session_id,
                        chunk_index=chunk_index,
                        capture_chunk_id=capture_chunk_id,
                        transcription=transcription["text"],
                        language=transcription.get("language"),
                        transcription_model=transcription["model"],
                        transcription_device=transcription.get("device"),
                        transcription_compute_type=transcription.get("compute_type"),
                        analysis=analysis.model_dump(mode="json"),
                        analysis_model=getattr(app.state.analyzer, "model", None),
                    )
                    session.commit()
                    session.refresh(interaction)
                    session.expunge(interaction)
                    return interaction
                except IntegrityError:
                    session.rollback()
                    if capture_chunk_id is not None:
                        duplicate = get_interaction_by_capture_chunk_id(session, capture_chunk_id)
                        if duplicate is not None:
                            session.expunge(duplicate)
                            return duplicate
                    raise
                except SQLAlchemyError:
                    session.rollback()
                    raise
        except SQLAlchemyError as exc:
            raise HTTPException(503, "No se pudo guardar la interacción") from exc

    def interaction_response(interaction) -> InteractionResponse:
        return InteractionResponse(
            id=interaction.id,
            capture_mode=interaction.capture_mode,
            capture_session_id=interaction.capture_session_id,
            chunk_index=interaction.chunk_index,
            capture_chunk_id=interaction.capture_chunk_id,
            recorded_at=to_utc(interaction.recorded_at),
            created_at=to_utc(interaction.created_at),
            transcription={
                "text": interaction.transcription,
                "language": interaction.language,
                "model": interaction.transcription_model,
                "device": interaction.transcription_device,
                "compute_type": interaction.transcription_compute_type,
            },
            analysis=AnalysisResult.model_validate(interaction.analysis),
            analysis_model=interaction.analysis_model,
        )

    def daily_summary_state(summary, fingerprint: str) -> DailySummaryState:
        if summary is None:
            return DailySummaryState(status="missing", result=None, generated_at=None, model=None)
        return DailySummaryState(
            status=(
                "ready"
                if (
                    summary.source_fingerprint == fingerprint
                    and summary.timezone == app.state.settings.app_timezone
                )
                else "stale"
            ),
            result=DailySummaryResult.model_validate(summary.result),
            generated_at=to_utc(summary.generated_at),
            model=summary.llm_model,
        )

    def derived_daily_interactions(interactions: list) -> list[dict]:
        """La única entrada del LLM diario: datos derivados y hora local."""
        local_zone = ZoneInfo(app.state.settings.app_timezone)
        derived = []
        for interaction in interactions:
            analysis = AnalysisResult.model_validate(interaction.analysis)
            derived.append(
                {
                    "local_time": to_utc(interaction.recorded_at)
                    .astimezone(local_zone)
                    .isoformat(timespec="minutes"),
                    "summary": analysis.summary,
                    "topics": analysis.topics,
                    "decisions": [item.model_dump(mode="json") for item in analysis.decisions],
                    "tasks": [item.model_dump(mode="json") for item in analysis.tasks],
                    "reminders": [item.model_dump(mode="json") for item in analysis.reminders],
                }
            )
        return derived

    def load_day(day: date):
        start, end = day_interval(day, app.state.settings.app_timezone)
        with app.state.session_factory() as session:
            interactions = list_interactions(session, start, end)
            fingerprint = interactions_fingerprint(interactions)
            summary = get_daily_summary(session, day)
            return interactions, fingerprint, summary

    def day_response(day: date, interactions: list, fingerprint: str, summary) -> DayResponse:
        analyses = [AnalysisResult.model_validate(item.analysis) for item in interactions]
        return DayResponse(
            day=day,
            timezone=app.state.settings.app_timezone,
            interactions=[interaction_response(item) for item in interactions],
            decisions=[decision for analysis in analyses for decision in analysis.decisions],
            tasks=[task for analysis in analyses for task in analysis.tasks],
            reminders=[reminder for analysis in analyses for reminder in analysis.reminders],
            summary=daily_summary_state(summary, fingerprint),
        )

    @app.post("/analyses", response_model=AnalysisResult)
    async def analyses(request: AnalysisRequest):
        return await run_in_threadpool(analyze_text, request.text)

    @app.post("/process")
    async def process(
        file: Annotated[UploadFile, File()],
        recorded_at: Annotated[str | None, Form()] = None,
        capture_mode: Annotated[str, Form()] = "manual",
        capture_session_id: Annotated[str | None, Form()] = None,
        chunk_index: Annotated[int | None, Form()] = None,
        capture_chunk_id: Annotated[str | None, Form()] = None,
    ):
        received_at = datetime.now(timezone.utc)
        parsed_recorded_at = parse_recorded_at(recorded_at, received_at)
        if capture_mode not in {"manual", "continuous", "smart"}:
            raise HTTPException(422, "capture_mode no válido")
        try:
            parsed_session_id = uuid.UUID(capture_session_id) if capture_session_id else None
            parsed_chunk_id = uuid.UUID(capture_chunk_id) if capture_chunk_id else None
        except ValueError as exc:
            raise HTTPException(422, "Los identificadores de captura deben ser UUID") from exc
        if capture_mode == "continuous" and (parsed_session_id is None or chunk_index is None):
            raise HTTPException(422, "Continuous requiere capture_session_id y chunk_index")
        if chunk_index is not None and chunk_index < 0:
            raise HTTPException(422, "chunk_index no puede ser negativo")
        if parsed_chunk_id is not None:
            with app.state.session_factory() as session:
                existing = await run_in_threadpool(
                    get_interaction_by_capture_chunk_id, session, parsed_chunk_id
                )
            if existing is not None:
                await file.close()
                return {
                    "interaction_id": existing.id,
                    "recorded_at": to_utc(existing.recorded_at),
                    "created_at": to_utc(existing.created_at),
                    "transcription": {
                        "text": existing.transcription,
                        "language": existing.language,
                        "model": existing.transcription_model,
                        "device": existing.transcription_device,
                        "compute_type": existing.transcription_compute_type,
                    },
                    "analysis": AnalysisResult.model_validate(existing.analysis),
                    "capture_mode": existing.capture_mode,
                    "capture_session_id": existing.capture_session_id,
                    "chunk_index": existing.chunk_index,
                    "capture_chunk_id": existing.capture_chunk_id,
                }
        transcription = await transcribe_upload(file)
        analysis = await run_in_threadpool(analyze_text, transcription["text"])
        interaction = await run_in_threadpool(
            persist_interaction,
            parsed_recorded_at,
            transcription,
            analysis,
            capture_mode=capture_mode,
            capture_session_id=parsed_session_id,
            chunk_index=chunk_index,
            capture_chunk_id=parsed_chunk_id,
        )
        return {
            "interaction_id": interaction.id,
            "recorded_at": to_utc(interaction.recorded_at),
            "created_at": to_utc(interaction.created_at),
            "transcription": transcription,
            "analysis": analysis,
            "capture_mode": interaction.capture_mode,
            "capture_session_id": interaction.capture_session_id,
            "chunk_index": interaction.chunk_index,
            "capture_chunk_id": interaction.capture_chunk_id,
        }

    @app.get("/interactions/{interaction_id}", response_model=InteractionResponse)
    async def interaction_detail(interaction_id: uuid.UUID):
        try:
            with app.state.session_factory() as session:
                interaction = await run_in_threadpool(get_interaction, session, interaction_id)
        except SQLAlchemyError as exc:
            raise HTTPException(503, "No se pudo consultar el histórico") from exc
        if interaction is None:
            raise HTTPException(404, "Interacción no encontrada")
        return interaction_response(interaction)

    @app.get("/interactions", response_model=list[InteractionResponse])
    async def interaction_history(
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
        from_: Annotated[datetime | None, Query(alias="from")] = None,
        to: datetime | None = None,
    ):
        try:
            if from_ is not None:
                from_ = to_utc(ensure_aware(from_))
            if to is not None:
                to = to_utc(ensure_aware(to))
            if from_ is not None and to is not None and from_ > to:
                raise HTTPException(422, "from debe ser anterior o igual a to")
            with app.state.session_factory() as session:
                items = await run_in_threadpool(list_interactions, session, from_, to, limit, offset)
        except HTTPException:
            raise
        except ValueError as exc:
            raise HTTPException(422, "from y to deben incluir zona horaria") from exc
        except SQLAlchemyError as exc:
            raise HTTPException(503, "No se pudo consultar el histórico") from exc
        return [interaction_response(item) for item in items]

    @app.get("/days/{day}", response_model=DayResponse)
    async def day_detail(day: date):
        try:
            interactions, fingerprint, summary = await run_in_threadpool(load_day, day)
        except SQLAlchemyError as exc:
            raise HTTPException(503, "No se pudo consultar el diario") from exc
        return day_response(day, interactions, fingerprint, summary)

    def save_daily_summary(day: date, expected_fingerprint: str, generation):
        start, end = day_interval(day, app.state.settings.app_timezone)
        try:
            with app.state.session_factory() as session:
                try:
                    current = list_interactions(session, start, end)
                    if interactions_fingerprint(current) != expected_fingerprint:
                        return None
                    summary = upsert_daily_summary(
                        session,
                        day=day,
                        timezone=app.state.settings.app_timezone,
                        result=generation.result.model_dump(mode="json"),
                        source_fingerprint=expected_fingerprint,
                        llm_model=generation.model,
                        generated_at=datetime.now(timezone.utc),
                    )
                    session.commit()
                    session.refresh(summary)
                    session.expunge(summary)
                    return summary
                except SQLAlchemyError:
                    session.rollback()
                    raise
        except SQLAlchemyError as exc:
            raise HTTPException(503, "No se pudo guardar el resumen diario") from exc

    @app.post("/days/{day}/summary", response_model=DailySummaryState)
    async def generate_day_summary(day: date):
        try:
            interactions, fingerprint, _ = await run_in_threadpool(load_day, day)
        except SQLAlchemyError as exc:
            raise HTTPException(503, "No se pudo consultar el diario") from exc
        if not interactions:
            raise HTTPException(409, "No hay interacciones para resumir ese día")
        generation = await run_in_threadpool(summarize_day, derived_daily_interactions(interactions))
        summary = await run_in_threadpool(save_daily_summary, day, fingerprint, generation)
        if summary is None:
            raise HTTPException(409, "El día cambió durante la generación; inténtalo de nuevo")
        return daily_summary_state(summary, fingerprint)

    return app


app = create_app()
