"""The plugins every app of this package carries.

`SchemaMismatch` turns an answer that does not fit its schema into the stage's own error. Run on the pinned engine:
ADK alone validates the answer and raises, which ends the run; with the answer replaced by an error response the
workflow goes on to the next node with the stage's key unwritten, and a gate there can ask again.

`UsageLedger` counts each stage's calls and tokens as the provider reports them, and past a ceiling refuses a call
before it is sent. The stages of a command run one after another, so the count is exact when the next call asks.

Each leaves its reason in state under `STAGE_ERROR`, where the gate after the stage reads why there is no answer.
The ledger stands first in the roster: a plugin that answers a hook ends it for the plugins after it, and an answer
off its schema was still paid for.
"""

from __future__ import annotations

from typing import Any, override

from google.adk.models.llm_response import LlmResponse
from google.adk.plugins.base_plugin import BasePlugin

# ADK's own two functions, the ones its agent and its workflow node validate an answer with. `_schema_utils` is
# private: the pinned ADK holds it, and an upgrade that moved it fails this import, and the suite, at once.
from google.adk.utils._schema_utils import validate_schema
from google.adk.utils.content_utils import extract_text_from_content
from pydantic import BaseModel, ValidationError

from .run import Usage

#: The state key a plugin leaves its reason under, for the gate after the stage.
STAGE_ERROR = "stage_error"
MISMATCH = "the answer did not fit its schema"
#: How the ledger's refusal begins, and its error code.
CEILING = "CEILING"
#: How the reason begins where the provider itself ended an answer: cut at the model's output limit, or filtered.
ENDED = "the provider ended the answer"
#: The reasons no second asking can change: the same request would meet the same ceiling, or be cut the same way.
FINAL = (CEILING, ENDED)


class SchemaMismatch(BasePlugin):
    """An answer off the schema its request asked for becomes the stage's own error."""

    def __init__(self) -> None:
        super().__init__(name="schema_mismatch")
        self.schemas: dict[str, type[BaseModel]] = {}

    @override
    async def before_model_callback(self, *, callback_context: Any, llm_request: Any) -> LlmResponse | None:
        schema = llm_request.config.response_schema
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            self.schemas[callback_context.agent_name] = schema
        return None

    @override
    async def after_model_callback(self, *, callback_context: Any, llm_response: Any) -> LlmResponse | None:
        if llm_response.partial:  # a streamed piece: the whole answer follows it
            return None
        if llm_response.error_code:  # the provider's own verdict, which a cut answer's broken JSON would hide
            why = f"{ENDED}: {llm_response.error_code}: {llm_response.error_message or 'no reason given'}"
            callback_context.state[STAGE_ERROR] = why
            return LlmResponse(
                error_code=llm_response.error_code, error_message=why, usage_metadata=llm_response.usage_metadata
            )
        schema = self.schemas.get(callback_context.agent_name)
        text = extract_text_from_content(llm_response.content) if schema is not None else ""
        if schema is None or not text.strip():
            return None  # nothing ADK would validate
        try:
            validate_schema(schema, text)
        except ValidationError as exc:
            why = f"{MISMATCH}: {exc.errors()[0]['msg']}"
            callback_context.state[STAGE_ERROR] = why
            return LlmResponse(
                error_code="SCHEMA_MISMATCH", error_message=why, usage_metadata=llm_response.usage_metadata
            )
        return None


class UsageLedger(BasePlugin):
    """Each stage's calls and tokens, and a ceiling no call is sent past."""

    def __init__(self, ceiling: int | None = None) -> None:
        super().__init__(name="usage_ledger")
        self.ceiling = ceiling
        #: What each stage spent, by its agent's name.
        self.spent: dict[str, Usage] = {}

    @property
    def total(self) -> Usage:
        return sum(self.spent.values(), Usage())

    @override
    async def before_model_callback(self, *, callback_context: Any, llm_request: Any) -> LlmResponse | None:
        if self.ceiling is None or self.total.total < self.ceiling:
            return None
        why = f"{CEILING}: the run's token ceiling of {self.ceiling:,} is spent"
        callback_context.state[STAGE_ERROR] = why
        return LlmResponse(error_code=CEILING, error_message=why)

    @override
    async def after_model_callback(self, *, callback_context: Any, llm_response: Any) -> LlmResponse | None:
        usage = llm_response.usage_metadata
        if llm_response.partial or usage is None:  # a streamed piece, or a call refused before it was sent
            return None
        stage = callback_context.agent_name
        self.spent[stage] = self.spent.get(stage, Usage()) + Usage.of(usage)
        return None


def roster(ledger: UsageLedger, recorder: BasePlugin | None = None) -> list[BasePlugin]:
    """The plugins of every app: the recorder where the command keeps one, then the ledger, then the mismatch. Each
    must read an answer before the mismatch replaces it, and the recorder a request before the ledger refuses it.
    The ledger and the recorder are the command's own, one for all its runs."""
    return [*([recorder] if recorder is not None else []), ledger, SchemaMismatch()]
