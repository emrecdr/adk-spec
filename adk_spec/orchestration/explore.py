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
from ..domain.drafts import ReviewDraft, ScoutDraft, SurveyDraft
from ..domain.model import Statement
from ..domain.text import plain
from ..workspace.source import Source, merged
from .gate import AGAIN, GIVE_UP, OK, checked, tries_key
from .graph import NONE, SOME, _app, _ended
from .plugins import UsageLedger
from .stages import LIBRARIES
from .stages import review as review_stage
from .stages import scout as scout_stage
from .stages import survey as survey_stage
from .stages.survey import MATERIAL, READ, STATED

#: The roles of the reading's stages, each one's model asked after before a command spends anything.
ROLES = (scout_stage.KEY, survey_stage.KEY, review_stage.KEY)
#: How many rounds of reading one change gets, and how many statements are kept of it.
LOOK_BUDGET = 3
STATEMENT_BUDGET = 40
#: How often a reading is reviewed, and how many unknowns, each how long, a review leaves.
REVIEW_BUDGET = 2
#: The most model calls one reading makes, a gate's asking again aside: a scout, the rounds and the review's one
#: round more, each surveyed, and the reviews. What a command says before it reads.
MAX_CALLS = 1 + LOOK_BUDGET + 1 + REVIEW_BUDGET
#: The brief a reading of a whole repository is seeded with, where there is no change: `init`'s.
DESCRIBE = """\
# Describe this repository

## Why

A person is about to change this repository, and needs to know it first.

## What changes

Nothing. Read the code to state what a person changing it first needs to know about the whole repository, not one
feature of it: the stack and its versions; the layout, and where each part lives; how it is built, run and tested;
how errors, logging and configuration are handled; and what is risky to change.

Phrase each convention as a rule new code must follow, in one sentence, such as "Every error is raised as an
AppError." or "Each module has its test beside it, named after it.": what is merely there is not a convention.
"""
UNKNOWN_BUDGET = 8
QUESTION_MAX_CHARS = 200
WHERE_MAX_CHARS = 120
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
#: Phase 18: the searches and folder listings made, how many statements and unknowns went past their budgets, and
#: what was asked for past what the reading reads; kept apart from what was left out, which the review is told.
_LOOKED_LIST = "looked_list"
_OVER = "over"
_UNKNOWN_OVER = "unknown_over"
_UNREAD = "unread"
#: What the review leaves: what is still unknown, how many statements it disputed, and how often it ran.
UNKNOWN = "unknown"
DISPUTED = "disputed"
REVIEWS = "reviews"


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
    #: What the last review named as still unknown, each a question and where it might be answered.
    unknown: tuple[tuple[str, str], ...] = ()
    #: How many statements a review left out for a quote that does not bear out their note.
    disputed: int = 0
    #: Each search made and folder listed, with what it found.
    looked: tuple[str, ...] = ()
    #: How many statements went past the budget, and how many unknowns past theirs.
    over: int = 0
    unknown_over: int = 0
    #: How many requests went past what the reading reads.
    unread: int = 0


def explored(state: Mapping[str, Any]) -> Explored:
    """What a run kept, as it stands in `state`: also the state of a run that ended early."""
    statements = [Statement.model_validate(one) for one in state.get(KEPT) or ()]
    unknown = tuple((question, where) for question, where in state.get(UNKNOWN) or ())
    read, left_out = tuple(state.get(_READ_LIST) or ()), tuple(state.get(LEFT_OUT) or ())
    return Explored(
        statements,
        read,
        left_out,
        state.get(DROPPED) or 0,
        unknown,
        state.get(DISPUTED) or 0,
        looked=tuple(state.get(_LOOKED_LIST) or ()),
        over=state.get(_OVER) or 0,
        unknown_over=state.get(_UNKNOWN_OVER) or 0,
        unread=state.get(_UNREAD) or 0,
    )


def _unread(state: Mapping[str, Any], answer: SurveyDraft | ReviewDraft) -> dict[str, Any]:
    """How many of the requests of `answer` not answered already go past what the reading reads, added to those before:
    a count, as the request is the model's words. Found by phase 18's code review: named, a request read whole before
    was said not read, and a model's text went into the file whole."""
    fresh = _new(state, answer.more_files, answer.more_folders, answer.more_searches)
    return {_UNREAD: (state.get(_UNREAD) or 0) + sum(len(part) for part in fresh)}


def _said(statements: Sequence[Statement]) -> str:
    """The statements kept so far, as a later round reads them: one a line."""
    return "\n".join(
        f"- {one.kind}: {one.path}:{one.line} {one.note}" + (f" (in: {one.within})" if one.within else "")
        for one in statements
    )


def _holding(statements: Sequence[Statement]) -> dict[str, Any]:
    """The statements kept, as state holds them: the records, and the same as the next survey reads them."""
    return {KEPT: [one.model_dump() for one in statements], STATED: _said(statements)}


def _numbered(statements: Sequence[Statement]) -> str:
    """The statements kept, as the review reads them: each numbered, with the block it stands in and its quote."""
    return "\n".join(
        f"{number}. {one.kind} {one.path}:{one.line}"
        + (f"\n   in: {one.within}" if one.within else "")
        + f"\n   {one.note}\n   > {one.quote}"
        for number, one in enumerate(statements, 1)
    )


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


def _look(
    source: Source, state: Mapping[str, Any], files: Sequence[str], folders: Sequence[str], searches: Sequence[str]
) -> Event:
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
    looked = list(state.get(_LOOKED_LIST) or ())
    looked += [note for note in got.looked if note not in looked]
    update = {
        SEEN: seen,
        _REACHED: reached,
        _ASKED: [*(state.get(_ASKED) or ()), *answered],
        _READ_LIST: read,
        _LOOKED_LIST: looked,
        READ: "\n".join(read),
        LEFT_OUT: [*(state.get(LEFT_OUT) or ()), *got.left_out],
    }
    if not got.shown:
        return Event(route=NONE, state=update)
    # The survey of this round starts anew: its own tries, and no answer of the round before to be taken for it.
    anew = {survey_stage.KEY: None, tries_key(survey_stage.KEY): 0, LOOKS: (state.get(LOOKS) or 0) + 1}
    return Event(route=SOME, state={**update, **anew, MATERIAL: got.shown, LIBRARIES: source.libraries()})


def _looking(source: Source) -> tuple[Callable[[Context], Event], ...]:
    """The nodes that read: the first look, of what the scout named; each look after a survey; the one look a review
    may ask for, past the rounds of the budget; and the grounding of what a survey stated, which finds the block each
    quoted line stands in."""

    def first_look(ctx: Context) -> Event:
        asked = ScoutDraft.model_validate(ctx.state[scout_stage.KEY])
        return _look(source, ctx.state.to_dict(), asked.files, asked.folders, asked.searches)

    def next_look(ctx: Context) -> Event:
        asked = SurveyDraft.model_validate(ctx.state[survey_stage.KEY])
        return _look(source, ctx.state.to_dict(), asked.more_files, asked.more_folders, asked.more_searches)

    def review_look(ctx: Context) -> Event:
        asked = ReviewDraft.model_validate(ctx.state[review_stage.KEY])
        return _look(source, ctx.state.to_dict(), asked.more_files, asked.more_folders, asked.more_searches)

    def grounded(ctx: Context) -> Event:
        return _grounded(ctx, source)

    return first_look, next_look, review_look, grounded


def _grounded(ctx: Context, source: Source) -> Event:
    """What the survey stated is held to the text it was shown, and kept, each with the block its quoted line stands
    in. It is a node of its own, before any further reading: what was kept is in state whatever becomes of the
    reading after it. The run reads on where the survey asked for more and a round and room for a statement are
    left, and goes to the review where not."""
    state = ctx.state.to_dict()
    answer = SurveyDraft.model_validate(state[survey_stage.KEY])
    found, dropped = to_statements(answer, state.get(SEEN) or {})
    fresh = [one.model_copy(update={"within": source.within(one.path, one.line)}) for one in found]
    before = explored(state)
    held = {(one.path, one.line, one.kind) for one in before.statements}
    kept = [*before.statements, *(one for one in fresh if (one.path, one.line, one.kind) not in held)]
    over = max(0, len(kept) - STATEMENT_BUDGET)
    kept = kept[:STATEMENT_BUDGET]
    update = {**_holding(kept), DROPPED: before.dropped + dropped, _OVER: before.over + over}
    more = any((answer.more_files, answer.more_folders, answer.more_searches))
    on = more and (state.get(LOOKS) or 0) < LOOK_BUDGET and len(kept) < STATEMENT_BUDGET
    return Event(route=SOME if on else NONE, state={**update, **(_unread(state, answer) if more and not on else {})})


def _to_review(ctx: Context) -> Event:
    """The review started anew on what was kept, numbered: its own tries, and no answer of the review before. No
    review where nothing was kept, or where the reviews of the budget ran."""
    state = ctx.state.to_dict()
    found, reviews = explored(state), state.get(REVIEWS) or 0
    if not found.statements or reviews >= REVIEW_BUDGET:
        return Event(route=NONE)
    anew = {review_stage.KEY: None, tries_key(review_stage.KEY): 0, REVIEWS: reviews + 1}
    numbered = {review_stage.NUMBERED: _numbered(found.statements), review_stage.NOT_READ: "\n".join(found.left_out)}
    return Event(route=SOME, state={**anew, **numbered})


def _weighed(ctx: Context) -> Event:
    """What the review said, done: each disputed statement that names a kept number left out and counted, and what
    is still unknown kept, plain and within the budget. The run reads one more round where the review asked for it
    and a review is left."""
    state = ctx.state.to_dict()
    answer = ReviewDraft.model_validate(state[review_stage.KEY])
    found = explored(state)
    numbers = {one.statement for one in answer.disputed}
    kept = [one for number, one in enumerate(found.statements, 1) if number not in numbers]
    asked = ((plain(one.question)[:QUESTION_MAX_CHARS], plain(one.where)[:WHERE_MAX_CHARS]) for one in answer.unknown)
    # The last review's unknowns stand, as it read what the first asked for. Phase 18: those past the budget counted.
    unknown = [[question, where] for question, where in asked if question]
    disputed = found.disputed + len(found.statements) - len(kept)
    over = max(0, len(unknown) - UNKNOWN_BUDGET)
    update = {**_holding(kept), DISPUTED: disputed, UNKNOWN: unknown[:UNKNOWN_BUDGET], _UNKNOWN_OVER: over}
    more = any((answer.more_files, answer.more_folders, answer.more_searches))
    on = more and (state.get(REVIEWS) or 0) < REVIEW_BUDGET and len(kept) < STATEMENT_BUDGET
    return Event(route=SOME if on else NONE, state={**update, **(_unread(state, answer) if more and not on else {})})


def build_explore_app(*, source: Source, ledger: UsageLedger, recorder: BasePlugin | None = None) -> App:
    """The scout behind its gate, the first look, and then the survey behind its gate for as many rounds as it asks
    for and the budget leaves; then the review behind its gate, which may send the reading one round further and is
    then asked once more. At most seven model calls: one scout, four surveys, two reviews. Every way out ends the
    run: what was kept is read from its state by `explored`."""
    first_look, next_look, review_look, grounded = _looking(source)
    scout, scout_gate = scout_stage.build_scout(), checked(scout_stage.KEY, lambda _state: [])
    survey, survey_gate = survey_stage.build_survey(), checked(survey_stage.KEY, lambda _state: [])
    review, review_gate = review_stage.build_review(), checked(review_stage.KEY, lambda _state: [])
    edges: list[Any] = [
        ("START", scout, scout_gate),
        (scout_gate, {OK: first_look, AGAIN: scout, GIVE_UP: _ended}),
        (first_look, {SOME: survey, NONE: _ended}),
        (survey, survey_gate),
        (survey_gate, {OK: grounded, AGAIN: survey, GIVE_UP: _ended}),
        (grounded, {SOME: next_look, NONE: _to_review}),
        (next_look, {SOME: survey, NONE: _to_review}),
        (_to_review, {SOME: review, NONE: _ended}),
        (review, review_gate),
        (review_gate, {OK: _weighed, AGAIN: review, GIVE_UP: _ended}),
        (_weighed, {SOME: review_look, NONE: _ended}),
        (review_look, {SOME: survey, NONE: _ended}),
    ]
    return _app(edges, ledger, recorder)
