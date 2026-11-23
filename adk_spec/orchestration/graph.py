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
from dataclasses import dataclass, field
from typing import Any, Literal

from google.adk.agents.context import Context
from google.adk.apps.app import App
from google.adk.events import Event
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.workflow import Workflow
from google.genai import types

from ..domain.brief_md import MARKER_BUDGET, markers, parse_brief, render_brief
from ..domain.check import coverage
from ..domain.convert import DESIGN_SECTIONS, questions_of, render_design, to_brief, to_deltas, to_tasks
from ..domain.delta_md import parse_delta, render_delta
from ..domain.drafts import BriefDraft, DeltasDraft, DesignDraft, TasksDraft, Triage, VerdictsDraft
from ..domain.ids import slug_problem
from ..domain.lessons_md import coded
from ..domain.lifecycle import DEMANDS, capture_bases
from ..domain.model import Brief, Delta, Finding, GrammarError, Spec, Tier
from ..domain.tasks_md import parse_tasks, render_tasks
from ..domain.validate import validate_brief, validate_delta, validate_tasks
from ..workspace.context import ContextTooLargeError, living_text
from ..workspace.layout import BRIEF as BRIEF_FILE
from ..workspace.layout import SPEC_FILE, SPECS
from .gate import AGAIN, FAILURE, GIVE_UP, OK, PENDING, SENT_BACK, checked, tries_key
from .plugins import STAGE_ERROR, Scrub, UsageLedger, roster
from .stages import BRIEF_TEXT, FINDINGS, LIVING, REQUEST, SIZED, TIER
from .stages import brief as brief_stage
from .stages import check as check_stage
from .stages import deltas as deltas_stage
from .stages import design as design_stage
from .stages import tasks as tasks_stage
from .stages import triage as triage_stage
from .stages import verify as verify_stage

NAME = "adk_spec"
GO, NONE, STOP, SOME = "GO", "NONE", "STOP", "SOME"
#: How many rounds of questions a command asks in all. A round asks one question a marker, and a brief that passed
#: its gate holds `MARKER_BUDGET` of them at most.
ROUND_BUDGET = 3
#: The state keys of the asking: the rounds answered so far, and the questions a run ended on. The second is
#: written by code alone, read from the brief that passed its gate, so each answer is kept beside the very question
#: that was put to the person.
ROUNDS = "rounds"
ASKING = "asking"
#: Where a propose run starts: at the request, at a brief to draft with a person's answers or tier, or at the
#: deltas of a brief that stands.
Entry = Literal["triage", "brief", "deltas"]


@dataclass(frozen=True)
class Known:
    """What a run is told of the workspace, as plain values: no node of this module reads a file. The one app that
    reads during its run is the reading of a repository's code, `explore.py`, through a reader it is handed."""

    living: Mapping[str, Spec]
    #: Every requirement ID spoken for, in a living spec or in an open change.
    taken: frozenset[str]
    #: The IDs a change being revised has given, by capability and requirement name: kept where a name stays.
    kept: Mapping[tuple[str, str], Sequence[str]] = field(default_factory=dict)


@dataclass(frozen=True)
class Drafted:
    """A run's drafts as the domain's types: what the gates checked, and what the command writes."""

    brief: Brief
    deltas: dict[str, Delta]
    needs_design: bool


def _errors(findings: list[Finding]) -> list[str]:
    """Each ERROR as the validator words it, for a stage to put right."""
    return [coded(found.code, found.message) for found in findings if found.severity == "ERROR"]


def _brief(state: Mapping[str, Any]) -> Brief:
    return to_brief(BriefDraft.model_validate(state[brief_stage.KEY]))


def drafted(state: Mapping[str, Any], known: Known) -> Drafted:
    """The brief and the deltas a run left in state, converted. The same call gives the same IDs, so what a gate
    checked is what the command writes."""
    draft = BriefDraft.model_validate(state[brief_stage.KEY])
    deltas = to_deltas(DeltasDraft.model_validate(state[deltas_stage.KEY]), known.living, known.taken, known.kept)
    return Drafted(to_brief(draft), deltas, draft.design_needed)


def files_of(made: Drafted) -> dict[str, str]:
    """A run's drafts as the files a change holds, by their paths in its folder: the brief, and one delta a
    capability. What the command writes, and what the chat shows."""
    files = {BRIEF_FILE: render_brief(made.brief)}
    files |= {f"{SPECS}/{capability}/{SPEC_FILE}": render_delta(delta) for capability, delta in made.deltas.items()}
    return files


def first_run(tier: Tier | None, seed: Mapping[str, Any]) -> tuple[Entry, dict[str, Any]]:
    """Where a propose starts, and what its run is seeded with: at triage, or straight at the brief where a person
    named the tier. Triage is asked for the tier alone; with the tier given, nothing would read its answer."""
    return ("brief", {**seed, TIER: tier}) if tier else ("triage", dict(seed))


def next_run(seed: Mapping[str, Any], state: Mapping[str, Any], answers: Sequence[str]) -> tuple[Entry, dict[str, Any]]:
    """Where the run after a round of questions starts, and what it is seeded with. `seed` is what the run that
    asked was seeded with, `state` what it left, and `answers` the person's, in the order of the questions under
    `ASKING`, an empty one for a point left open.

    What was answered starts the next run at the brief, each answer beside the question the person was shown, after
    those of the rounds before, and with the brief the questions were asked about, for the new draft to keep and
    settle. A round nobody answered starts it at the deltas, with the brief that passed its gate, its points left
    open."""
    carried = {**seed, TIER: state[TIER]}
    if not any(answers):
        return "deltas", {**carried, brief_stage.KEY: state[brief_stage.KEY]}
    told = [seed[brief_stage.ANSWERS]] if seed.get(brief_stage.ANSWERS) else []
    told += [f"{asked['question']} -> {answer}" for asked, answer in zip(state[ASKING], answers, strict=True) if answer]
    replaces = render_brief(_brief(state))  # the draft the questions were asked about: the next one starts from it
    return "brief", {
        **carried,
        brief_stage.ANSWERS: "\n".join(told),
        brief_stage.REPLACES: replaces,
        ROUNDS: (seed.get(ROUNDS) or 0) + 1,
    }


def _app(edges: list[Any], ledger: UsageLedger, recorder: BasePlugin | None = None) -> App:
    """An app of this package: one workflow named for it, with the roster's plugins."""
    return App(name=NAME, root_agent=Workflow(name=NAME, edges=edges), plugins=roster(ledger, recorder))


def build_triage_app(*, ledger: UsageLedger, recorder: BasePlugin | None = None) -> App:
    """Triage alone, behind its gate: the tier under `TIER`, `none` among them. `propose` sizes a request first, so
    that one owing no spec spends no reading of the code, and the brief is drafted after the reading, from it."""
    return _app(_opening(_ended, "triage", "START", _ended), ledger, recorder)


def build_smoke_app() -> App:
    """The triage stage alone: what `adk-spec smoke` runs to prove an arm answers in a schema."""
    edges = [("START", triage_stage.build_triage())]
    return App(name=NAME, root_agent=Workflow(name=NAME, edges=edges), plugins=[Scrub()])


# What each gate checks: what is wrong with the stage's answer, a sentence a problem.


def _check_brief(state: Mapping[str, Any]) -> list[str]:
    brief = _brief(state)
    if not brief.title:
        return [coded("brief.no-title", "the brief has no title. Give it one, on one line.")]
    text = render_brief(brief)
    try:
        same = parse_brief(text) == brief
    except GrammarError as exc:
        return [
            coded(
                "brief.unwritable",
                f"the brief cannot be written as its file: {exc.message}. Write no heading and no open code fence.",
            )
        ]
    if not same:
        return [
            coded(
                "brief.round-trip",
                "a section of the brief does not read back as written. Write no line that starts `## ` in one.",
            )
        ]
    found = validate_brief(brief, text)
    over = any(one.code == _OVER_BUDGET for one in found)
    return _errors([one for one in found if one.code != _OVER_BUDGET]) + ([_over_budget(state, text)] if over else [])


#: The validator's finding for a brief past its markers. It is worded for a person, "settle some with its author
#: first", which a stage cannot do: the gate says in its place what the stage can.
_OVER_BUDGET = "brief.markers-over-budget"


def _over_budget(state: Mapping[str, Any], text: str) -> str:
    draft = BriefDraft.model_validate(state[brief_stage.KEY])
    held = len(markers(text))
    by_hand = len(markers(render_brief(to_brief(draft.model_copy(update={"open_points": []})))))
    copied = f", {by_hand} of them written as a marker in a section. Write no marker there" if by_hand else ""
    return coded(
        _OVER_BUDGET,
        f"the brief leaves {held} points open, past the {MARKER_BUDGET} it may{copied}. Name in "
        "open_points the three that matter most, and state what you assume for the rest.",
    )


def _deltas_check(known: Known) -> Callable[[Mapping[str, Any]], list[str]]:
    def check_deltas(state: Mapping[str, Any]) -> list[str]:
        made = drafted(state, known)
        listed = set(made.brief.capabilities)
        problems = [
            coded(
                "delta.capability-unlisted",
                f"the delta names `{capability}`, which the brief does not list. Change only a "
                "capability the brief lists.",
            )
            for capability in made.deltas
            if capability not in listed
        ]
        problems += [
            coded(
                "delta.capability-missing", f"the brief lists `{capability}` and no delta changes it. Write its delta."
            )
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
        return [coded("delta.capability-bad-name", f"the delta names a capability that cannot be one: {why}.")]
    bases = capture_bases({capability: delta}, known.living)
    if wrong := _errors(validate_delta(delta, known.living.get(capability), bases)):
        return wrong
    try:
        read = parse_delta(render_delta(delta))
    except GrammarError as exc:
        return [coded("delta.unwritable", f"the delta of `{capability}` cannot be written as its file: {exc.message}.")]
    before, after = (*delta.added, *delta.modified), (*read.added, *read.modified)
    for wrote, back in zip(before, after, strict=False):
        if wrote != back:
            return [
                coded(
                    "delta.round-trip",
                    f"{wrote.id} `{wrote.name}` does not read back as written. Keep its name and each "
                    "step on one line, "
                    "and write no heading and no open code fence in its statement.",
                )
            ]
    if read != delta:
        return [
            coded(
                "delta.reason-round-trip",
                f"the delta of `{capability}` does not read back as written: keep each reason on one line.",
            )
        ]
    return []


def _check_design(state: Mapping[str, Any]) -> list[str]:
    draft = DesignDraft.model_validate(state[design_stage.KEY])
    return [
        coded("design.section-empty", f"the design's {name} section is empty. Write it.")
        for name in DESIGN_SECTIONS
        if not getattr(draft, name).strip()
    ]


def _tasks_check(owed: frozenset[str], nameable: frozenset[str]) -> Callable[[Mapping[str, Any]], list[str]]:
    """What the tasks' gate checks, for a change that owes a task to each of `owed` and may name any of `nameable`.
    The validator and the coverage speak before the round trip: they name the ID or the task that is wrong."""

    def check_tasks(state: Mapping[str, Any]) -> list[str]:
        groups = to_tasks(TasksDraft.model_validate(state[tasks_stage.KEY]))
        if not any(group.tasks for group in groups):
            return [
                coded(
                    "tasks.empty",
                    "the plan holds no task. Write one task at least for each requirement the deltas add or change.",
                )
            ]
        if wrong := _errors([*validate_tasks(groups), *coverage(groups, owed=owed, nameable=nameable)]):
            return wrong
        try:
            same = parse_tasks(render_tasks(groups)) == groups
        except GrammarError as exc:
            return [coded("tasks.unwritable", f"the tasks cannot be written as their file: {exc.message}.")]
        if same:
            return []
        sentence = "the tasks do not read back as written: keep each description and check on one line."
        return [coded("tasks.round-trip", sentence)]

    return check_tasks


# The nodes between the stages. One that reads what the command knows is made for it; the rest read state alone.


def _ended() -> Event:
    return Event(output="ended")


def _sized(ctx: Context) -> Event:
    """The model's tier, and the capabilities it found, which the brief starts from. `none` ends the run with nothing
    drafted. Found by the third audit: the chat gave the brief no capabilities, where `propose` gives them."""
    chosen = Triage.model_validate(ctx.state[triage_stage.KEY])
    found = {TIER: chosen.tier, SIZED: triage_stage.sized_text(chosen)}
    return Event(route=NONE if chosen.tier == "none" else GO, state=found)


def _open_points(ask: bool) -> Callable[[Context], Event]:
    def open_points(ctx: Context) -> Event:
        """Ask only where the command may, only on a tier that asks, only while the rounds last, and only while
        the brief leaves a point open. The questions are read by code from the brief that passed its gate, and the
        run ends on them: the command puts them to the person, and `next_run` starts the run after with what was
        answered."""
        asks = (tier := ctx.state.get(TIER)) in DEMANDS and DEMANDS[tier].asks
        if not (ask and asks and (ctx.state.get(ROUNDS) or 0) < ROUND_BUDGET):
            return Event(route=NONE)
        # The last round asks every point still open: found by review, one that waited was otherwise never shown.
        last = (ctx.state.get(ROUNDS) or 0) == ROUND_BUDGET - 1
        questions = questions_of(BriefDraft.model_validate(ctx.state[brief_stage.KEY]), every=last)
        return Event(route=SOME, state={ASKING: questions}) if questions else Event(route=NONE)

    return open_points


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


def _propose_edges(
    known: Known, *, ask: bool, entry: Entry, start: Any = "START", done: Any = _ended, ended: Any = _ended
) -> list[Any]:
    """The edges of a propose run from `entry` on: triage, the brief and the deltas, each behind its gate. The run
    begins after `start`, goes to `done` once the deltas pass their gate, and to `ended` wherever it stops short:
    a stage given up, or a request that owes no spec."""
    gathered = _gathering(known)
    deltas, deltas_gate = deltas_stage.build_deltas(), checked(deltas_stage.KEY, _deltas_check(known), learns=True)
    edges: list[Any] = [
        (gathered, {GO: deltas, STOP: ended}),
        (deltas, deltas_gate),
        (deltas_gate, {OK: done, AGAIN: deltas, GIVE_UP: ended}),
    ]
    if entry == "deltas":
        return [(start, gathered), *edges]
    open_points = _open_points(ask)
    brief, brief_gate = brief_stage.build_brief(), checked(brief_stage.KEY, _check_brief, learns=True)
    return [
        *_opening(brief, entry, start, ended),
        (brief, brief_gate),
        (brief_gate, {OK: open_points, AGAIN: brief, GIVE_UP: ended}),
        (open_points, {NONE: gathered, SOME: _ended}),  # a run that asks ends there; a chat never asks
        *edges,
    ]


def _opening(brief: Any, entry: Entry, start: Any, ended: Any) -> list[Any]:
    """The edges up to the brief: through triage for a request to size, straight to it otherwise."""
    if entry == "brief":
        return [(start, brief)]
    triage, triage_gate = triage_stage.build_triage(), checked(triage_stage.KEY, lambda _state: [])
    return [
        (start, triage, triage_gate),
        (triage_gate, {OK: _sized, AGAIN: triage, GIVE_UP: ended}),
        (_sized, {GO: brief, NONE: ended}),
    ]


def build_propose_app(
    known: Known, *, ask: bool, entry: Entry, ledger: UsageLedger, recorder: BasePlugin | None = None
) -> App:
    """Triage, the brief and the deltas, each behind its gate, from `entry` on. A request the model sizes as `none`
    ends the run with nothing drafted.

    With `ask`, a standard change whose brief leaves a point open ends its run on the questions, under `ASKING`.
    `first_run` and `next_run` say which entry a run takes and what it is seeded with."""
    edges = _propose_edges(known, ask=ask, entry=entry)
    return _app(edges, ledger, recorder)


#: Every key a propose run leaves in state, each set back to nothing. A command's run starts on a session of its
#: own; a chat keeps one session for all its messages, so what one message drafted, and how often its stages were
#: asked, would otherwise still be there for the next: a stage that failed would be answered with the old draft.
_DRAFTING = (triage_stage.KEY, brief_stage.KEY, deltas_stage.KEY)
_NOTHING_YET: dict[str, None] = dict.fromkeys(
    (
        *_DRAFTING,
        *(tries_key(stage) for stage in _DRAFTING),
        *(PENDING, SENT_BACK),
        *(FAILURE, FINDINGS, STAGE_ERROR, TIER, SIZED, ASKING, ROUNDS, BRIEF_TEXT, LIVING),
        *(brief_stage.ANSWERS, brief_stage.REPLACES),
    )
)


def build_chat_app(known: Known, told: Mapping[str, Any], *, ledger: UsageLedger) -> App:
    """The shape ADK's own interface loads: one message typed is one request. It is drafted as `propose` drafts it
    with no question asked and no code read, and the run ends on one message that holds the drafts as their files, or
    the reason there are none. Nothing is written: a chat is for watching a run, and `adk-spec propose` is what writes.

    `told` is what every run is seeded with of the workspace: the capability index and the repository's rules."""

    def opened(node_input: Any = None) -> Event:
        """The message typed becomes the request, beside what the workspace says."""
        parts = getattr(node_input, "parts", None) or ()
        typed = " ".join(part.text for part in parts if part.text) or str(node_input or "")
        return Event(state={**_NOTHING_YET, **told, REQUEST: typed})

    def shown(ctx: Context) -> Event:
        files = files_of(drafted(ctx.state.to_dict(), known))
        pages = "\n\n".join(f"--- {path}\n{text}" for path, text in files.items())
        return Event(
            content=types.ModelContent(f"Drafted, and not written. `adk-spec propose` writes a change.\n\n{pages}")
        )

    def closed(ctx: Context) -> Event:
        why = ctx.state.get(FAILURE)
        if not why and ctx.state.get(TIER) == "none":
            why = f"no spec is owed. {Triage.model_validate(ctx.state[triage_stage.KEY]).reason}"
        return Event(content=types.ModelContent(f"Nothing was drafted: {why or 'the run ended early'}"))

    edges = [
        ("START", opened),
        *_propose_edges(known, ask=False, entry="triage", start=opened, done=shown, ended=closed),
    ]
    return _app(edges, ledger)


def build_plan_app(
    *,
    design: bool,
    ledger: UsageLedger,
    owed: frozenset[str],
    nameable: frozenset[str],
    recorder: BasePlugin | None = None,
) -> App:
    """The design, where the change owes one, and then the tasks, each behind its gate. The tasks are held to the
    change's own requirements: each of `owed` served, and none named outside `nameable`."""
    tasks, tasks_gate = tasks_stage.build_tasks(), checked(tasks_stage.KEY, _tasks_check(owed, nameable), learns=True)
    edges: list[Any] = [(tasks, tasks_gate), (tasks_gate, {OK: _ended, AGAIN: tasks, GIVE_UP: _ended})]
    if design:
        drafting, design_gate = design_stage.build_design(), checked(design_stage.KEY, _check_design, learns=True)
        edges = [
            ("START", drafting, design_gate),
            (design_gate, {OK: _designed, AGAIN: drafting, GIVE_UP: _ended}),
            (_designed, tasks),
            *edges,
        ]
    else:
        edges = [("START", tasks), *edges]
    return _app(edges, ledger, recorder)


def build_check_app(*, ledger: UsageLedger, recorder: BasePlugin | None = None) -> App:
    """The check stage behind its gate. The gate holds the answer to its schema and nothing more: a finding that
    points at nothing is left out by code afterwards, not sent back."""
    check, check_gate = check_stage.build_check(), checked(check_stage.KEY, lambda _state: [])
    edges: list[Any] = [("START", check, check_gate), (check_gate, {OK: _ended, AGAIN: check, GIVE_UP: _ended})]
    return _app(edges, ledger, recorder)


def build_verify_app(*, ledger: UsageLedger, required: frozenset[str], recorder: BasePlugin | None = None) -> App:
    """The verify stage behind its gate, which holds it to one thing code can see: a verdict for each requirement
    of `required`. Whether a verdict stands is decided afterwards, against the diff."""

    def check_verdicts(state: Mapping[str, Any]) -> list[str]:
        given = {one.id.strip() for one in VerdictsDraft.model_validate(state[verify_stage.KEY]).verdicts}
        missing = sorted(required - given)
        return (
            [f"no verdict was given for {', '.join(missing)}. Give one for each requirement listed."] if missing else []
        )

    verify, verify_gate = verify_stage.build_verify(), checked(verify_stage.KEY, check_verdicts)
    edges: list[Any] = [("START", verify, verify_gate), (verify_gate, {OK: _ended, AGAIN: verify, GIVE_UP: _ended})]
    return _app(edges, ledger, recorder)
