"""The gate after a stage: its answer is checked in code, and the stage is asked again at most twice.

Run on the pinned engine: a loop in a workflow is a back-edge the engine does not bound, so the count lives here, in
state. With the roster's plugins, an answer off its schema leaves the stage's key unwritten and the reason in state,
and the workflow comes on to this node, which decides.

A gate never raises for a bad answer. It routes: on to the next stage, back to its own, or out with the reason in
state under `FAILURE`, which the command says to the person in one sentence.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any

from google.adk.agents.context import Context
from google.adk.events import Event
from google.adk.workflow import FunctionNode

from .plugins import FINAL, MISMATCH, STAGE_ERROR
from .stages import BOUNDARY, FINDINGS

#: How often a stage is asked in all: once, and twice more with what was wrong.
MAX_TRIES = 3
#: The state key the reason is left under where a stage is given up.
FAILURE = "failure"
OK, AGAIN, GIVE_UP = "OK", "AGAIN", "GIVE_UP"
#: What a stage is told where its answer repeats this process's marker: written to a file and read by the next
#: stage, the marker would end a fenced section early there. Only a model can repeat it, and every answer of a
#: model comes through a gate.
ECHO = "the answer repeats a marker line of your instructions. Write no marker line."


def tries_key(stage: str) -> str:
    return f"tries_{stage}"


def checked(stage: str, check: Callable[[Mapping[str, Any]], list[str]]) -> FunctionNode:
    """The gate of `stage`, named `<stage>_gate`. `check` is given the state and says what is wrong with the answer
    at `state[stage]`, a sentence each; nothing wrong sends the run on."""

    def gate(ctx: Context) -> Event:
        tries = (ctx.state.get(tries_key(stage)) or 0) + 1
        answer = ctx.state.get(stage)
        if answer is None:  # the plugin's reason, or an answer that never came
            problems = [ctx.state.get(STAGE_ERROR) or MISMATCH]
        elif BOUNDARY in json.dumps(answer):
            problems = [ECHO]
        else:
            problems = check(ctx.state.to_dict())
        # The findings are a stage's own: cleared wherever the run leaves it, so no later stage is told them.
        counted = {tries_key(stage): tries, STAGE_ERROR: None, FINDINGS: None}
        if not problems:
            return Event(route=OK, state=counted)
        if tries >= MAX_TRIES or problems[0].startswith(FINAL):  # no second asking changes a final reason
            return Event(route=GIVE_UP, state={**counted, FAILURE: f"{stage}: {'; '.join(problems)}"})
        # The refused answer is cleared: were the next one off its schema, this one would stand there and be
        # checked a second time.
        return Event(route=AGAIN, state={**counted, FINDINGS: "\n".join(problems), stage: None})

    return FunctionNode(func=gate, name=f"{stage}_gate")
