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
from google.adk.workflow import Workflow

from ..domain.brief_md import render_brief
from ..domain.convert import to_brief, to_deltas
from ..domain.delta_md import parse_delta, render_delta
from ..domain.drafts import BriefDraft, DeltasDraft, Triage
from ..domain.ids import slug_problem
from ..domain.lifecycle import capture_bases
from ..domain.model import Brief, Delta, Finding, GrammarError, Spec, Tier
from ..domain.spec_md import render_spec
from ..domain.validate import validate_brief, validate_delta
from ..workspace.context import ContextTooLargeError, joined
from .gate import AGAIN, FAILURE, GIVE_UP, OK, checked
from .plugins import roster
from .stages import brief as brief_stage
from .stages import deltas as deltas_stage
from .stages import triage as triage_stage

NAME = "adk_spec"
#: The state key the tier a run settled on is left under: a tier, or `none` where no spec is owed.
TIER = "tier"
GO, NONE, STOP = "GO", "NONE", "STOP"


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


def build_propose_app(known: Known, *, tier: Tier | None, ask: bool) -> App:  # noqa: ARG001 -- `ask`: the questions
    """Triage, the brief and the deltas, each behind its gate. `tier` is a person's own choice, which wins over the
    model's; with none, a request the model sizes as `none` ends the run with nothing drafted."""

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

    def sized(ctx: Context) -> Event:
        """The tier the run goes on with: the person's, else the model's, `strict` read as `standard` for now."""
        model = Triage.model_validate(ctx.state[triage_stage.KEY]).tier
        chosen = tier or ("standard" if model == "strict" else model)
        return Event(route=NONE if chosen == "none" else GO, state={TIER: chosen})

    def gathered(ctx: Context) -> Event:
        """What the deltas stage reads: the brief as its file, and each living spec it touches, whole."""
        _draft, brief = _brief(ctx.state.to_dict())
        specs = {slug: render_spec(known.living[slug]) for slug in brief.capabilities if slug in known.living}
        try:
            living = joined(specs)
        except ContextTooLargeError as exc:
            return Event(route=STOP, state={FAILURE: f"context: {exc}"})
        return Event(route=GO, state={deltas_stage.BRIEF_TEXT: render_brief(brief), deltas_stage.LIVING: living})

    def ended() -> Event:
        return Event(output="ended")

    triage, brief, deltas = triage_stage.build_triage(), brief_stage.build_brief(), deltas_stage.build_deltas()
    triage_gate = checked(triage_stage.KEY, lambda _state: [])
    brief_gate = checked(brief_stage.KEY, check_brief)
    deltas_gate = checked(deltas_stage.KEY, check_deltas)
    edges = [
        ("START", triage, triage_gate),
        (triage_gate, {OK: sized, AGAIN: triage, GIVE_UP: ended}),
        (sized, {GO: brief, NONE: ended}),
        (brief, brief_gate),
        (brief_gate, {OK: gathered, AGAIN: brief, GIVE_UP: ended}),
        (gathered, {GO: deltas, STOP: ended}),
        (deltas, deltas_gate),
        (deltas_gate, {OK: ended, AGAIN: deltas, GIVE_UP: ended}),
    ]
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
