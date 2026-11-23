"""The brief stage: why the change is wanted, what changes, what does not, and which capabilities it touches."""

from __future__ import annotations

from google.adk.agents import LlmAgent

from ...domain.drafts import BriefDraft
from . import (
    CAPABILITIES,
    ENDING,
    REQUEST,
    RETRY,
    RULES,
    SIZED,
    THE_CONTEXT,
    THE_LESSONS,
    THE_PROFILE,
    TIER,
    fenced,
    placeholder,
    stage,
)

KEY = "brief"
#: The state keys a new draft reads beside the request: a person's answers, each beside the question that was put,
#: and the brief it replaces, as its file.
ANSWERS = "answers"
REPLACES = "replaces"
OPENING = "You write the brief of a change for a spec-driven workflow. You write no spec and no code."
GUIDE = (
    """\
Say why the change is wanted, what will be different once it is done, what it leaves alone, and what else it affects.
State what you assume. A point you cannot settle from the request goes in open_points: the question, worded so a
person can answer it in a sentence, and the answer you would suggest. Three at most, and do not guess past one.
State nothing the request, an answer or what the repository holds does not say.
Keep an answer's numbers, order and negatives exactly as the person gave them.
Settle each fact from what the repository already holds and what is known of it, where they are given: never ask the
person what they show. Of what they list as still unknown, put in open_points only what the person can decide or
knows, and state the rest as unknown.
Write no [NEEDS CLARIFICATION] marker yourself.
A design is needed only where the change is cross-cutting, adds a dependency, carries security or migration risk, or
owes a technical decision before coding. Say which, in one sentence.
Name every point you cannot settle at once: a later draft is for what an answer opened, not for a point you could
have raised before. Where a point's question only makes sense once another is answered, give that point's number in
depends_on: it is asked in a later round. Word each question so that "yes" accepts your suggested answer.
Where a brief to replace is given, keep what it says, settle each point an answer settles, and contradict no answer.
Where the request asks to change that brief, change only what it asks, and keep every other line as it is.
A [NEEDS CLARIFICATION: ...] line in it is a point that draft left open: do not copy it. Settle it from an answer, or
name it again in open_points.
On the lean tier no question is asked: leave open_points empty there, and state what you assume.
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
            "The capabilities the request was sized as touching, where it was sized:",
            fenced("sized", placeholder(SIZED, optional=True)),
            "Name as few capabilities as hold the change: start from those it was sized as touching, and add one only",
            "for behaviour none of them holds. Each capability you name gets one requirement at least.",
            "",
            "## What to write",
            GUIDE,
            "",
            THE_LESSONS,
            "",
            THE_PROFILE,
            "",
            THE_CONTEXT,
            "",
            "## Answers from the person, to use and not to question",
            fenced("answers", placeholder(ANSWERS, optional=True)),
            "",
            "## The brief you are replacing",
            fenced("replaces", placeholder(REPLACES, optional=True)),
            "",
            "## The request",
            fenced("request", placeholder(REQUEST)),
            "",
            RETRY,
            ENDING,
        ]
    )
    return stage(KEY, "Writes the brief of a change.", instruction, BriefDraft)
