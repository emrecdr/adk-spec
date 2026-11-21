"""The deltas stage: what the change does to each capability's living spec, requirement by requirement."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from google.adk.agents import LlmAgent

from ...domain.drafts import DeltasDraft
from . import ENDING, RETRY, fenced, placeholder, read_back, stage

KEY = "deltas"
#: The state keys the instruction reads: the brief as its canonical file, and the living specs it touches, whole.
BRIEF_TEXT = "brief_text"
LIVING = "living"
OPENING = "You write the requirement deltas of a change. You write no code."
GUIDE = """\
Write one delta for each capability the brief lists, and for no other.
A requirement is one statement of what the system does, with SHALL or MUST, and one scenario at least.
A scenario is steps in order. Each step starts with GIVEN, WHEN, THEN or AND. It has one WHEN and one THEN at least.
To change a living requirement, give its ID exactly as the spec spells it and restate it whole, with every scenario
that still holds. To remove one, give its ID and one sentence of reason.
A new requirement carries no ID: one is assigned. Never invent one.
Give a purpose only for a capability that has no living spec yet."""


def build_deltas() -> LlmAgent:
    instruction = "\n".join(
        [
            OPENING,
            "",
            "## What to write",
            GUIDE,
            "",
            RETRY,
            "",
            "## The living specs the change touches",
            fenced("living", placeholder(LIVING, optional=True)),
            "",
            "## The brief",
            fenced("brief", placeholder(BRIEF_TEXT)),
            ENDING,
        ]
    )
    return stage(KEY, "Writes the requirement deltas of a change.", instruction, DeltasDraft)


def read_deltas(state: Mapping[str, Any]) -> DeltasDraft | str:
    return read_back(state, KEY, DeltasDraft)
