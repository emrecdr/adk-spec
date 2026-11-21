"""The graphs, built where a command asks for one and never at import.

A command is one short `Workflow` run. A drafting stage is an agent; after each stands a gate, a function node that
converts the draft, checks it with the domain's validator and routes: on, back to its stage, or out. Nothing is
written inside a graph. The command reads the drafts from state when the run has ended well, and writes then.

`NAME` is the app's and the root node's, the package folder's own name, as ADK's loader expects of a root agent.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from google.adk.agents.context import Context
from google.adk.apps.app import App
from google.adk.events import Event
from google.adk.events.request_input import RequestInput
from google.adk.workflow import Workflow

from ..domain.brief_md import markers, render_brief
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
from .gate import AGAIN, FAILURE, GIVE_UP, OK, checked, tries_key
from .plugins import roster
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
#: The state keys of the asking: the rounds so far, and the key of the answers in the payload sent back.
ROUNDS = "rounds"
ANSWERS = "answers"


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
        return _errors(validate_brief(brief, render_brief(brief)))

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
    """The nodes that put a standard change's open points to the person: whether to ask, the pause, and the answers
    kept for the next brief."""

    def open_points(ctx: Context) -> Event:
        """Ask only on the standard tier, only while the brief leaves a point open, and only while the rounds last."""
        _draft, brief = _brief(ctx.state.to_dict())
        text = render_brief(brief)
        rounds = ctx.state.get(ROUNDS) or 0
        if not ask or ctx.state.get(TIER) != "standard" or not markers(text) or rounds >= ROUND_BUDGET:
            return Event(route=NONE)
        return Event(route=SOME, state={deltas_stage.BRIEF_TEXT: text})

    def asked(ctx: Context):
        """One pause for the round's questions, the first `QUESTION_BUDGET` of them."""
        yield RequestInput(
            message="The brief leaves points open.", payload={"questions": [one.model_dump() for one in _asked(ctx)]}
        )

    def answered(ctx: Context, node_input: dict[str, Any]) -> Event:
        """The person's answers kept for the next brief, each beside its question. A round nobody answered ends the
        asking: the points stay open in the brief, and a person settles them later."""
        given = [str(one).strip() for one in (node_input or {}).get(ANSWERS) or []]
        lines = [f"{put.question} -> {reply}" for put, reply in zip(_asked(ctx), given, strict=False) if reply]
        before = ctx.state.get(brief_stage.ANSWERS) or ""
        return Event(
            state={
                brief_stage.ANSWERS: "\n".join([*([before] if before else []), *lines]),
                ROUNDS: (ctx.state.get(ROUNDS) or 0) + 1 if lines else ROUND_BUDGET,
                # A new round: the brief is drafted afresh, and neither stage's earlier tries count against it.
                brief_stage.KEY: None,
                questions_stage.KEY: None,
                tries_key(brief_stage.KEY): 0,
                tries_key(questions_stage.KEY): 0,
            }
        )

    return open_points, asked, answered


def _asked(ctx: Context) -> list[Any]:
    """The questions a round puts: the first `QUESTION_BUDGET` the model worded."""
    return QuestionsDraft.model_validate(ctx.state[questions_stage.KEY]).questions[:QUESTION_BUDGET]


def _check_questions(state: Mapping[str, Any]) -> list[str]:
    held = QuestionsDraft.model_validate(state[questions_stage.KEY]).questions
    return [] if held else ["the brief leaves a point open and no question was written. Write one for each marker."]


def _ended() -> Event:
    return Event(output="ended")


def build_propose_app(known: Known, *, tier: Tier | None, ask: bool) -> App:
    """Triage, the brief and the deltas, each behind its gate. `tier` is a person's own choice, which wins over the
    model's; with none, a request the model sizes as `none` ends the run with nothing drafted. With `ask`, a
    standard change's open points are put to the person, a bounded number of times, before the deltas are drafted."""
    check_brief, check_deltas = _checks(known)
    sized, gathered = _routing(known, tier)
    open_points, asked, answered = _asking(ask)
    triage, brief, deltas = triage_stage.build_triage(), brief_stage.build_brief(), deltas_stage.build_deltas()
    questions = questions_stage.build_questions()
    triage_gate = checked(triage_stage.KEY, lambda _state: [])
    brief_gate = checked(brief_stage.KEY, check_brief)
    questions_gate = checked(questions_stage.KEY, _check_questions)
    deltas_gate = checked(deltas_stage.KEY, check_deltas)
    edges = [
        ("START", triage, triage_gate),
        (triage_gate, {OK: sized, AGAIN: triage, GIVE_UP: _ended}),
        (sized, {GO: brief, NONE: _ended}),
        (brief, brief_gate),
        (brief_gate, {OK: open_points, AGAIN: brief, GIVE_UP: _ended}),
        (open_points, {NONE: gathered, SOME: questions}),
        (questions, questions_gate),
        (questions_gate, {OK: asked, AGAIN: questions, GIVE_UP: _ended}),
        (asked, answered),
        (answered, brief),
        (gathered, {GO: deltas, STOP: _ended}),
        (deltas, deltas_gate),
        (deltas_gate, {OK: _ended, AGAIN: deltas, GIVE_UP: _ended}),
    ]
    return App(name=NAME, root_agent=Workflow(name=NAME, edges=edges), plugins=roster(known.ceiling))


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
    tasks, tasks_gate = tasks_stage.build_tasks(), checked(tasks_stage.KEY, _check_tasks)
    edges: list[Any] = [(tasks, tasks_gate), (tasks_gate, {OK: _ended, AGAIN: tasks, GIVE_UP: _ended})]
    if design:
        drafting, design_gate = design_stage.build_design(), checked(design_stage.KEY, _check_design)
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
    """What is wrong with one converted delta: a name no folder holds, text that does not survive being written as
    its file, or an error of the validator's against the living spec."""
    if why := slug_problem(capability):
        return [f"the delta names a capability that cannot be one: {why}."]
    try:
        same = parse_delta(render_delta(delta)) == delta
    except GrammarError as exc:
        return [f"the delta of `{capability}` cannot be written as its file: {exc.message}."]
    if not same:
        return [f"the delta of `{capability}` does not read back as written: keep each name and each step on one line."]
    bases = capture_bases({capability: delta}, known.living)
    return _errors(validate_delta(delta, known.living.get(capability), bases))
