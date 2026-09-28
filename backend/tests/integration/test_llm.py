"""The real provider, once: a validated object back and a row in ``llm_calls`` (task 6.1).

Skipped unless a model is configured, so the offline suite is unaffected.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import func, select

from mdia.agents.investigation import PURPOSE, build_investigation, investigate
from mdia.agents.llm import get_chat_model, structured
from mdia.agents.prompts import DIAGNOSIS_PROMPT_VERSION, DIAGNOSIS_SYSTEM, diagnosis_prompt
from mdia.agents.schemas import LlmDiagnosis
from mdia.domain.evidence import build_evidence
from mdia.models import LlmCall
from mdia.repositories.llm_calls import LlmCallRepository
from tests.builders import creative_fatigue

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


@pytest.fixture
def model() -> BaseChatModel:
    chat = get_chat_model()
    if chat is None:
        pytest.skip("LLM_MODEL not configured")
    return chat


def test_a_structured_call_returns_a_validated_object_and_a_logged_row(
    model: BaseChatModel, db_session: Session
) -> None:
    evidence = build_evidence(creative_fatigue())

    completion = structured(
        model,
        LlmDiagnosis,
        diagnosis_prompt(evidence),
        system=DIAGNOSIS_SYSTEM,
        purpose=PURPOSE,
        prompt_version=DIAGNOSIS_PROMPT_VERSION,
    )

    assert completion.ok
    assert completion.output is not None
    assert completion.output.hypotheses
    assert completion.record.latency_ms > 0

    LlmCallRepository(db_session).log([completion.record])
    db_session.commit()

    assert db_session.scalar(select(func.count()).select_from(LlmCall)) == 1


def test_a_real_opportunity_is_diagnosed(model: BaseChatModel) -> None:
    result = investigate(build_investigation(model), creative_fatigue())

    assert result.diagnosis.hypotheses
    assert result.recommendation is not None
    # Either way it is a real diagnosis; the label says which, and a grounded LLM
    # answer must have left a call that says so.
    assert result.source in {"llm", "rules"}
    if result.source == "llm":
        assert result.calls[-1].grounded is True
