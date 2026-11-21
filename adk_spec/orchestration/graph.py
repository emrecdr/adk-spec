"""The graphs, built where a command asks for one and never at import.

A command is one short `Workflow` run, or a few. A drafting stage is an agent; after each stands a gate, a function
node that converts the draft, checks it with the domain's validator and routes: on, back to its stage, or out.
Nothing is written inside a graph. The command reads the drafts from state when the run has ended well, and writes
then.

No run pauses for a person. A `propose` whose brief leaves a point open ends its run on the questions; the command
asks, and `next_run` says where the run after starts and what it is seeded with. The whole of that protocol is
here: the command holds the terminal, and nothing of the state's keys.

`NAME` is the app's and the root node's, the package folder's own name, as ADK's loader expects of a root agent.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from google.adk.agents.context import Context
from google.adk.apps.app import App
from google.adk.events import Event
from google.adk.workflow import Workflow

from ..domain.brief_md import markers, parse_brief, render_brief
from ..domain.check import coverage
from ..domain.convert import DESIGN_SECTIONS, render_design, to_brief, to_deltas, to_tasks
from ..domain.delta_md import parse_delta, render_delta
from ..domain.drafts import BriefDraft, DeltasDraft, DesignDraft, QuestionsDraft, TasksDraft, Triage
from ..domain.ids import slug_problem
from ..domain.lifecycle import capture_bases
from ..domain.model import Brief, Delta, Finding, GrammarError, Spec, Tier
from ..domain.tasks_md import parse_tasks, render_tasks
from ..domain.validate import validate_brief, validate_delta, validate_tasks
from ..workspace.context import ContextTooLargeError, living_text
from .gate import AGAIN, FAILURE, GIVE_UP, OK, checked
from .plugins import UsageLedger, roster
from .stages import BRIEF_TEXT, LIVING
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
#: How many questions one round asks, and how many rounds a command asks in all.
QUESTION_BUDGET = 5
ROUND_BUDGET = 3
#: The state keys of the asking: the rounds answered so far, and the questions a run ended on. The second is
#: written by code alone, so each answer is kept beside the very question that was put to the person.
ROUNDS = "rounds"
ASKING = "asking"
#: The state key the reason is left under where a brief's open points could not be worded as questions.
UNWORDED = "unworded"
#: Where a propose run starts: at the request, at a brief to draft with a person's answers or tier, or at the
#: deltas of a brief that stands.
Entry = Literal["triage", "brief", "deltas"]


@dataclass(frozen=True)
class Known:
    """What a run is told of the workspace, as plain values: no node reads a file."""

    living: Mapping[str, Spec]
    #: Every requirement ID spoken for, in a living spec or in an open change.
    taken: frozenset[str]


@dataclass(frozen=True)
class Drafted:
    """A run's drafts as the domain's types: what the gates checked, and what the command writes."""

    brief: Brief
    deltas: dict[str, Delta]
    needs_design: bool


def _errors(findings: list[Finding]) -> list[str]:
    """Each ERROR as the validator words it, for a stage to put right."""
    return [f"{found.code}: {found.message}" for found in findings if found.severity == "ERROR"]


def _brief(state: Mapping[str, Any]) -> Brief:
    return to_brief(BriefDraft.model_validate(state[brief_stage.KEY]))


def drafted(state: Mapping[str, Any], known: Known) -> Drafted:
    """The brief and the deltas a run left in state, converted. The same call gives the same IDs, so what a gate
    checked is what the command writes."""
    draft = BriefDraft.model_validate(state[brief_stage.KEY])
    deltas = to_deltas(DeltasDraft.model_validate(state[deltas_stage.KEY]), known.living, known.taken)
    return Drafted(to_brief(draft), deltas, draft.design_needed)


def first_run(tier: Tier | None, seed: Mapping[str, Any]) -> tuple[Entry, dict[str, Any]]:
    """Where a propose starts, and what its run is seeded with: at triage, or straight at the brief where a person
    named the tier. Triage is asked for the tier alone; with the tier given, nothing would read its answer."""
    return ("brief", {**seed, TIER: tier}) if tier else ("triage", dict(seed))


def next_run(seed: Mapping[str, Any], state: Mapping[str, Any], answers: Sequence[str]) -> tuple[Entry, dict[str, Any]]:
    """Where the run after a round of questions starts, and what it is seeded with. `seed` is what the run that
    asked was seeded with, `state` what it left, and `answers` the person's, in the order of the questions under
    `ASKING`, an empty one for a point left open.

    What was answered starts the next run at the brief, each answer beside the question the person was shown, after
    those of the rounds before. A round nobody answered starts it at the deltas, with the brief that passed its
    gate, its points left open."""
    carried = {**seed, TIER: state[TIER]}
    if not any(answers):
        return "deltas", {**carried, brief_stage.KEY: state[brief_stage.KEY]}
    told = [seed[brief_stage.ANSWERS]] if seed.get(brief_stage.ANSWERS) else []
    told += [
        f"{' '.join(asked['question'].split())} -> {answer}"
        for asked, answer in zip(state[ASKING], answers, strict=True)
        if answer
    ]
    return "brief", {**carried, brief_stage.ANSWERS: "\n".join(told), ROUNDS: (seed.get(ROUNDS) or 0) + 1}


def build_smoke_app() -> App:
    """The triage stage alone: what `adk-spec smoke` runs to prove an arm answers in a schema."""
    edges = [("START", triage_stage.build_triage())]
    return App(name=NAME, root_agent=Workflow(name=NAME, edges=edges), plugins=[])


# What each gate checks: what is wrong with the stage's answer, a sentence a problem.


def _check_brief(state: Mapping[str, Any]) -> list[str]:
    brief = _brief(state)
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


def _check_questions(state: Mapping[str, Any]) -> list[str]:
    held = QuestionsDraft.model_validate(state[questions_stage.KEY]).questions
    return [] if held else ["the brief leaves a point open and no question was written. Write one for each marker."]


def _deltas_check(known: Known) -> Callable[[Mapping[str, Any]], list[str]]:
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

    return check_deltas


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


def _check_design(state: Mapping[str, Any]) -> list[str]:
    draft = DesignDraft.model_validate(state[design_stage.KEY])
    return [
        f"the design's {name} section is empty. Write it."
        for name in DESIGN_SECTIONS
        if not getattr(draft, name).strip()
    ]


def _tasks_check(owed: frozenset[str], nameable: frozenset[str]) -> Callable[[Mapping[str, Any]], list[str]]:
    """What the tasks' gate checks, for a change that owes a task to each of `owed` and may name any of `nameable`.
    The validator and the coverage speak before the round trip: they name the ID or the task that is wrong."""

    def check_tasks(state: Mapping[str, Any]) -> list[str]:
        groups = to_tasks(TasksDraft.model_validate(state[tasks_stage.KEY]))
        if not any(group.tasks for group in groups):
            return ["the plan holds no task. Write one task at least for each requirement the deltas add or change."]
        if wrong := _errors([*validate_tasks(groups), *coverage(groups, owed=owed, nameable=nameable)]):
            return wrong
        try:
            same = parse_tasks(render_tasks(groups)) == groups
        except GrammarError as exc:
            return [f"the tasks cannot be written as their file: {exc.message}."]
        return [] if same else ["the tasks do not read back as written: keep each description and check on one line."]

    return check_tasks


# The nodes between the stages. One that reads what the command knows is made for it; the rest read state alone.


def _ended() -> Event:
    return Event(output="ended")


def _sized(ctx: Context) -> Event:
    """The model's tier, `strict` read as `standard` for now. `none` ends the run with nothing drafted."""
    model = Triage.model_validate(ctx.state[triage_stage.KEY]).tier
    chosen = "standard" if model == "strict" else model
    return Event(route=NONE if chosen == "none" else GO, state={TIER: chosen})


def _open_points(ask: bool) -> Callable[[Context], Event]:
    def open_points(ctx: Context) -> Event:
        """Ask only where the command may, only on the standard tier, only while the rounds last, and only while
        the brief leaves a point open."""
        text = render_brief(_brief(ctx.state.to_dict()))
        asking = ask and ctx.state.get(TIER) == "standard" and (ctx.state.get(ROUNDS) or 0) < ROUND_BUDGET
        return Event(route=SOME, state={BRIEF_TEXT: text}) if asking and markers(text) else Event(route=NONE)

    return open_points


def _pending(ctx: Context) -> Event:
    """The run ends here, on the round's questions, the first `QUESTION_BUDGET` of them: the command puts them to
    the person, and `next_run` starts the run after with what was answered."""
    held = QuestionsDraft.model_validate(ctx.state[questions_stage.KEY]).questions[:QUESTION_BUDGET]
    return Event(state={ASKING: [one.model_dump() for one in held]})


def _unasked(ctx: Context) -> Event:
    """No question could be worded: the brief that passed its gate stands, its points left open for a person, and
    the gate's failure becomes a note."""
    return Event(state={FAILURE: None, UNWORDED: ctx.state.get(FAILURE)})


def _gathering(known: Known) -> Callable[[Context], Event]:
    def gathered(ctx: Context) -> Event:
        """What the deltas stage reads: the brief as its file, and each living spec it touches, whole."""
        brief = _brief(ctx.state.to_dict())
        try:
            living = living_text(known.living, brief.capabilities)
        except ContextTooLargeError as exc:
            return Event(route=STOP, state={FAILURE: f"context: {exc}"})
        return Event(route=GO, state={BRIEF_TEXT: render_brief(brief), LIVING: living})

    return gathered


def _designed(ctx: Context) -> Event:
    """The design as its file, for the tasks stage to read."""
    draft = DesignDraft.model_validate(ctx.state[design_stage.KEY])
    return Event(state={tasks_stage.DESIGN_TEXT: render_design(draft)})


def build_propose_app(known: Known, *, ask: bool, entry: Entry, ledger: UsageLedger) -> App:
    """Triage, the brief and the deltas, each behind its gate, from `entry` on. A request the model sizes as `none`
    ends the run with nothing drafted.

    With `ask`, a standard change whose brief leaves a point open ends its run on the questions, under `ASKING`.
    `first_run` and `next_run` say which entry a run takes and what it is seeded with."""
    gathered = _gathering(known)
    deltas, deltas_gate = deltas_stage.build_deltas(), checked(deltas_stage.KEY, _deltas_check(known))
    edges: list[Any] = [
        (gathered, {GO: deltas, STOP: _ended}),
        (deltas, deltas_gate),
        (deltas_gate, {OK: _ended, AGAIN: deltas, GIVE_UP: _ended}),
    ]
    if entry == "deltas":
        edges = [("START", gathered), *edges]
    else:
        open_points = _open_points(ask)
        brief, brief_gate = brief_stage.build_brief(), checked(brief_stage.KEY, _check_brief)
        questions, questions_gate = questions_stage.build_questions(), checked(questions_stage.KEY, _check_questions)
        edges = [
            *_opening(brief, entry),
            (brief, brief_gate),
            (brief_gate, {OK: open_points, AGAIN: brief, GIVE_UP: _ended}),
            (open_points, {NONE: gathered, SOME: questions}),
            (questions, questions_gate),
            (questions_gate, {OK: _pending, AGAIN: questions, GIVE_UP: _unasked}),
            (_unasked, gathered),
            *edges,
        ]
    return App(name=NAME, root_agent=Workflow(name=NAME, edges=edges), plugins=roster(ledger))


def _opening(brief: Any, entry: Entry) -> list[Any]:
    """The edges up to the brief: through triage for a request to size, straight to it otherwise."""
    if entry == "brief":
        return [("START", brief)]
    triage, triage_gate = triage_stage.build_triage(), checked(triage_stage.KEY, lambda _state: [])
    return [
        ("START", triage, triage_gate),
        (triage_gate, {OK: _sized, AGAIN: triage, GIVE_UP: _ended}),
        (_sized, {GO: brief, NONE: _ended}),
    ]


def build_plan_app(*, design: bool, ledger: UsageLedger, owed: frozenset[str], nameable: frozenset[str]) -> App:
    """The design, where the change owes one, and then the tasks, each behind its gate. The tasks are held to the
    change's own requirements: each of `owed` served, and none named outside `nameable`."""
    tasks, tasks_gate = tasks_stage.build_tasks(), checked(tasks_stage.KEY, _tasks_check(owed, nameable))
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
    return App(name=NAME, root_agent=Workflow(name=NAME, edges=edges), plugins=roster(ledger))
