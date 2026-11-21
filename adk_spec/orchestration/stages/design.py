"""The design stage, run only where a change owes one: the decisions to settle before its tasks are written."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from google.adk.agents import LlmAgent

from ...domain.drafts import DesignDraft
from . import FILES, LIVING_SPECS, RULES, THE_BRIEF, THE_DELTAS, instruction, read_back, stage

KEY = "design"
OPENING = "You write the design of a change. You write no code."
GUIDE = """\
Say what stands today that the design must fit. Say what the design must achieve, and what it need not.
Give each decision with the alternatives you weighed and why this one. Say what could go wrong, and what limits it.
Decide only what the requirements leave open. Change no requirement.
Call existing only what the files or the living specs show."""


def build_design() -> LlmAgent:
    text = instruction(OPENING, GUIDE, RULES, LIVING_SPECS, FILES, THE_BRIEF, THE_DELTAS)
    return stage(KEY, "Writes the design of a change.", text, DesignDraft)


def read_design(state: Mapping[str, Any]) -> DesignDraft | str:
    return read_back(state, KEY, DesignDraft)
