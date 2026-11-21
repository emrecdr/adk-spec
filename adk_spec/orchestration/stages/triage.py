"""Triage, the first model stage: how much ceremony a change request needs, and which capabilities it touches."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from google.adk.agents import LlmAgent

from ...domain.drafts import Triage
from . import BOUNDARY, CAPABILITIES, ENDING, REQUEST, RETRY, fenced, placeholder, read_back, stage

#: The agent's name, its role for `SPEC_TRIAGE_MODEL`, and the state key its answer is written under.
KEY = "triage"
OPENING = (
    "You size a change request for a spec-driven workflow. You decide how much ceremony it needs and which "
    "capabilities it touches. You write no spec and no code."
)
#: When each tier fits. The owner's to word: these lines decide how much ceremony every change gets. No brace may
#: stand in them, since ADK reads `{name}` in an instruction as a state key.
TIER_GUIDE = """\
none: a typo, a cosmetic change or a throwaway prototype. No spec is owed.
lean: one small, well-understood change or bug fix inside one capability.
standard: a feature that touches one or a few capabilities, or any request whose intent is ambiguous.
strict: many capabilities, high regression risk, or a change that owes an audit trail."""

__all__ = ["BOUNDARY", "CAPABILITIES", "KEY", "REQUEST", "TIER_GUIDE", "build_triage", "placeholder", "read_triage"]


def build_triage() -> LlmAgent:
    """The triage agent, built for the arm the environment names."""
    instruction = "\n".join(
        [
            OPENING,
            "",
            "## Tiers",
            TIER_GUIDE,
            "Choose the smallest tier that fits. Where two fit, choose the larger only for ambiguous intent or high "
            "regression risk.",
            "",
            "## Capabilities",
            "A capability is a kebab-case name for one area of behaviour, such as `auth` or `billing-export`. Reuse a "
            "known capability where one fits. Name a new one only where none does. "
            f"Known capabilities: {placeholder(CAPABILITIES, optional=True)}",
            "",
            RETRY,
            "",
            "## The request",
            fenced("request", placeholder(REQUEST)),
            ENDING,
        ]
    )
    return stage(KEY, "Sizes a change request.", instruction, Triage)


def read_triage(state: Mapping[str, Any]) -> Triage | str:
    return read_back(state, KEY, Triage)
