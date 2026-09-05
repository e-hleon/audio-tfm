"""API síncrona: la respuesta HTTP espera al texto final."""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from threading import Lock
from typing import Annotated
import uuid

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from starlette.concurrency import run_in_threadpool
from sqlalchemy.exc import SQLAlchemyError

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
from app.schemas import AnalysisRequest, AnalysisResult
from app.db import make_session_factory
from app.repositories import create_interaction, get_interaction, list_interactions
from app.schemas import InteractionResponse
from app.time_utils import ensure_aware, to_utc
from app.transcription import AudioTooLong, InvalidAudio, Transcriber

MAX_BYTES = 10 * 1024 * 1024


def create_app(transcriber_factory=Transcriber, analyzer_factory=OpenAIAnalyzer, session_factory=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.transcriber = transcriber_factory()
        app.state.analyzer = analyzer_factory()
        app.state.session_factory = session_factory or make_session_factory()
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

    def parse_recorded_at(value: str | None, received_at: datetime) -> datetime:
        if value is None:
            return received_at
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return to_utc(ensure_aware(parsed))
        except (TypeError, ValueError) as exc:
            raise HTTPException(422, "recorded_at debe ser un ISO-8601 con zona horaria") from exc

    def persist_interaction(recorded_at: datetime, transcription: dict, analysis: AnalysisResult):
        try:
            with app.state.session_factory() as session:
                try:
                    interaction = create_interaction(
                        session,
                        recorded_at=recorded_at,
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
                except SQLAlchemyError:
                    session.rollback()
                    raise
        except SQLAlchemyError as exc:
            raise HTTPException(503, "No se pudo guardar la interacción") from exc

    def interaction_response(interaction) -> InteractionResponse:
        return InteractionResponse(
            id=interaction.id,
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

    @app.post("/analyses", response_model=AnalysisResult)
    async def analyses(request: AnalysisRequest):
        return await run_in_threadpool(analyze_text, request.text)

    @app.post("/process")
    async def process(
        file: Annotated[UploadFile, File()],
        recorded_at: Annotated[str | None, Form()] = None,
    ):
        received_at = datetime.now(timezone.utc)
        parsed_recorded_at = parse_recorded_at(recorded_at, received_at)
        transcription = await transcribe_upload(file)
        analysis = await run_in_threadpool(analyze_text, transcription["text"])
        interaction = await run_in_threadpool(
            persist_interaction, parsed_recorded_at, transcription, analysis
        )
        return {
            "interaction_id": interaction.id,
            "recorded_at": to_utc(interaction.recorded_at),
            "created_at": to_utc(interaction.created_at),
            "transcription": transcription,
            "analysis": analysis,
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

    return app


app = create_app()
