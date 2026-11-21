"""The design stage, run only where a change owes one: the decisions to settle before its tasks are written."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from google.adk.agents import LlmAgent

from ...domain.drafts import DesignDraft
from . import ENDING, RETRY, fenced, placeholder, read_back, stage
from .brief import CONSTITUTION
from .deltas import BRIEF_TEXT, LIVING

KEY = "design"
#: The state key the change's deltas are read from, each as its canonical file.
DELTAS_TEXT = "deltas_text"
OPENING = "You write the design of a change. You write no code."
GUIDE = """\
Say what stands today that the design must fit. Say what the design must achieve, and what it need not.
Give each decision with the alternatives you weighed and why this one. Say what could go wrong, and what limits it.
Decide only what the requirements leave open. Change no requirement."""


def build_design() -> LlmAgent:
    instruction = "\n".join(
        [
            OPENING,
            "",
            "## What to write",
            GUIDE,
            "",
            RETRY,
            "",
            "## The rules of this repository",
            fenced("constitution", placeholder(CONSTITUTION, optional=True)),
            "",
            "## The living specs the change touches",
            fenced("living", placeholder(LIVING, optional=True)),
            "",
            "## The brief",
            fenced("brief", placeholder(BRIEF_TEXT)),
            "",
            "## The requirement deltas",
            fenced("deltas", placeholder(DELTAS_TEXT, optional=True)),
            ENDING,
        ]
    )
    return stage(KEY, "Writes the design of a change.", instruction, DesignDraft)


def read_design(state: Mapping[str, Any]) -> DesignDraft | str:
    return read_back(state, KEY, DesignDraft)
