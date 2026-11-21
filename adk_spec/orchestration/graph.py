"""The graphs, built where a command asks for one and never at import.

A command is one short `Workflow` run. A drafting stage is an agent; after each stands a gate, a function node that
converts the draft, checks it with the domain's validator and routes: on, back to its stage, or out. Nothing is
written inside a graph. The command reads the drafts from state when the run has ended well, and writes then.

`NAME` is the app's and the root node's, the package folder's own name, as ADK's loader expects of a root agent.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from google.adk.agents.context import Context
from google.adk.apps.app import App
from google.adk.events import Event
from google.adk.workflow import Workflow

from ..domain.brief_md import markers, parse_brief, render_brief
from ..domain.convert import render_design, to_brief, to_deltas, to_tasks
from ..domain.delta_md import parse_delta, render_delta
from ..domain.drafts import BriefDraft, DeltasDraft, DesignDraft, QuestionsDraft, TasksDraft, Triage
from ..domain.ids import slug_problem
from ..domain.lifecycle import capture_bases
from ..domain.model import Brief, Delta, Finding, GrammarError, Spec, Tier
from ..domain.spec_md import render_spec
from ..domain.tasks_md import parse_tasks, render_tasks
from ..domain.validate import validate_brief, validate_delta, validate_tasks
from ..workspace.context import ContextTooLargeError, joined
from .gate import AGAIN, FAILURE, FINDINGS, GIVE_UP, OK, checked
from .plugins import UsageLedger, roster
from .stages import BOUNDARY
from .stages import brief as brief_stage
from .stages import deltas as deltas_stage
from .stages import design as design_stage
from .stages import questions as questions_stage
from .stages import tasks as tasks_stage
from .stages import triage as triage_stage

NAME = "adk_spec"
#: The state key the tier a run settled on is left under: a tier, or `none` where no spec is owed.
TIER = "tier"
GO, NONE, STOP, SOME = "GO", "NONE", "STOP", "SOME"
#: How many questions one round asks, and how many rounds a run asks in all.
QUESTION_BUDGET = 5
ROUND_BUDGET = 3
#: The state keys of the asking: the rounds answered so far, and the questions a run ended on. The second is
#: written by code alone, so the command pairs each answer with the very question it put to the person.
ROUNDS = "rounds"
ASKING = "asking"
#: The state key the reason is left under where a brief's open points could not be worded as questions.
UNWORDED = "unworded"
#: Where a propose run starts: at the request, at a brief to draft again with a person's answers, or at the deltas
#: of a brief that stands.
Entry = Literal["triage", "brief", "deltas"]


@dataclass(frozen=True)
class Known:
    """What a run is told of the workspace, as plain values: no node reads a file."""

    living: Mapping[str, Spec]
    #: By capability: every requirement ID spoken for, in its spec or in another open change.
    taken: Mapping[str, frozenset[str]]
    ceiling: int | None = None


@dataclass(frozen=True)
class Drafted:
    """A run's drafts as the domain's types: what the gates checked, and what the command writes."""

    draft: BriefDraft
    brief: Brief
    deltas: dict[str, Delta]


def _errors(findings: list[Finding]) -> list[str]:
    """Each ERROR as the validator words it, for a stage to put right."""
    return [f"{found.code}: {found.message}" for found in findings if found.severity == "ERROR"]


def _brief(state: Mapping[str, Any]) -> tuple[BriefDraft, Brief]:
    draft = BriefDraft.model_validate(state[brief_stage.KEY])
    return draft, to_brief(draft)


def drafted(state: Mapping[str, Any], known: Known) -> Drafted:
    """The brief and the deltas a run left in state, converted. The same call gives the same IDs, so what a gate
    checked is what the command writes."""
    draft, brief = _brief(state)
    deltas = DeltasDraft.model_validate(state[deltas_stage.KEY])
    touched = {one.capability.strip() for one in deltas.deltas}
    taken = set().union(*(known.taken.get(capability, frozenset()) for capability in touched))
    return Drafted(draft, brief, to_deltas(deltas, known.living, taken))


def build_smoke_app() -> App:
    """The triage stage alone: what `adk-spec smoke` runs to prove an arm answers in a schema."""
    edges = [("START", triage_stage.build_triage())]
    return App(name=NAME, root_agent=Workflow(name=NAME, edges=edges), plugins=[])


def _checks(known: Known):
    """What the brief's gate and the deltas' gate check, each as what is wrong, a sentence a problem."""

    def check_brief(state: Mapping[str, Any]) -> list[str]:
        _draft, brief = _brief(state)
        if not brief.title:
            return ["the brief has no title. Give it one, on one line."]
        text = render_brief(brief)
        try:
            same = parse_brief(text) == brief
        except GrammarError as exc:
            return [f"the brief cannot be written as its file: {exc.message}. Write no heading and no open code fence."]
        if not same:
            return ["a section of the brief does not read back as written. Write no line that starts `## ` in one."]
        return _errors(validate_brief(brief, text))

    def check_deltas(state: Mapping[str, Any]) -> list[str]:
        made = drafted(state, known)
        listed = set(made.brief.capabilities)
        problems = [
            f"the delta names `{capability}`, which the brief does not list. Change only a capability the brief lists."
            for capability in made.deltas
            if capability not in listed
        ]
        problems += [
            f"the brief lists `{capability}` and no delta changes it. Write its delta."
            for capability in sorted(listed - set(made.deltas))
        ]
        for capability, delta in made.deltas.items():
            problems += _of_delta(capability, delta, known)
        return problems

    return check_brief, check_deltas


def _routing(known: Known, tier: Tier | None):
    """The two nodes that decide and prepare between stages: the tier the run goes on with, and what the deltas
    stage reads."""

    def sized(ctx: Context) -> Event:
        """The person's tier, else the model's, `strict` read as `standard` for now."""
        model = Triage.model_validate(ctx.state[triage_stage.KEY]).tier
        chosen = tier or ("standard" if model == "strict" else model)
        return Event(route=NONE if chosen == "none" else GO, state={TIER: chosen})

    def gathered(ctx: Context) -> Event:
        """The brief as its file, and each living spec it touches, whole."""
        _draft, brief = _brief(ctx.state.to_dict())
        specs = {slug: render_spec(known.living[slug]) for slug in brief.capabilities if slug in known.living}
        try:
            living = joined(specs)
        except ContextTooLargeError as exc:
            return Event(route=STOP, state={FAILURE: f"context: {exc}"})
        return Event(route=GO, state={deltas_stage.BRIEF_TEXT: render_brief(brief), deltas_stage.LIVING: living})

    return sized, gathered


def _asking(ask: bool):
    """The nodes around a standard change's open points: whether to ask, the questions a run ends on, and what
    happens where none could be worded."""

    def open_points(ctx: Context) -> Event:
        """Ask only on the standard tier, only while the brief leaves a point open, and only while the rounds last."""
        _draft, brief = _brief(ctx.state.to_dict())
        text = render_brief(brief)
        rounds = ctx.state.get(ROUNDS) or 0
        if not ask or ctx.state.get(TIER) != "standard" or not markers(text) or rounds >= ROUND_BUDGET:
            return Event(route=NONE)
        return Event(route=SOME, state={deltas_stage.BRIEF_TEXT: text})

    def pending(ctx: Context) -> Event:
        """The run ends here, on the round's questions, the first `QUESTION_BUDGET` of them: the command puts them
        to the person and starts the next run with what was answered."""
        held = QuestionsDraft.model_validate(ctx.state[questions_stage.KEY]).questions[:QUESTION_BUDGET]
        return Event(state={ASKING: [one.model_dump() for one in held]})

    def unasked(ctx: Context) -> Event:
        """No question could be worded: the brief that passed its gate stands, its points left open for a person.
        The questions' findings are cleared, or the deltas stage would be told them as its own."""
        return Event(state={FAILURE: None, FINDINGS: None, UNWORDED: ctx.state.get(FAILURE)})

    return open_points, pending, unasked


def _check_questions(state: Mapping[str, Any]) -> list[str]:
    held = QuestionsDraft.model_validate(state[questions_stage.KEY]).questions
    return [] if held else ["the brief leaves a point open and no question was written. Write one for each marker."]


def _ended() -> Event:
    return Event(output="ended")


def _gate(stage: str, check: Callable[[Mapping[str, Any]], list[str]]):
    """The gate of `stage`, which first refuses an answer that repeats this process's marker: written to a file and
    read by the next stage, it would end a fenced section early there."""

    def clean(state: Mapping[str, Any]) -> list[str]:
        if BOUNDARY in json.dumps(state[stage]):
            return ["the answer repeats a marker line of your instructions. Write no marker line."]
        return check(state)

    return checked(stage, clean)


def build_propose_app(
    known: Known, *, tier: Tier | None, ask: bool, entry: Entry = "triage", ledger: UsageLedger | None = None
) -> App:
    """Triage, the brief and the deltas, each behind its gate. `tier` is a person's own choice, which wins over the
    model's; with none, a request the model sizes as `none` ends the run with nothing drafted.

    With `ask`, a standard change whose brief leaves a point open ends its run on the questions, under `ASKING`. The
    command asks, and starts the next run at `entry`: `brief`, seeded with the answers, to draft the brief again; or
    `deltas`, seeded with a brief that stands, where nobody answered."""
    check_brief, check_deltas = _checks(known)
    sized, gathered = _routing(known, tier)
    deltas, deltas_gate = deltas_stage.build_deltas(), _gate(deltas_stage.KEY, check_deltas)
    edges: list[Any] = [
        (gathered, {GO: deltas, STOP: _ended}),
        (deltas, deltas_gate),
        (deltas_gate, {OK: _ended, AGAIN: deltas, GIVE_UP: _ended}),
    ]
    if entry == "deltas":
        edges = [("START", gathered), *edges]
    else:
        open_points, pending, unasked = _asking(ask)
        brief, brief_gate = brief_stage.build_brief(), _gate(brief_stage.KEY, check_brief)
        questions, questions_gate = questions_stage.build_questions(), _gate(questions_stage.KEY, _check_questions)
        edges = [
            *_opening(sized, brief, entry),
            (brief, brief_gate),
            (brief_gate, {OK: open_points, AGAIN: brief, GIVE_UP: _ended}),
            (open_points, {NONE: gathered, SOME: questions}),
            (questions, questions_gate),
            (questions_gate, {OK: pending, AGAIN: questions, GIVE_UP: unasked}),
            (unasked, gathered),
            *edges,
        ]
    return App(name=NAME, root_agent=Workflow(name=NAME, edges=edges), plugins=roster(known.ceiling, ledger))


def _opening(sized: Any, brief: Any, entry: Entry) -> list[Any]:
    """The edges up to the brief: through triage for a new request, straight to it for a brief drafted again."""
    if entry == "brief":
        return [("START", brief)]
    triage, triage_gate = triage_stage.build_triage(), _gate(triage_stage.KEY, lambda _state: [])
    return [
        ("START", triage, triage_gate),
        (triage_gate, {OK: sized, AGAIN: triage, GIVE_UP: _ended}),
        (sized, {GO: brief, NONE: _ended}),
    ]


def _check_design(state: Mapping[str, Any]) -> list[str]:
    draft = DesignDraft.model_validate(state[design_stage.KEY])
    sections = {"context": draft.context, "goals": draft.goals, "decisions": draft.decisions, "risks": draft.risks}
    return [f"the design's {name} section is empty. Write it." for name, text in sections.items() if not text.strip()]


def _check_tasks(state: Mapping[str, Any]) -> list[str]:
    groups = to_tasks(TasksDraft.model_validate(state[tasks_stage.KEY]))
    if not any(group.tasks for group in groups):
        return ["the plan holds no task. Write one task at least for each requirement the deltas add or change."]
    try:
        same = parse_tasks(render_tasks(groups)) == groups
    except GrammarError as exc:
        return [f"the tasks cannot be written as their file: {exc.message}."]
    if not same:
        return ["the tasks do not read back as written: keep each description, file and check on one line."]
    return _errors(validate_tasks(groups))


def _designed(ctx: Context) -> Event:
    """The design as its file, for the tasks stage to read."""
    draft = DesignDraft.model_validate(ctx.state[design_stage.KEY])
    return Event(state={tasks_stage.DESIGN_TEXT: render_design(draft)})


def build_plan_app(known: Known, *, design: bool) -> App:
    """The design, where the change owes one, and then the tasks, each behind its gate."""
    tasks, tasks_gate = tasks_stage.build_tasks(), _gate(tasks_stage.KEY, _check_tasks)
    edges: list[Any] = [(tasks, tasks_gate), (tasks_gate, {OK: _ended, AGAIN: tasks, GIVE_UP: _ended})]
    if design:
        drafting, design_gate = design_stage.build_design(), _gate(design_stage.KEY, _check_design)
        edges = [
            ("START", drafting, design_gate),
            (design_gate, {OK: _designed, AGAIN: drafting, GIVE_UP: _ended}),
            (_designed, tasks),
            *edges,
        ]
    else:
        edges = [("START", tasks), *edges]
    return App(name=NAME, root_agent=Workflow(name=NAME, edges=edges), plugins=roster(known.ceiling))


def _of_delta(capability: str, delta: Delta, known: Known) -> list[str]:
    """What is wrong with one converted delta: a name no folder holds, an error of the validator's against the
    living spec, or text that does not survive being written as its file. The validator speaks first: it names the
    ID that is wrong, where a failed round trip could only name a shape."""
    if why := slug_problem(capability):
        return [f"the delta names a capability that cannot be one: {why}."]
    bases = capture_bases({capability: delta}, known.living)
    if wrong := _errors(validate_delta(delta, known.living.get(capability), bases)):
        return wrong
    try:
        read = parse_delta(render_delta(delta))
    except GrammarError as exc:
        return [f"the delta of `{capability}` cannot be written as its file: {exc.message}."]
    before, after = (*delta.added, *delta.modified), (*read.added, *read.modified)
    for wrote, back in zip(before, after, strict=False):
        if wrote != back:
            return [
                f"{wrote.id} `{wrote.name}` does not read back as written. Keep its name and each step on one line, "
                "and write no heading and no open code fence in its statement."
            ]
    if read != delta:
        return [f"the delta of `{capability}` does not read back as written: keep each reason on one line."]
    return []
