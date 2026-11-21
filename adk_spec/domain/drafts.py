"""What a model answers in: the schemas a stage's agent is bound to.

Written for the strictest arm. Each is a plain `BaseModel`: Gemini's `response_schema` refuses the
`additionalProperties` that `extra="forbid"` adds. Every field is required and described, since the Copilot arm's
strict mode lists every property as required and both arms read the descriptions.

No field is nullable. ADK stores a stage's answer with every `None` dropped, so a required field that held `None`
is missing when the answer is read back from state. An empty string or an empty list means "none".
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Triage(BaseModel):
    """How much ceremony a change request needs, and which capabilities it touches."""

    tier: Literal["none", "lean", "standard", "strict"] = Field(description="The smallest tier that fits the request.")
    capabilities: list[str] = Field(description="Kebab-case capability slugs the request touches. Empty for tier none.")
    reason: str = Field(description="One sentence: why this tier.")


class ScenarioDraft(BaseModel):
    """One scenario of a requirement."""

    name: str = Field(description="A short name for the scenario.")
    steps: list[str] = Field(
        description="The steps in order. Each starts with GIVEN, WHEN, THEN or AND. One WHEN and one THEN at least."
    )


class RequirementDraft(BaseModel):
    """One requirement, whole."""

    name: str = Field(description="A short name for the requirement, on one line.")
    statement: str = Field(description="What the system does, in one or two sentences, with SHALL or MUST.")
    scenarios: list[ScenarioDraft] = Field(description="The scenarios that show it. One at least.")


class ModifiedDraft(BaseModel):
    """A living requirement restated whole, as it reads after the change."""

    id: str = Field(description="The ID of the living requirement this replaces, exactly as the spec spells it.")
    requirement: RequirementDraft = Field(description="The requirement after the change, whole.")


class RemovedDraft(BaseModel):
    """A living requirement the change removes."""

    id: str = Field(description="The ID of the living requirement to remove, exactly as the spec spells it.")
    reason: str = Field(description="One sentence: why it goes.")


class DeltaDraft(BaseModel):
    """What the change does to one capability's spec."""

    capability: str = Field(description="The capability's kebab-case slug.")
    purpose: str = Field(
        description="One sentence on what the capability is for, only where the change creates it. Empty otherwise."
    )
    added: list[RequirementDraft] = Field(description="New requirements. Give no ID: one is assigned.")
    modified: list[ModifiedDraft] = Field(description="Living requirements restated whole. Empty where none changes.")
    removed: list[RemovedDraft] = Field(description="Living requirements removed. Empty where none goes.")


class DeltasDraft(BaseModel):
    """The requirement deltas of a change, one a capability."""

    deltas: list[DeltaDraft] = Field(description="One entry for each capability the change touches.")


class BriefDraft(BaseModel):
    """The brief of a change."""

    title: str = Field(description="A short title for the change, on one line.")
    why: str = Field(description="Why the change is wanted.")
    what_changes: str = Field(description="What will be different once it is done.")
    non_goals: str = Field(description="What the change leaves alone. Empty where nothing needs saying.")
    capabilities: list[str] = Field(description="Kebab-case slugs of the capabilities the change touches.")
    impact: str = Field(description="What else is affected: code, people, data.")
    assumptions: str = Field(
        description="What is assumed. A point that cannot be settled is marked [NEEDS CLARIFICATION: question]."
    )
    design_needed: bool = Field(
        description=(
            "True only for a cross-cutting change, a new dependency, security or migration risk, or a technical "
            "decision owed before coding."
        )
    )
    design_reason: str = Field(description="One sentence: why a design is needed, or why not.")


class Question(BaseModel):
    """One open point of a brief, worded for a person to answer."""

    marker: str = Field(description="The marker from the brief this asks about, exactly as written there.")
    question: str = Field(description="One question a person can answer in a sentence.")
    recommended: str = Field(description="The answer you would give, in a sentence.")


class QuestionsDraft(BaseModel):
    """The open points of a brief, as questions."""

    questions: list[Question] = Field(description="One question for each marker in the brief, in the brief's order.")


class TaskDraft(BaseModel):
    """One task."""

    description: str = Field(description="What to do, on one line, starting with a verb.")
    requirements: list[str] = Field(
        description="The IDs of the requirements this serves, exactly as the deltas spell them. Empty for a setup task."
    )
    files: list[str] = Field(description="The files it creates or changes, as paths from the repository's root.")
    verify: str = Field(description="How its result is checked: a command, or what to look at.")
    parallel: bool = Field(
        description="True only where it touches other files than its neighbours and waits on none of them."
    )


class TaskGroupDraft(BaseModel):
    """Tasks that deliver one thing together."""

    title: str = Field(description="What the group delivers, with its number: `1. Passkey sign-in`.")
    tasks: list[TaskDraft] = Field(description="The group's tasks, a test before the code it tests.")


class TasksDraft(BaseModel):
    """The tasks of a change."""

    groups: list[TaskGroupDraft] = Field(description="The groups, in the order to do them.")


class DesignDraft(BaseModel):
    """The design of a change."""

    context: str = Field(description="What stands today that the design must fit.")
    goals: str = Field(description="What the design must achieve, and what it need not.")
    decisions: str = Field(description="Each decision with the alternatives weighed and why this one.")
    risks: str = Field(description="What could go wrong, and what limits it.")
