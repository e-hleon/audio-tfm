import io
import wave
from types import SimpleNamespace

import pytest

from app.transcription import AudioTooLong, InvalidAudio, Transcriber


def wav(seconds):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(16000)
        output.writeframes(b"\0\0" * (seconds * 16000))
    buffer.seek(0)
    return buffer


def transcriber_without_gpu():
    return Transcriber.__new__(Transcriber)


def test_real_decoder_rejects_invalid_audio():
    with pytest.raises(InvalidAudio):
        transcriber_without_gpu().transcribe(io.BytesIO(b"not audio"))


def test_duration_limit_before_inference():
    with pytest.raises(AudioTooLong):
        transcriber_without_gpu().transcribe(wav(61))


def test_segments_consumed_before_response():
    transcriber = transcriber_without_gpu()
    transcriber.model_name = "test"
    consumed = []

    def segments():
        consumed.append(True)
        yield SimpleNamespace(text=" Hola")
        yield SimpleNamespace(text=" mundo")

    transcriber.model = SimpleNamespace(
        model=SimpleNamespace(device="cuda", compute_type="int8_float16"),
        transcribe=lambda *args, **kwargs: (segments(), SimpleNamespace(language="es")),
    )
    assert transcriber.transcribe(wav(1))["text"] == "Hola mundo"
    assert consumed
