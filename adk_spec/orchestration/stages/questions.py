"""The questions stage: each point a brief leaves open, worded for a person to answer in a sentence.

Python counts the points and holds the budget. The model only words them, and suggests an answer for each.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from google.adk.agents import LlmAgent

from ...domain.drafts import QuestionsDraft
from . import ENDING, RETRY, fenced, placeholder, read_back, stage
from .deltas import BRIEF_TEXT

KEY = "questions"
OPENING = "You word the open points of a brief as questions a person can answer in a sentence. You settle none of them."
GUIDE = """\
The brief marks each open point as [NEEDS CLARIFICATION: ...]. Write one question for each marker, in the brief's
order, and no other question. Give each the answer you would suggest, in a sentence, so the person can take it or
correct it."""


def build_questions() -> LlmAgent:
    instruction = "\n".join(
        [
            OPENING,
            "",
            "## What to write",
            GUIDE,
            "",
            RETRY,
            "",
            "## The brief",
            fenced("brief", placeholder(BRIEF_TEXT)),
            ENDING,
        ]
    )
    return stage(KEY, "Words a brief's open points as questions.", instruction, QuestionsDraft)


def read_questions(state: Mapping[str, Any]) -> QuestionsDraft | str:
    return read_back(state, KEY, QuestionsDraft)
