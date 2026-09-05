from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from fastapi.testclient import TestClient

from app.analysis import (
    AnalysisAuthenticationFailed,
    AnalysisIncomplete,
    AnalysisInvalidResponse,
    AnalysisNetworkFailed,
    AnalysisNotConfigured,
    AnalysisRateLimited,
    AnalysisTimedOut,
)
from app.main import MAX_BYTES, create_app
from app.schemas import AnalysisResult
from app.transcription import AudioTooLong, InvalidAudio


class FakeTranscriber:
    def __init__(self):
        self.files = []
        self.error = None

    def details(self):
        return {"model": "fake", "device": "cuda", "compute_type": "int8_float16"}

    def transcribe(self, file):
        self.files.append(file)
        if self.error:
            raise self.error
        return {"text": "Texto de prueba", "language": "es", **self.details()}


class FakeAnalyzer:
    def __init__(self):
        self.texts = []
        self.error = None

    def available(self):
        return True

    def analyze(self, text):
        self.texts.append(text)
        if self.error:
            raise self.error
        return AnalysisResult.model_validate({
            "summary": "Resumen de prueba", "topics": ["prueba"],
            "decisions": [], "tasks": [], "reminders": [],
        })


@pytest.fixture
def api():
    transcriber = FakeTranscriber()
    analyzer = FakeAnalyzer()
    with TestClient(create_app(lambda: transcriber, lambda: analyzer)) as client:
        yield client, transcriber, analyzer


def test_model_loaded_once_and_result(api):
    client, transcriber, _ = api
    assert client.get("/health").json()["status"] == "ready"
    for _ in range(2):
        response = client.post("/transcriptions", files={"file": ("test.wav", b"audio" * 300_000)})
        assert response.status_code == 200
        assert response.json()["text"] == "Texto de prueba"
    assert len(transcriber.files) == 2
    assert all(file.closed for file in transcriber.files)


@pytest.mark.parametrize("error,status", [(InvalidAudio("inválido"), 400), (AudioTooLong("largo"), 413)])
def test_expected_errors_close_upload(api, error, status):
    client, transcriber, _ = api
    transcriber.error = error
    response = client.post("/transcriptions", files={"file": ("test.wav", b"x" * 2_000_000)})
    assert response.status_code == status
    assert transcriber.files[0].closed
    transcriber.error = None
    assert client.post("/transcriptions", files={"file": ("test.wav", b"audio")}).status_code == 200


def test_missing_empty_oversize(api):
    client, transcriber, _ = api
    assert client.post("/transcriptions").status_code == 422
    assert client.post("/transcriptions", files={"file": ("empty.wav", b"")}).status_code == 400
    assert client.post("/transcriptions", files={"file": ("large.wav", b"x" * (MAX_BYTES + 1))}).status_code == 413
    assert not transcriber.files


def test_unexpected_failure_closes_file_and_releases_lock(api):
    client, transcriber, _ = api
    transcriber.error = RuntimeError("GPU failure")
    with pytest.raises(RuntimeError):
        client.post("/transcriptions", files={"file": ("test.wav", b"audio")})
    assert transcriber.files[0].closed
    transcriber.error = None
    assert client.post("/transcriptions", files={"file": ("test.wav", b"audio")}).status_code == 200


def test_busy_request_rejected(api):
    client, transcriber, _ = api
    entered, release = Event(), Event()
    original = transcriber.transcribe

    def slow(file):
        entered.set()
        assert release.wait(10)
        return original(file)

    transcriber.transcribe = slow
    with ThreadPoolExecutor() as pool:
        first = pool.submit(client.post, "/transcriptions", files={"file": ("test.wav", b"audio")})
        try:
            assert entered.wait(10)
            assert client.post("/transcriptions", files={"file": ("test.wav", b"audio")}).status_code == 503
            assert client.get("/health").status_code == 200
        finally:
            release.set()
        assert first.result().status_code == 200


def test_factory_called_once_per_lifespan():
    calls = []

    def factory():
        calls.append(True)
        return FakeTranscriber()

    with TestClient(create_app(factory, FakeAnalyzer)) as client:
        for _ in range(2):
            assert client.post("/transcriptions", files={"file": ("test.wav", b"audio")}).status_code == 200
        assert len(calls) == 1


def test_analyses_returns_structured_result_and_only_text(api):
    client, _, analyzer = api
    response = client.post("/analyses", json={"text": "Ana preparará el informe."})
    assert response.status_code == 200
    assert response.json() == {
        "summary": "Resumen de prueba", "topics": ["prueba"],
        "decisions": [], "tasks": [], "reminders": [],
    }
    assert analyzer.texts == ["Ana preparará el informe."]


def test_analyses_rejects_blank_text(api):
    client, _, _ = api
    assert client.post("/analyses", json={"text": "  "}).status_code == 422


@pytest.mark.parametrize("error,status", [
    (AnalysisNotConfigured(""), 503),
    (AnalysisAuthenticationFailed(""), 502),
    (AnalysisRateLimited(""), 429),
    (AnalysisTimedOut(""), 504),
    (AnalysisNetworkFailed(""), 503),
    (AnalysisInvalidResponse(""), 502),
    (AnalysisIncomplete(""), 502),
])
def test_analyses_maps_provider_errors_without_details(api, error, status):
    client, _, analyzer = api
    analyzer.error = error
    response = client.post("/analyses", json={"text": "Texto público"})
    assert response.status_code == status
    assert "Texto público" not in response.text
    if status == 429:
        assert "límite de peticiones o cuota insuficiente" in response.json()["detail"]


def test_process_reuses_transcription_and_sends_its_text_only(api):
    client, transcriber, analyzer = api
    response = client.post("/process", files={"file": ("test.wav", b"audio")})
    assert response.status_code == 200
    body = response.json()
    assert body["transcription"]["text"] == "Texto de prueba"
    assert body["analysis"]["summary"] == "Resumen de prueba"
    assert analyzer.texts == ["Texto de prueba"]
    assert all(file.closed for file in transcriber.files)
