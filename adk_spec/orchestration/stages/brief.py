"""The brief stage: why the change is wanted, what changes, what does not, and which capabilities it touches."""

from __future__ import annotations

from google.adk.agents import LlmAgent

from ...domain.drafts import BriefDraft
from . import CAPABILITIES, ENDING, REQUEST, RETRY, RULES, TIER, fenced, placeholder, stage

KEY = "brief"
#: The state keys a new draft reads beside the request: a person's answers, each beside the question that was put,
#: and the brief it replaces, as its file.
ANSWERS = "answers"
REPLACES = "replaces"
OPENING = "You write the brief of a change for a spec-driven workflow. You write no spec and no code."
GUIDE = (
    """\
Say why the change is wanted, what will be different once it is done, what it leaves alone, and what else it affects.
State what you assume. A point you cannot settle from the request is left in the assumptions as
[NEEDS CLARIFICATION: <the question>]. Leave three at most, and do not guess past one.
A design is needed only where the change is cross-cutting, adds a dependency, carries security or migration risk, or
owes a technical decision before coding. Say which, in one sentence.
Leave every point you cannot settle at once: a later draft is for what an answer opened, not for a point you could
have raised before.
Where a brief to replace is given, keep what it says, settle each point an answer settles, and contradict no answer.
On the lean tier no question is asked: leave no marker there, and state what you assume in its place.
"""
    + f"This change's tier is {placeholder(TIER)}."
)


def build_brief() -> LlmAgent:
    instruction = "\n".join(
        [
            OPENING,
            "",
            RULES,
            "",
            "## Capabilities",
            "Known capabilities, each with its purpose:",
            fenced("capabilities", placeholder(CAPABILITIES, optional=True)),
            "Name each capability the change touches by its kebab-case slug. Reuse a known one where it fits.",
            "",
            "## What to write",
            GUIDE,
            "",
            "## Answers from the person, to use and not to question",
            fenced("answers", placeholder(ANSWERS, optional=True)),
            "",
            "## The brief you are replacing",
            fenced("replaces", placeholder(REPLACES, optional=True)),
            "",
            RETRY,
            "",
            "## The request",
            fenced("request", placeholder(REQUEST)),
            ENDING,
        ]
    )
    return stage(KEY, "Writes the brief of a change.", instruction, BriefDraft)
