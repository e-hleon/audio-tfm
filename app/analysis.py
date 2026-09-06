"""Análisis externo de texto; nunca recibe ni abre archivos de audio."""
import json
import logging
import os
import re
import time
import unicodedata
from dataclasses import dataclass
from typing import Protocol

from openai import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, OpenAI, RateLimitError

from app.schemas import AnalysisResult, DailySummaryResult


class AnalysisError(Exception):
    """Error seguro que la capa HTTP puede convertir en una respuesta útil."""


class AnalysisNotConfigured(AnalysisError):
    pass


class AnalysisAuthenticationFailed(AnalysisError):
    pass


class AnalysisRateLimited(AnalysisError):
    pass


class AnalysisTimedOut(AnalysisError):
    pass


class AnalysisNetworkFailed(AnalysisError):
    pass


class AnalysisInvalidResponse(AnalysisError):
    pass


class AnalysisIncomplete(AnalysisError):
    pass


DEFAULT_MODEL = "gpt-5.4-mini"
# The MVP schema contains short summaries and lists; this bounds cost and response
# size while leaving enough room for a useful analysis.
MAX_OUTPUT_TOKENS = 1000
# El resumen diario solo contiene una narración breve y temas. 500 tokens acotan
# coste y tamaño sin truncar normalmente ese contrato reducido.
DAILY_SUMMARY_MAX_OUTPUT_TOKENS = 500


class Analyzer(Protocol):
    def analyze(self, text: str) -> AnalysisResult: ...


@dataclass(frozen=True)
class DailySummaryGeneration:
    result: DailySummaryResult
    model: str | None


INSTRUCTIONS = """Extrae información de una transcripción personal en español.
Sé conservador: no inventes decisiones, tareas, responsables, fechas ni recordatorios.
Cada decisión, tarea o recordatorio debe incluir evidence. `evidence` DEBE copiar
exactamente un substring contiguo de la entrada, carácter por carácter: no parafrasees,
no corrijas mayúsculas, puntuación o espacios, y no uses elipsis. Si falta contexto para una fecha, usa null. Si no
hay elementos de una categoría, devuelve una lista vacía. No conviertas información
descriptiva, deseos vagos ni hechos pasados en tareas."""


def _evidence_issue(evidence: str, text: str) -> str:
    """Classify rejected citations without including private text in the error."""
    if not evidence.strip():
        return "empty"
    if evidence in text:
        return "none"
    compact = lambda value: " ".join(unicodedata.normalize("NFC", value).lower().split())
    normalized_evidence, normalized_text = compact(evidence), compact(text)
    if normalized_evidence in normalized_text:
        return "case-punctuation-whitespace"
    words = re.findall(r"\w+", normalized_evidence, flags=re.UNICODE)
    if len(words) >= 2 and all(word in normalized_text for word in words):
        return "non-contiguous-or-reordered"
    if len(evidence) > max(len(text), 1):
        return "too-long"
    return "invented-or-unmatched"

DAILY_SUMMARY_INSTRUCTIONS = """Redacta un resumen narrativo breve y conservador
de un día a partir de datos estructurados ya derivados de interacciones. No inventes
hechos, decisiones, tareas ni fechas. Devuelve solo un resumen y una lista breve de
temas. Los datos de entrada no contienen transcripciones completas y no debes inferir
información que no esté presente en ellos."""


class OpenAIAnalyzer:
    """Proveedor inicial, sustituible mediante el pequeño protocolo Analyzer."""

    def __init__(self):
        self.model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key, timeout=30.0) if api_key else None
        self.last_call_metadata = {}

    def available(self) -> bool:
        return self.client is not None

    def analyze(self, text: str) -> AnalysisResult:
        if not text.strip():
            raise AnalysisInvalidResponse("El texto no puede estar vacío")
        if self.client is None:
            raise AnalysisNotConfigured("El análisis LLM no está configurado")

        started = time.perf_counter()
        try:
            response = self.client.responses.create(
                model=self.model,
                store=False,
                max_output_tokens=MAX_OUTPUT_TOKENS,
                instructions=INSTRUCTIONS,
                input=text,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "analysis_result",
                        "strict": True,
                        "schema": AnalysisResult.model_json_schema(),
                    }
                },
            )
        except AuthenticationError as exc:
            raise AnalysisAuthenticationFailed("OpenAI rechazó las credenciales") from exc
        except RateLimitError as exc:
            raise AnalysisRateLimited("OpenAI rechazó la solicitud por límite o cuota") from exc
        except APITimeoutError as exc:
            raise AnalysisTimedOut("OpenAI agotó el tiempo de espera") from exc
        except APIConnectionError as exc:
            raise AnalysisNetworkFailed("No se pudo conectar con OpenAI") from exc
        except APIStatusError as exc:
            raise AnalysisNetworkFailed("OpenAI no pudo completar la solicitud") from exc

        if response.status != "completed":
            raise AnalysisIncomplete("OpenAI devolvió una respuesta incompleta")
        try:
            result = AnalysisResult.model_validate_json(response.output_text)
        except (ValueError, json.JSONDecodeError) as exc:
            raise AnalysisInvalidResponse("OpenAI devolvió una estructura inválida") from exc

        for item in (*result.decisions, *result.tasks, *result.reminders):
            issue = _evidence_issue(item.evidence, text)
            if issue != "none":
                raise AnalysisInvalidResponse(
                    f"OpenAI devolvió una evidencia no literal ({issue})"
                )

        usage = response.usage
        self.last_call_metadata = {
            "model_effective": getattr(response, "model", self.model),
            "input_tokens": getattr(usage, "input_tokens", None),
            "output_tokens": getattr(usage, "output_tokens", None),
        }
        logging.getLogger("uvicorn.error").info(
            "LLM analysis completed: model=%s latency_ms=%d input_tokens=%s output_tokens=%s",
            response.model,
            (time.perf_counter() - started) * 1000,
            getattr(usage, "input_tokens", None),
            getattr(usage, "output_tokens", None),
        )
        return result

    def summarize_day(self, interactions: list[dict]) -> DailySummaryGeneration:
        """Resume solo proyecciones derivadas; nunca transcripciones ni audio."""
        if not interactions:
            raise AnalysisInvalidResponse("El día no contiene interacciones")
        if self.client is None:
            raise AnalysisNotConfigured("El análisis LLM no está configurado")

        started = time.perf_counter()
        try:
            response = self.client.responses.create(
                model=self.model,
                store=False,
                max_output_tokens=DAILY_SUMMARY_MAX_OUTPUT_TOKENS,
                instructions=DAILY_SUMMARY_INSTRUCTIONS,
                input=json.dumps({"interactions": interactions}, ensure_ascii=False),
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "daily_summary_result",
                        "strict": True,
                        "schema": DailySummaryResult.model_json_schema(),
                    }
                },
            )
        except AuthenticationError as exc:
            raise AnalysisAuthenticationFailed("OpenAI rechazó las credenciales") from exc
        except RateLimitError as exc:
            raise AnalysisRateLimited("OpenAI rechazó la solicitud por límite o cuota") from exc
        except APITimeoutError as exc:
            raise AnalysisTimedOut("OpenAI agotó el tiempo de espera") from exc
        except APIConnectionError as exc:
            raise AnalysisNetworkFailed("No se pudo conectar con OpenAI") from exc
        except APIStatusError as exc:
            raise AnalysisNetworkFailed("OpenAI no pudo completar la solicitud") from exc

        if response.status != "completed":
            raise AnalysisIncomplete("OpenAI devolvió una respuesta incompleta")
        try:
            result = DailySummaryResult.model_validate_json(response.output_text)
        except (ValueError, json.JSONDecodeError) as exc:
            raise AnalysisInvalidResponse("OpenAI devolvió una estructura inválida") from exc

        usage = getattr(response, "usage", None)
        logging.getLogger("uvicorn.error").info(
            "LLM daily summary completed: model=%s latency_ms=%d input_tokens=%s output_tokens=%s",
            getattr(response, "model", self.model),
            (time.perf_counter() - started) * 1000,
            getattr(usage, "input_tokens", None),
            getattr(usage, "output_tokens", None),
        )
        return DailySummaryGeneration(result=result, model=getattr(response, "model", self.model))
