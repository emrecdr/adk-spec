"""The verify stage: the work, read as a diff, judged against each requirement of the change.

The model gives a verdict a requirement and quotes the lines that show it. Code then keeps a `met` only where a
quoted line is in the diff, on the side that can show it.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from google.adk.agents import LlmAgent

from ...domain.drafts import VerdictsDraft
from . import THE_DELTAS, instruction, read_back, section, stage

KEY = "verify"
#: The state keys the instruction reads beside the deltas: the tasks as their file, which requirements to judge and
#: on which side of the diff each is shown, and the diff.
TASKS_TEXT = "tasks_text"
REQUIRED = "required"
DIFF = "diff"
OPENING = "You judge whether a diff meets the requirements of a change. You change nothing."
GUIDE = """\
Give one verdict for each requirement listed under the requirements to judge, and for no other.
met: the diff shows the requirement done, every scenario of it. Quote the lines that show it, each copied word for
word without its + or - sign, with the path the diff gives its file. For a requirement the change adds or modifies,
quote lines the diff adds. For one the change removes, quote lines the diff removes.
unmet: the diff shows it not done, or done wrong. Say what is missing.
unclear: the diff does not let you tell. Say what you would need to see.
A test that exercises the behaviour is good evidence. A comment or a name alone is not.
Judge what the diff shows, not which boxes of the tasks are ticked."""


def build_verify() -> LlmAgent:
    text = instruction(
        OPENING,
        GUIDE,
        THE_DELTAS,
        section("## The tasks", "tasks", TASKS_TEXT, optional=True),
        section("## The requirements to judge", "required", REQUIRED),
        section("## The diff", "diff", DIFF),
    )
    return stage(KEY, "Judges a diff against a change's requirements.", text, VerdictsDraft)


def read_verify(state: Mapping[str, Any]) -> VerdictsDraft | str:
    return read_back(state, KEY, VerdictsDraft)
