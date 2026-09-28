"""The only file that knows which provider is behind the agents (NFR-4).

Three things live here: the chat model built from the environment, one structured-output
call at temperature 0, and the record of that call which NFR-3 asks to be logged. The
record is returned rather than written — nothing under ``agents/`` touches the database.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Any

import structlog
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage

from mdia.core.settings import get_settings

if TYPE_CHECKING:
    from collections.abc import Mapping

    from langchain_core.language_models import BaseChatModel
    from pydantic import BaseModel

    from mdia.core.settings import Settings

log = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class CallRecord:
    """One call to the model, as the ``llm_calls`` table stores it (NFR-3)."""

    purpose: str
    provider: str
    model: str
    prompt_version: str
    # 1 for the first try; a retry after a grounding failure is 2 (FR-8.3).
    attempt: int
    latency_ms: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    # Whether this answer passed the grounding guard, and whether the investigation
    # ended up in the rule-based fallback anyway. Both are filled in by the graph.
    grounded: bool = False
    fallback: bool = False
    error: str | None = None


@dataclass(frozen=True, slots=True)
class Completion[T: BaseModel]:
    """A structured answer, or the reason there isn't one, plus what the call cost."""

    output: T | None
    record: CallRecord

    @property
    def ok(self) -> bool:
        return self.output is not None


@lru_cache
def get_chat_model() -> BaseChatModel | None:
    """The configured model, or ``None`` when none is set so the agents use the rules.

    Cached: building the client reads credentials and opens a session, and every
    investigation in a run shares it.
    """
    settings = get_settings()
    if not settings.llm_model:
        log.info("llm.not_configured")
        return None
    model: BaseChatModel = init_chat_model(
        settings.llm_model,
        model_provider=settings.llm_provider,
        temperature=settings.llm_temperature,
        **_credentials(settings),
    )
    log.info("llm.ready", provider=settings.llm_provider, model=settings.llm_model)
    return model


def structured[T: BaseModel](
    model: BaseChatModel,
    schema: type[T],
    prompt: str,
    *,
    system: str,
    purpose: str,
    prompt_version: str,
    attempt: int = 1,
) -> Completion[T]:
    """One structured-output call. Transport failures raise; a bad answer comes back.

    A malformed answer is the model's problem to fix, so it is returned as an error the
    graph can feed back to it. A network or throttling failure is not, so it propagates
    to the node's ``RetryPolicy``.
    """
    settings = get_settings()
    started = time.perf_counter()
    result = model.with_structured_output(schema, include_raw=True).invoke(
        [SystemMessage(system), HumanMessage(prompt)]
    )
    elapsed = int((time.perf_counter() - started) * 1000)
    output, error, usage = _unpack(result, schema)
    record = CallRecord(
        purpose=purpose,
        provider=settings.llm_provider,
        model=settings.llm_model,
        prompt_version=prompt_version,
        attempt=attempt,
        latency_ms=elapsed,
        input_tokens=usage.get("input_tokens"),
        output_tokens=usage.get("output_tokens"),
        error=error,
    )
    log.info(
        "llm.call",
        purpose=purpose,
        attempt=attempt,
        latency_ms=elapsed,
        tokens=usage.get("total_tokens"),
        error=error,
    )
    return Completion(output, record)


def failure_record(purpose: str, prompt_version: str, error: str) -> CallRecord:
    """A row for a call that never produced an answer, so the failure stays traceable."""
    settings = get_settings()
    return CallRecord(
        purpose=purpose,
        provider=settings.llm_provider,
        model=settings.llm_model,
        prompt_version=prompt_version,
        attempt=1,
        latency_ms=0,
        fallback=True,
        error=error[:500],
    )


def _unpack[T: BaseModel](
    result: Any, schema: type[T]
) -> tuple[T | None, str | None, Mapping[str, int]]:
    """Split ``include_raw=True``'s answer into the object, the parse error and the usage."""
    if not isinstance(result, dict):
        return (result if isinstance(result, schema) else None), None, {}
    parsed = result.get("parsed")
    problem = result.get("parsing_error")
    raw = result.get("raw")
    usage = getattr(raw, "usage_metadata", None) or {}
    error = None if problem is None else f"{type(problem).__name__}: {problem}"
    if not isinstance(parsed, schema):
        return None, error or "the model returned nothing matching the schema", usage
    return parsed, error, usage


def _credentials(settings: Settings) -> dict[str, Any]:
    """Credentials per provider: pydantic-settings keeps ``.env`` out of ``os.environ``,
    so the SDKs cannot find them by themselves."""
    if settings.llm_provider.startswith("bedrock"):
        return _present(
            region_name=settings.aws_region,
            aws_access_key_id=_secret(settings.aws_access_key_id),
            aws_secret_access_key=_secret(settings.aws_secret_access_key),
        )
    if settings.llm_provider.startswith("google"):
        return _present(google_api_key=_secret(settings.google_api_key))
    return {}


def _present(**values: str | None) -> dict[str, Any]:
    """Drop the credentials that aren't set, so the SDK's own discovery still applies."""
    return {name: value for name, value in values.items() if value}


def _secret(value: Any) -> str | None:
    return None if value is None else str(value.get_secret_value())
