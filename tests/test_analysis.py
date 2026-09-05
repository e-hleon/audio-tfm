from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.analysis import (
    AnalysisAuthenticationFailed,
    AnalysisIncomplete,
    AnalysisInvalidResponse,
    AnalysisNetworkFailed,
    AnalysisNotConfigured,
    AnalysisRateLimited,
    AnalysisTimedOut,
    MAX_OUTPUT_TOKENS,
    OpenAIAnalyzer,
)
from app.schemas import AnalysisRequest, AnalysisResult


def payload():
    return {
        "summary": "Se acordó preparar una propuesta.",
        "topics": ["propuesta"],
        "decisions": [{"text": "Preparar una propuesta", "evidence": "Decidimos preparar una propuesta."}],
        "tasks": [{"text": "Preparar una propuesta", "assignee": "Ana", "due_date": None,
                   "evidence": "Ana preparará una propuesta."}],
        "reminders": [{"text": "Revisar la propuesta", "when": "el lunes",
                       "evidence": "Recuérdame revisarla el lunes."}],
    }


def test_schema_accepts_nullable_fields_and_empty_categories():
    result = AnalysisResult.model_validate({**payload(), "decisions": [], "tasks": [], "reminders": []})
    assert result.decisions == []
    assert result.tasks == []
    assert result.reminders == []


@pytest.mark.parametrize("text", ["", "   "])
def test_request_rejects_blank_text(text):
    with pytest.raises(ValidationError):
        AnalysisRequest(text=text)


def test_schema_rejects_extra_or_missing_evidence():
    invalid = payload()
    invalid["tasks"] = [{"text": "Hacer algo", "assignee": None, "due_date": None}]
    with pytest.raises(ValidationError):
        AnalysisResult.model_validate(invalid)


def test_openai_request_sends_only_text_and_uses_strict_schema(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    analyzer = OpenAIAnalyzer()
    calls = []
    analyzer.client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: calls.append(kwargs) or SimpleNamespace(
        status="completed", output_text=AnalysisResult.model_validate(payload()).model_dump_json(),
        model="gpt-5.4-mini-2026-03-17", usage=SimpleNamespace(input_tokens=10, output_tokens=20),
    )))

    source = "Decidimos preparar una propuesta. Ana preparará una propuesta. Recuérdame revisarla el lunes."
    result = analyzer.analyze(source)
    assert result.tasks[0].assignee == "Ana"
    request = calls[0]
    assert request["input"] == source
    assert "audio" not in request
    assert request["store"] is False
    assert request["max_output_tokens"] == MAX_OUTPUT_TOKENS
    assert request["text"]["format"]["type"] == "json_schema"
    assert request["text"]["format"]["strict"] is True


def test_openai_rejects_evidence_not_present_in_source(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    analyzer = OpenAIAnalyzer()
    invalid = payload()
    invalid["tasks"][0]["evidence"] = "Esta frase no aparece"
    analyzer.client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: SimpleNamespace(
        status="completed", output_text=AnalysisResult.model_validate(invalid).model_dump_json(),
        model="gpt-5.4-mini-2026-03-17", usage=None,
    )))
    with pytest.raises(AnalysisInvalidResponse, match="evidencia"):
        analyzer.analyze("Decidimos preparar una propuesta. Ana preparará una propuesta. Recuérdame revisarla el lunes.")


def test_openai_analyzer_requires_configuration(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(AnalysisNotConfigured):
        OpenAIAnalyzer().analyze("Texto de prueba")


def test_incomplete_and_invalid_provider_responses(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    analyzer = OpenAIAnalyzer()
    analyzer.client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: SimpleNamespace(status="incomplete")))
    with pytest.raises(AnalysisIncomplete):
        analyzer.analyze("Texto")

    analyzer.client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: SimpleNamespace(
        status="completed", output_text='{"summary": "incompleto"}', model="test", usage=None,
    )))
    with pytest.raises(AnalysisInvalidResponse):
        analyzer.analyze("Texto")


@pytest.mark.parametrize("error", [
    AnalysisAuthenticationFailed(""), AnalysisRateLimited(""), AnalysisTimedOut(""), AnalysisNetworkFailed(""),
])
def test_provider_error_types_are_distinct(error):
    assert str(error) == ""
