"""Test doubles for the agent graphs, so no test needs a key or a network (task 6.2)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableLambda
from pydantic import Field

if TYPE_CHECKING:
    from collections.abc import Sequence

    from langchain_core.messages import BaseMessage
    from pydantic import BaseModel

# Plausible token counts, so the call log has something to store.
USAGE = {"input_tokens": 900, "output_tokens": 180, "total_tokens": 1080}


class FakeChatModel(BaseChatModel):
    """Answers from a queue, shaped exactly as ``with_structured_output(include_raw=True)``.

    ``answers`` holds the objects to return in order; ``None`` stands for an answer that
    did not match the schema, and ``raises`` for a transport failure. The last answer
    repeats, so a test that expects the graph to retry twice only has to queue one lie.
    """

    answers: list[Any] = Field(default_factory=list)
    raises: bool = False
    # Every prompt the model was given, so a test can assert what it was told.
    prompts: list[str] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "fake"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Required by ``BaseChatModel``; the agents only ever use structured output."""
        return ChatResult(generations=[ChatGeneration(message=AIMessage("ok"))])

    def with_structured_output(
        self, schema: Any, *, include_raw: bool = False, **kwargs: Any
    ) -> RunnableLambda[Any, Any]:
        def answer(messages: Any) -> Any:
            self.prompts.append(_text(messages))
            if self.raises:
                raise RuntimeError("throttled")
            parsed = self.answers.pop(0) if len(self.answers) > 1 else _last(self.answers)
            if not include_raw:
                return parsed
            return {
                "raw": AIMessage(content="", usage_metadata=USAGE),
                "parsed": parsed,
                "parsing_error": None if parsed else ValueError("no object in the answer"),
            }

        return RunnableLambda(answer)


def _last(answers: Sequence[BaseModel | None]) -> Any:
    return answers[0] if answers else None


def _text(messages: Any) -> str:
    if isinstance(messages, str):
        return messages
    return "\n".join(str(getattr(message, "content", message)) for message in messages)
