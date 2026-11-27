"""What a model answers in: the schemas a stage's agent is bound to.

Written for the strictest arm. Each is a plain `BaseModel`: Gemini's `response_schema` refuses the
`additionalProperties` that `extra="forbid"` adds. Every field is required and described, since the Copilot arm's
strict mode lists every property as required and both arms read the descriptions.

No field is nullable. ADK stores a stage's answer with every `None` dropped, so a required field that held `None`
is missing when the answer is read back from state. An empty string or an empty list means "none".
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from .model import StatementKind


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


class OpenPointDraft(BaseModel):
    """One point a brief cannot settle from the request, as a question for the person who made it."""

    question: str = Field(description="The open point as one question a person can answer in a sentence.")
    suggested: str = Field(description="The answer you would suggest, in a sentence. Empty where you have none.")
    depends_on: list[int] = Field(
        description=(
            "The numbers, counting from 1 in this list, of the other open points whose answers this one waits on. "
            "Empty where it waits on none."
        )
    )

    @model_validator(mode="before")
    @classmethod
    def _waits_on_none_where_unsaid(cls, data: Any) -> Any:
        """An answer that names no wait, an arm's that left the field out or one drafted before points named what
        they wait on, waits on none. The field stays required in the schema: Copilot's strict schemas require every
        property."""
        if isinstance(data, dict) and "depends_on" not in data:
            return {**data, "depends_on": []}
        return data


class BriefDraft(BaseModel):
    """The brief of a change."""

    title: str = Field(description="A short title for the change, on one line.")
    why: str = Field(description="Why the change is wanted.")
    what_changes: str = Field(description="What will be different once it is done.")
    non_goals: str = Field(description="What the change leaves alone. Empty where nothing needs saying.")
    capabilities: list[str] = Field(description="Kebab-case slugs of the capabilities the change touches.")
    impact: str = Field(description="What else is affected: code, people, data.")
    assumptions: str = Field(description="What is assumed. A point that cannot be settled goes in open_points.")
    open_points: list[OpenPointDraft] = Field(
        description="Each point that cannot be settled from the request. Three at most. Empty where all is settled."
    )
    design_needed: bool = Field(
        description=(
            "True only for a cross-cutting change, a new dependency, security or migration risk, or a technical "
            "decision owed before coding."
        )
    )
    design_reason: str = Field(description="One sentence: why a design is needed, or why not.")


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


class FindingDraft(BaseModel):
    """One thing a review of a change's files found, with the text it points to."""

    kind: Literal["contradiction", "ambiguity", "gap", "duplication", "constitution"] = Field(
        description=(
            "contradiction: two files say opposite things. ambiguity: wording that allows two readings. gap: "
            "something promised that no requirement delivers. duplication: one requirement stated twice. "
            "constitution: a rule of the repository the change breaks."
        )
    )
    severity: Literal["critical", "warning", "note"] = Field(
        description="critical: the change would be built wrong as it stands. warning: worth a look. note: a remark."
    )
    file: str = Field(description="The path of the file the quote is from, exactly as given above that file.")
    quote: str = Field(description="The exact text the finding points to, copied from that file: a line or a phrase.")
    message: str = Field(description="One sentence: what is wrong, and what to change.")


class FindingsDraft(BaseModel):
    """What a review of a change's files found. An empty list where it found nothing."""

    findings: list[FindingDraft] = Field(description="Each finding. Empty where the files agree.")


class EvidenceDraft(BaseModel):
    """One line of a diff that shows a requirement met, or gone."""

    path: str = Field(description="The file's path, exactly as the diff gives it.")
    quote: str = Field(description="The line, copied word for word, without its + or - sign.")


class VerdictDraft(BaseModel):
    """Whether a diff meets one requirement."""

    id: str = Field(description="The requirement's ID, exactly as it is listed.")
    verdict: Literal["met", "unmet", "unclear"] = Field(
        description=(
            "met: the diff shows the requirement done, every scenario of it. unmet: the diff shows it not done, or "
            "done wrong. unclear: the diff does not let you tell."
        )
    )
    evidence: list[EvidenceDraft] = Field(description="The lines of the diff that show it. Empty where none does.")
    reason: str = Field(description="One or two sentences: why this verdict, and for unmet or unclear what is missing.")


class VerdictsDraft(BaseModel):
    """One verdict for each requirement to judge."""

    verdicts: list[VerdictDraft] = Field(description="One verdict for each requirement listed, and for no other.")


class ScoutDraft(BaseModel):
    """What a scout asks to see of a repository, before a plan is drafted from it."""

    files: list[str] = Field(
        description=(
            "Paths of files to read, each as the list of the repository's files spells it. A range of lines may "
            "follow one, src/app.py:120-260, or a definition's name, src/app.py::Reader.read. Twelve at most. Empty "
            "where the list shows folders and no file."
        )
    )
    folders: list[str] = Field(
        description="Folders whose files to list, where the list shows a folder and not what is in it. Four at most."
    )
    searches: list[str] = Field(
        description="Words or phrases to search the repository for, each as it would stand in the code. Six at most."
    )
    reason: str = Field(description="One sentence: what you expect to find there.")


class StatementDraft(BaseModel):
    """One thing the code shows that matters for the change, with the text it rests on."""

    kind: StatementKind = Field(
        description=(
            "exists: behaviour or code already there that the change builds on, or must not write a second time. "
            "touches: where the change plugs in, code that would be called, extended or changed. convention: how "
            "this repository does a thing that new code should follow. risk: what the code leaves unclear, or what "
            "the change could break."
        )
    )
    file: str = Field(description="The path of the file the statement is about, as written above its text.")
    quote: str = Field(description="Text copied from that file word for word: the line or the phrase that shows it.")
    note: str = Field(description="What it means for the change, in one or two sentences.")


class SurveyDraft(BaseModel):
    """What a reading of the code found for a change, and what is still worth a look."""

    statements: list[StatementDraft] = Field(
        description="Each thing the text above shows that matters for the change. Empty where it shows none."
    )
    more_files: list[str] = Field(
        description=(
            "Files still worth reading, each by its path, with a range of lines, src/app.py:260-400, or with a "
            "definition's name, src/app.py::Reader.read. A file that was cut is read on from where it stopped when "
            "you name it again. Empty where enough was read."
        )
    )
    more_folders: list[str] = Field(description="Folders still worth listing. Empty where none is.")
    more_searches: list[str] = Field(description="Words still worth searching for. Empty where none is.")


class DisputeDraft(BaseModel):
    statement: int = Field(description="The number of a statement above.")
    reason: str = Field(description="Why its quote, or the block it stands in, does not show what its note says.")


class UnknownDraft(BaseModel):
    question: str = Field(description="What the change needs to know that no statement establishes, on one line.")
    where: str = Field(description="Where it might be answered: a file, a folder, a word, a person. Empty if unsure.")


class ReviewDraft(BaseModel):
    """A review of what a reading of the code kept: statements its code does not bear out, what is still unknown, and
    what to read to know it."""

    disputed: list[DisputeDraft] = Field(description="Each statement its quote does not bear out. Empty where none.")
    unknown: list[UnknownDraft] = Field(description="What is still unknown that matters. Empty where nothing is.")
    more_files: list[str] = Field(
        description=(
            "Files to read to answer an unknown, by path, with a range of lines, or with a definition's name: "
            "src/app.py::Reader.read. Empty where none would."
        )
    )
    more_folders: list[str] = Field(description="Folders to list to answer an unknown. Empty where none would.")
    more_searches: list[str] = Field(description="Words to search for to answer an unknown. Empty where none would.")
