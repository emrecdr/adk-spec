"""The deltas stage: what the change does to each capability's living spec, requirement by requirement."""

from __future__ import annotations

from google.adk.agents import LlmAgent

from ...domain.drafts import DeltasDraft
from . import CURRENT_DELTAS, LIVING_SPECS, THE_BRIEF, THE_LESSONS, instruction, section, stage

KEY = "deltas"
OPENING = "You write the requirement deltas of a change. You write no code."
GUIDE = """\
Write one delta for each capability the brief lists, and for no other.
A requirement is one statement of what the system does, with SHALL or MUST, and one scenario at least.
A scenario is steps in order. Each step starts with GIVEN, WHEN, THEN or AND. It has one WHEN and one THEN at least.
To change a living requirement, give its ID exactly as the spec spells it and restate it whole, with every scenario
that still holds. To remove one, give its ID and one sentence of reason.
A new requirement carries no ID: one is assigned. Never invent one.
Give a purpose only for a capability that has no living spec yet.
Where the deltas as they stand are given, revise them: change only what the brief now asks, keep every other
requirement and scenario word for word, and keep the name of each requirement that stays. A requirement they list
under ADDED is this change's own, not a living one: it stays under added, with no ID, even where the request changes
it; to drop it, leave it out."""


def build_deltas() -> LlmAgent:
    current = section("## The deltas as they stand", "current deltas", CURRENT_DELTAS, optional=True)
    text = instruction(OPENING, GUIDE, THE_LESSONS, LIVING_SPECS, THE_BRIEF, current)
    return stage(KEY, "Writes the requirement deltas of a change.", text, DeltasDraft)
