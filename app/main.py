"""API síncrona: la respuesta HTTP espera al texto final."""
from contextlib import asynccontextmanager
from threading import Lock
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

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
from app.transcription import AudioTooLong, InvalidAudio, Transcriber

MAX_BYTES = 10 * 1024 * 1024


def create_app(transcriber_factory=Transcriber, analyzer_factory=OpenAIAnalyzer):
    @asynccontextmanager
    async def lifespan(app):
        app.state.transcriber = transcriber_factory()
        app.state.analyzer = analyzer_factory()
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

    @app.post("/analyses", response_model=AnalysisResult)
    async def analyses(request: AnalysisRequest):
        return await run_in_threadpool(analyze_text, request.text)

    @app.post("/process")
    async def process(file: Annotated[UploadFile, File()]):
        transcription = await transcribe_upload(file)
        analysis = await run_in_threadpool(analyze_text, transcription["text"])
        return {"transcription": transcription, "analysis": analysis}

    return app


app = create_app()
