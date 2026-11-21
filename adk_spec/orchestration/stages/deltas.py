"""The deltas stage: what the change does to each capability's living spec, requirement by requirement."""

from __future__ import annotations

from google.adk.agents import LlmAgent

from ...domain.drafts import DeltasDraft
from . import LIVING_SPECS, THE_BRIEF, instruction, stage

KEY = "deltas"
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
    text = instruction(OPENING, GUIDE, LIVING_SPECS, THE_BRIEF)
    return stage(KEY, "Writes the requirement deltas of a change.", text, DeltasDraft)
