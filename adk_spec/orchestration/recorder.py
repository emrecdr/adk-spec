"""The recorder: each model call of a command, as it was sent and as it was answered.

It stands after the scrub in the roster, and before everything else. Run on the pinned engine
(`q19_plan3_recorder_plugin_probe.py`): there it is handed each instruction already filled from state, sees each
answer before the mismatch plugin replaces it, and knows the stage by the agent's name. A call the ledger refuses
reaches it as a request and no answer, so a call is closed when the next one starts, or when the command reads
`calls`.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any, override

from google.adk.models.llm_response import LlmResponse
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.utils.content_utils import extract_text_from_content

from ..domain.secrets import scrub
from ..workspace.runs import Call
from .models import said
from .run import Usage
from .stages import FINDINGS


def _kept(answer: str | None) -> str | None:
    """An answer as a recording keeps it: as it came, less any known secret shape. A model is sent none, since the
    scrub reads every request first; an answer that holds one all the same is not written to disk."""
    return scrub(answer)[0] if answer else None


class Recorder(BasePlugin):
    """What a command's stages were sent and what each answered, in order."""

    def __init__(self, heard: Callable[[str, bool], None] | None = None) -> None:
        """`heard` is told of each call as it starts: its stage, and whether a gate asked for it again. It is how a
        command says where it is while it works; the recorder hears every call first, so nothing else is needed."""
        super().__init__(name="recorder")
        self._heard = heard
        self._kept: list[Call] = []
        #: The call sent and not answered yet: its fields so far, and the clock at its start.
        self._sent: tuple[dict[str, Any], float] | None = None

    @property
    def calls(self) -> tuple[Call, ...]:
        self._close()
        return tuple(self._kept)

    def _close(self, **came: Any) -> None:
        if self._sent is None:
            return
        (sent, started), self._sent = self._sent, None
        self._kept.append(Call(**sent, **came, seconds=round(time.perf_counter() - started, 3)))

    @override
    async def before_model_callback(self, *, callback_context: Any, llm_request: Any) -> LlmResponse | None:
        self._close()  # the call before this one got no answer: refused at the ceiling, or it raised
        sent = {
            "stage": callback_context.agent_name,
            "instruction": str(llm_request.config.system_instruction or ""),
            "findings": callback_context.state.get(FINDINGS),
        }
        self._sent = (sent, time.perf_counter())
        if self._heard is not None:
            self._heard(sent["stage"], bool(sent["findings"]))
        return None

    @override
    async def after_model_callback(self, *, callback_context: Any, llm_response: Any) -> LlmResponse | None:
        if llm_response.partial:  # a streamed piece: the whole answer follows it
            return None
        error = llm_response.error_code and f"{llm_response.error_code}: {llm_response.error_message or ''}".strip()
        counted = llm_response.usage_metadata
        self._close(
            answer=_kept(extract_text_from_content(llm_response.content)),
            error=error or None,
            tokens=Usage.of(counted).total if counted is not None else 0,
        )
        return None

    @override
    async def on_model_error_callback(
        self,
        *,
        callback_context: Any,
        llm_request: Any,
        error: Exception,
    ) -> LlmResponse | None:
        self._close(error=f"{type(error).__name__}: {said(error)}")
        return None  # recorded, and left to fail as it would
