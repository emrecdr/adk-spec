"""The reading of a repository's code for one change: the model points, and Python reads.

A scout names what to read. Code reads it through `Source`, which uses a path only where git lists it. A survey
states what the text shows, each statement with a quote, and code keeps a statement only where its quote is in the
file it names. The survey may ask to see more, and code reads again while a round is left.

The run ends with what was kept in state, also where it ends early: a stage given up, or the token ceiling. What a
command writes of it, and whether a plan goes on without it, is the command's.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from google.adk.agents.context import Context
from google.adk.apps.app import App
from google.adk.events import Event
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.workflow import Workflow

from ..domain.convert import to_statements
from ..domain.drafts import ScoutDraft, SurveyDraft
from ..domain.model import Statement
from ..workspace.source import Source, merged
from .gate import AGAIN, GIVE_UP, OK, checked, tries_key
from .plugins import UsageLedger, roster
from .stages import scout as scout_stage
from .stages import survey as survey_stage
from .stages.survey import MATERIAL, READ, STATED

NAME = "adk_spec"
#: How many rounds of reading one change gets, and how many statements are kept of it.
LOOK_BUDGET = 3
STATEMENT_BUDGET = 40
SOME, NONE = "SOME", "NONE"
#: The state keys of a reading: the statements kept, each file's text as it was shown, what was asked for and not
#: given, how many statements quoted nothing real, and how many rounds were read.
KEPT = "kept"
SEEN = "seen"
LEFT_OUT = "left_out"
DROPPED = "dropped"
LOOKS = "looks"
_READ_LIST = "read_list"


@dataclass(frozen=True)
class Explored:
    """What a reading kept."""

    statements: list[Statement]
    #: Each file read, with how much of it.
    read: tuple[str, ...]
    #: What was asked for and not given, each with why.
    left_out: tuple[str, ...]
    #: How many statements were left out for quoting text that is not in the file they name.
    dropped: int


def explored(state: Mapping[str, Any]) -> Explored:
    """What a run kept, as it stands in `state`: also the state of a run that ended early."""
    statements = [Statement.model_validate(one) for one in state.get(KEPT) or ()]
    return Explored(
        statements, tuple(state.get(_READ_LIST) or ()), tuple(state.get(LEFT_OUT) or ()), state.get(DROPPED) or 0
    )


def _ended() -> Event:
    return Event(output="ended")


def _said(statements: Sequence[Statement]) -> str:
    """The statements kept so far, as a later round reads them: one a line."""
    return "\n".join(f"- {one.kind}: {one.path}:{one.line} {one.note}" for one in statements)


def _looking(source: Source) -> tuple[Callable[[Context], Event], Callable[[Context], Event]]:
    """The two nodes that read: the first look, of what the scout named, and each look after a survey."""

    def look(
        state: Mapping[str, Any], files: Sequence[str], folders: Sequence[str], searches: Sequence[str]
    ) -> tuple[str, dict[str, Any]]:
        """One round read: where the run goes next, and what the round leaves in state. It goes to the survey with
        what was read, or to its end where there is nothing to show."""
        read = list(state.get(_READ_LIST) or ())
        whole = {note.removesuffix(" (whole)") for note in read if note.endswith(" (whole)")}
        got = source.gathered([path for path in files if path.strip() not in whole], folders, searches)
        seen = dict(state.get(SEEN) or {})
        for path, text in got.texts.items():
            seen[path] = merged(seen[path], text) if path in seen else text
        read += [note for note in got.read if note not in read]
        update = {
            SEEN: seen,
            _READ_LIST: read,
            READ: "\n".join(read),
            LEFT_OUT: [*(state.get(LEFT_OUT) or ()), *got.left_out],
        }
        if not got.shown:
            return NONE, update
        # The survey of this round starts anew: its own tries, and no answer of the round before to be taken for it.
        fresh = {survey_stage.KEY: None, tries_key(survey_stage.KEY): 0, LOOKS: (state.get(LOOKS) or 0) + 1}
        return SOME, {**update, **fresh, MATERIAL: got.shown}

    def first_look(ctx: Context) -> Event:
        asked = ScoutDraft.model_validate(ctx.state[scout_stage.KEY])
        route, update = look(ctx.state.to_dict(), asked.files, asked.folders, asked.searches)
        return Event(route=route, state=update)

    def grounded(ctx: Context) -> Event:
        """What the survey stated is held to the text it was shown, and what it asked for is read while a round and
        room for a statement are left."""
        state = ctx.state.to_dict()
        answer = SurveyDraft.model_validate(state[survey_stage.KEY])
        fresh, dropped = to_statements(answer, state.get(SEEN) or {})
        kept = [Statement.model_validate(one) for one in state.get(KEPT) or ()]
        held = {(one.path, one.line, one.kind) for one in kept}
        kept += [one for one in fresh if (one.path, one.line, one.kind) not in held]
        kept = kept[:STATEMENT_BUDGET]
        update = {
            KEPT: [one.model_dump() for one in kept],
            STATED: _said(kept),
            DROPPED: (state.get(DROPPED) or 0) + dropped,
        }
        more = (answer.more_files, answer.more_folders, answer.more_searches)
        if not any(more) or (state.get(LOOKS) or 0) >= LOOK_BUDGET or len(kept) >= STATEMENT_BUDGET:
            return Event(route=NONE, state=update)
        route, read = look({**state, **update}, *more)
        return Event(route=route, state={**update, **read})

    return first_look, grounded


def build_explore_app(*, source: Source, ledger: UsageLedger, recorder: BasePlugin | None = None) -> App:
    """The scout behind its gate, the first look, and then the survey behind its gate for as many rounds as it asks
    for and the budget leaves. Every way out ends the run: what was kept is read from its state by `explored`."""
    first_look, grounded = _looking(source)
    scout, scout_gate = scout_stage.build_scout(), checked(scout_stage.KEY, lambda _state: [])
    survey, survey_gate = survey_stage.build_survey(), checked(survey_stage.KEY, lambda _state: [])
    edges: list[Any] = [
        ("START", scout, scout_gate),
        (scout_gate, {OK: first_look, AGAIN: scout, GIVE_UP: _ended}),
        (first_look, {SOME: survey, NONE: _ended}),
        (survey, survey_gate),
        (survey_gate, {OK: grounded, AGAIN: survey, GIVE_UP: _ended}),
        (grounded, {SOME: survey, NONE: _ended}),
    ]
    return App(name=NAME, root_agent=Workflow(name=NAME, edges=edges), plugins=roster(ledger, recorder))
