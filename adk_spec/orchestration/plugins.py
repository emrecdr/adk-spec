"""The plugins every app of this package carries.

`SchemaMismatch` turns an answer that does not fit its schema into the stage's own error. Run on the pinned engine:
ADK alone validates the answer and raises, which ends the run; with the answer replaced by an error response the
workflow goes on to the next node with the stage's key unwritten, and a gate there can ask again.

`UsageLedger` counts each stage's calls and tokens as the provider reports them, and past a ceiling refuses a call
before it is sent. The stages of a command run one after another, so the count is exact when the next call asks.

`Scrub` hides known secret shapes in everything a model is about to be sent, and sends nothing where it cannot.

Each leaves its reason in state under `STAGE_ERROR`, where the gate after the stage reads why there is no answer.
The scrub stands first in the roster, so that the recorder and the provider both read what it left; the ledger
stands before the mismatch: a plugin that answers a hook ends it for the plugins after it, and an answer off its
schema was still paid for.
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

from ..domain.secrets import scrub
from .run import Usage

#: The state key a plugin leaves its reason under, for the gate after the stage.
STAGE_ERROR = "stage_error"
MISMATCH = "the answer did not fit its schema"
#: How the ledger's refusal begins, and its error code.
CEILING = "CEILING"
#: How the reason begins where the provider itself ended an answer: cut at the model's output limit, or filtered.
ENDED = "the provider ended the answer"
#: How the scrub's refusal begins, and its error code: what would be sent could not be scrubbed of secrets.
REDACTION = "REDACTION_FAILED"
#: The reasons no second asking can change: the same request would meet the same ceiling, be cut the same way, or
#: fail the same scrub.
FINAL = (CEILING, ENDED, REDACTION)


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

    def refusal(self) -> str | None:
        """Why the next call would be refused, or nothing while the ceiling holds."""
        if self.ceiling is None or self.total.total < self.ceiling:
            return None
        return f"{CEILING}: the run's token ceiling of {self.ceiling:,} is spent"

    @override
    async def before_model_callback(self, *, callback_context: Any, llm_request: Any) -> LlmResponse | None:
        if (why := self.refusal()) is None:
            return None
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


class Scrub(BasePlugin):
    """Known secret shapes hidden in every request before anything else reads it: its instruction, and each text
    of its content. Fail closed: where the scrub raises, the call is not sent."""

    def __init__(self) -> None:
        super().__init__(name="scrub")
        #: How many secrets were hidden, over every call.
        self.redacted = 0

    @override
    async def before_model_callback(self, *, callback_context: Any, llm_request: Any) -> LlmResponse | None:
        try:
            instruction = llm_request.config.system_instruction
            if isinstance(instruction, str):
                llm_request.config.system_instruction, count = scrub(instruction)
                self.redacted += count
            elif instruction is not None:  # ADK writes a string: any other shape is refused, never sent unread
                raise TypeError(f"the instruction is a {type(instruction).__name__}, and the scrub reads a string")
            for content in llm_request.contents or ():
                for part in content.parts or ():
                    if part.text:
                        part.text, count = scrub(part.text)
                        self.redacted += count
        except Exception as exc:  # noqa: BLE001 -- a scrub that breaks must not send what it did not read
            why = f"{REDACTION}: nothing was sent, since it could not be scrubbed of secrets first: {exc}"
            callback_context.state[STAGE_ERROR] = why
            return LlmResponse(error_code=REDACTION, error_message=why)
        return None


def roster(ledger: UsageLedger, recorder: BasePlugin | None = None) -> list[BasePlugin]:
    """The plugins of every app: the scrub, the recorder where the command keeps one, then the ledger, then the
    mismatch. The scrub is first, so nothing after it reads a secret. Each
    must read an answer before the mismatch replaces it, and the recorder a request before the ledger refuses it.
    The ledger is the command's own, one for everything it spends; the recorder is one pass's."""
    return [Scrub(), *([recorder] if recorder is not None else []), ledger, SchemaMismatch()]
