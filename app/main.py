"""API síncrona: la respuesta HTTP espera al texto final."""
from contextlib import asynccontextmanager
from threading import Lock
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.transcription import AudioTooLong, InvalidAudio, Transcriber

MAX_BYTES = 10 * 1024 * 1024


def create_app(transcriber_factory=Transcriber):
    @asynccontextmanager
    async def lifespan(app):
        app.state.transcriber = transcriber_factory()
        app.state.inference_lock = Lock()
        yield
        del app.state.transcriber

    app = FastAPI(title="Audio TFM — transcripción local", lifespan=lifespan)

    @app.get("/health")
    def health():
        return {"status": "ready", **app.state.transcriber.details()}

    @app.post("/transcriptions")
    async def transcriptions(file: Annotated[UploadFile, File()]):
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

    return app


app = create_app()
