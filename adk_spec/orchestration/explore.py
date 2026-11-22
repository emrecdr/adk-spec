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

from ..domain.convert import to_statements
from ..domain.drafts import ScoutDraft, SurveyDraft
from ..domain.model import Statement
from ..workspace.source import Source, merged
from .gate import AGAIN, GIVE_UP, OK, checked, tries_key
from .graph import NONE, SOME, _app, _ended
from .plugins import UsageLedger
from .stages import scout as scout_stage
from .stages import survey as survey_stage
from .stages.survey import MATERIAL, READ, STATED

#: How many rounds of reading one change gets, and how many statements are kept of it.
LOOK_BUDGET = 3
STATEMENT_BUDGET = 40
#: The state keys of a reading: the statements kept, each file's text as it was shown, what was asked for and not
#: given, how many statements quoted nothing real, how many rounds were read, every file read, how far each file
#: was read from its top, and every request that was made.
KEPT = "kept"
SEEN = "seen"
LEFT_OUT = "left_out"
DROPPED = "dropped"
LOOKS = "looks"
_READ_LIST = "read_list"
_REACHED = "reached"
_ASKED = "asked"


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


def _said(statements: Sequence[Statement]) -> str:
    """The statements kept so far, as a later round reads them: one a line."""
    return "\n".join(f"- {one.kind}: {one.path}:{one.line} {one.note}" for one in statements)


def _new(state: Mapping[str, Any], files: Sequence[str], folders: Sequence[str], searches: Sequence[str]) -> Any:
    """What of a request has not been answered yet, each piece with the key it is remembered by. A file read to its
    end and a request answered before are left out: the same text shown again would be paid for with a model call
    and tell it nothing. A file read from its top and cut there is read on from where it stopped, which is what
    asking for it again by its path means."""
    reached, asked = state.get(_REACHED) or {}, set(state.get(_ASKED) or ())
    wanted: list[tuple[str, str]] = []
    for one in files:
        path = one.strip()
        if path in reached:
            upto, total = reached[path]
            wanted += [(f"{path}:{upto + 1}-{total}", f"file {path}:{upto + 1}")] if upto < total else []
        else:
            wanted.append((path, f"file {path}"))
    listed = [(one, f"folder {one.strip().strip('/')}") for one in folders]
    sought = [(one, f"search {one.strip()}") for one in searches]
    fresh = []
    for part in (wanted, listed, sought):
        once = {key: what for what, key in reversed(part) if key not in asked}  # one named twice is read once
        fresh.append([(what, key) for key, what in reversed(once.items())])
    return fresh


def _looking(source: Source) -> tuple[Callable[[Context], Event], Callable[[Context], Event]]:
    """The two nodes that read: the first look, of what the scout named, and each look after a survey."""

    def look(state: Mapping[str, Any], files: Sequence[str], folders: Sequence[str], searches: Sequence[str]) -> Event:
        """One round read and left in state for the survey, or the run's end where nothing new is left to show."""
        fresh = _new(state, files, folders, searches)
        if not any(fresh):
            return Event(route=NONE)
        got = source.gathered(*([what for what, _key in part] for part in fresh))
        # What was left out for room alone is not answered: asked for again, it is read.
        later = set(got.deferred)
        answered = [key for part in fresh for what, key in part if what not in later]
        seen = dict(state.get(SEEN) or {})
        for path, text in got.texts.items():
            seen[path] = merged(seen.get(path, ""), text)
        reached = dict(state.get(_REACHED) or {})
        for path, (first, upto, total) in got.reached.items():
            if first == 1 or (path in reached and first == reached[path][0] + 1):  # read on from its top
                reached[path] = [upto, total]
        read = list(state.get(_READ_LIST) or ())
        read += [note for note in got.read if note not in read]
        update = {
            SEEN: seen,
            _REACHED: reached,
            _ASKED: [*(state.get(_ASKED) or ()), *answered],
            _READ_LIST: read,
            READ: "\n".join(read),
            LEFT_OUT: [*(state.get(LEFT_OUT) or ()), *got.left_out],
        }
        if not got.shown:
            return Event(route=NONE, state=update)
        # The survey of this round starts anew: its own tries, and no answer of the round before to be taken for it.
        anew = {survey_stage.KEY: None, tries_key(survey_stage.KEY): 0, LOOKS: (state.get(LOOKS) or 0) + 1}
        return Event(route=SOME, state={**update, **anew, MATERIAL: got.shown})

    def first_look(ctx: Context) -> Event:
        asked = ScoutDraft.model_validate(ctx.state[scout_stage.KEY])
        return look(ctx.state.to_dict(), asked.files, asked.folders, asked.searches)

    def next_look(ctx: Context) -> Event:
        asked = SurveyDraft.model_validate(ctx.state[survey_stage.KEY])
        return look(ctx.state.to_dict(), asked.more_files, asked.more_folders, asked.more_searches)

    return first_look, next_look


def _grounded(ctx: Context) -> Event:
    """What the survey stated is held to the text it was shown, and kept. It is a node of its own, before any
    further reading: what was kept is in state whatever becomes of the reading after it. The run reads on where the
    survey asked for more and a round and room for a statement are left."""
    state = ctx.state.to_dict()
    answer = SurveyDraft.model_validate(state[survey_stage.KEY])
    fresh, dropped = to_statements(answer, state.get(SEEN) or {})
    before = explored(state)
    held = {(one.path, one.line, one.kind) for one in before.statements}
    kept = [*before.statements, *(one for one in fresh if (one.path, one.line, one.kind) not in held)]
    kept = kept[:STATEMENT_BUDGET]
    update = {KEPT: [one.model_dump() for one in kept], STATED: _said(kept), DROPPED: before.dropped + dropped}
    more = any((answer.more_files, answer.more_folders, answer.more_searches))
    on = more and (state.get(LOOKS) or 0) < LOOK_BUDGET and len(kept) < STATEMENT_BUDGET
    return Event(route=SOME if on else NONE, state=update)


def build_explore_app(*, source: Source, ledger: UsageLedger, recorder: BasePlugin | None = None) -> App:
    """The scout behind its gate, the first look, and then the survey behind its gate for as many rounds as it asks
    for and the budget leaves. Every way out ends the run: what was kept is read from its state by `explored`."""
    first_look, next_look = _looking(source)
    scout, scout_gate = scout_stage.build_scout(), checked(scout_stage.KEY, lambda _state: [])
    survey, survey_gate = survey_stage.build_survey(), checked(survey_stage.KEY, lambda _state: [])
    edges: list[Any] = [
        ("START", scout, scout_gate),
        (scout_gate, {OK: first_look, AGAIN: scout, GIVE_UP: _ended}),
        (first_look, {SOME: survey, NONE: _ended}),
        (survey, survey_gate),
        (survey_gate, {OK: _grounded, AGAIN: survey, GIVE_UP: _ended}),
        (_grounded, {SOME: next_look, NONE: _ended}),
        (next_look, {SOME: survey, NONE: _ended}),
    ]
    return _app(edges, ledger, recorder)
