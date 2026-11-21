"""The brief stage: why the change is wanted, what changes, what does not, and which capabilities it touches."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from google.adk.agents import LlmAgent

from ...domain.drafts import BriefDraft
from . import CAPABILITIES, ENDING, REQUEST, RETRY, fenced, placeholder, read_back, stage

KEY = "brief"
#: The state keys the instruction reads beside the request: the repository's rules, and a person's answers.
CONSTITUTION = "constitution"
ANSWERS = "answers"
OPENING = "You write the brief of a change for a spec-driven workflow. You write no spec and no code."
GUIDE = """\
Say why the change is wanted, what will be different once it is done, what it leaves alone, and what else it affects.
State what you assume. A point you cannot settle from the request is left in the assumptions as
[NEEDS CLARIFICATION: <the question>]. Leave three at most, and do not guess past one.
A design is needed only where the change is cross-cutting, adds a dependency, carries security or migration risk, or
owes a technical decision before coding. Say which, in one sentence."""


def build_brief() -> LlmAgent:
    instruction = "\n".join(
        [
            OPENING,
            "",
            "## The rules of this repository",
            fenced("constitution", placeholder(CONSTITUTION, optional=True)),
            "",
            "## Capabilities",
            "Known capabilities, each with its purpose:",
            placeholder(CAPABILITIES, optional=True),
            "Name each capability the change touches by its kebab-case slug. Reuse a known one where it fits.",
            "",
            "## What to write",
            GUIDE,
            "",
            "## Answers from the person, to use and not to question",
            fenced("answers", placeholder(ANSWERS, optional=True)),
            "",
            RETRY,
            "",
            "## The request",
            fenced("request", placeholder(REQUEST)),
            ENDING,
        ]
    )
    return stage(KEY, "Writes the brief of a change.", instruction, BriefDraft)


def read_brief(state: Mapping[str, Any]) -> BriefDraft | str:
    return read_back(state, KEY, BriefDraft)
