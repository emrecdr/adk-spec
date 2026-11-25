"""The `adk-spec` command. `main` is a function of its arguments and returns the exit code; `run` is the process
boundary, which sets the console's encoding once and turns Ctrl-C into a sentence.

The engine is never imported at the top: a handler that calls a model imports it inside itself, so `--version`, a
usage error and every command that calls no model start without it.
"""

from __future__ import annotations

import argparse
import contextlib
import getpass
import json
import os
import re
import sys
from collections import Counter
from collections.abc import Callable, Generator, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from importlib import metadata
from pathlib import Path
from typing import Any, NoReturn

from ..domain.brief_md import assumption_count, parse_brief, render_brief
from ..domain.changelog_md import changelog_entry, with_entry
from ..domain.check import nameable, owed, removed, tasked
from ..domain.ci_md import annotation_lines, step_summary
from ..domain.context_md import (
    PARTIAL,
    PROFILE_HEADING,
    PROFILE_SECTIONS,
    SECTIONS,
    drafted_rules,
    render_context,
    unknown_count,
)
from ..domain.convert import kept_ids, questions_of, render_design, revision, slug_of, to_findings, to_tasks
from ..domain.delta_md import render_delta
from ..domain.evidence_md import kept, render_evidence
from ..domain.lifecycle import (
    DEMANDS,
    Step,
    approval_checks_first,
    approval_files,
    approval_stale,
    approve,
    approve_blockers,
    approver_blockers,
    archive_blockers,
    blocking,
    capture_bases,
    check_blockers,
    check_stands,
    check_stops,
    checked,
    edited_drafts,
    first_of_two,
    kept_bases,
    merge_gate,
    missing_bases,
    model_holds,
    next_step,
    owes_design,
    plan_blockers,
    reopened,
    verified,
    verify_blockers,
)
from ..domain.merge import MergeError, apply_delta
from ..domain.model import TIERS, Brief, Change, ChangeState, Delta, Finding, GrammarError, Spec, Tier
from ..domain.remaining import remaining, render_remaining
from ..domain.report_md import left_out, place, render_check, render_tests, render_verify
from ..domain.review_md import render_review, review_said
from ..domain.secrets import scrub, scrub_lines
from ..domain.spec_md import render_spec
from ..domain.summary_md import render_summary
from ..domain.tasks_md import render_tasks
from ..domain.text import lines_of, plain, sha256_of
from ..domain.validate import UNREAD, failed, finding, validate_spec
from ..domain.verify import TestRun, Verdict, grounded, parts_of_diff
from ..workspace.config import ConfigError
from ..workspace.context import (
    CONSTITUTION_MAX_CHARS,
    ContextTooLargeError,
    capability_index,
    constitution_text,
    context_of,
    context_text,
    files_text,
    lessons_text,
    living_text,
    profile_text,
)
from ..workspace.evidence import evidence_findings, evidence_folded
from ..workspace.files import NotTextError, append_text, read_text
from ..workspace.git import DIFF_MAX_CHARS, GitError, head, is_repository, resolves
from ..workspace.layout import BRIEF as BRIEF_FILE
from ..workspace.layout import (
    CHANGELOG,
    CHANGES,
    CONSTITUTION,
    EVIDENCE,
    LESSONS,
    PROFILE,
    REMAINING,
    REPORTS,
    REVIEW,
    ROOT_NAME,
    SPEC_FILE,
    SPECS,
    LoadedChange,
    Workspace,
    WorkspaceError,
    findings_of,
)
from ..workspace.layout import CONTEXT as CONTEXT_FILE
from ..workspace.layout import DESIGN as DESIGN_FILE
from ..workspace.layout import STATE as STATE_FILE
from ..workspace.layout import TASKS as TASKS_FILE
from ..workspace.lock import held as lock_held
from ..workspace.paths import PathError
from ..workspace.runs import Recording
from ..workspace.runs import write as write_run
from ..workspace.skill import SKILL_PARTS, write_skill
from ..workspace.source import NAME, Source, SourceError, Work, repositories_named
from ..workspace.tests import run_tests

EXIT_OK = 0
#: A gate refused, or findings at the bar.
EXIT_FINDINGS = 1
#: A usage or configuration error, before anything is spent.
EXIT_USAGE = 2
#: The engine or the provider failed.
EXIT_ENGINE = 3
EXIT_INTERRUPTED = 130

PROG = "adk-spec"
#: The checkout's root, whose `.env` alone is read: never one of the repository being worked on.
CHECKOUT = Path(__file__).resolve().parents[2]
SMOKE_REQUEST = "Let users reset a forgotten password by email."
#: What the workspace refuses with one sentence: said to the person, and `EXIT_USAGE`.
REFUSALS = (WorkspaceError, ConfigError, PathError, NotTextError, SourceError)


class NotYetError(Exception):
    """A command that cannot do its work yet, for a reason in the change itself: said, and exit code 1."""


class UsageError(Exception):
    """A usage or configuration error: one sentence for the person, and `EXIT_USAGE`."""


class _Parser(argparse.ArgumentParser):
    """argparse's, its every error ending with where to look next."""

    def error(self, message: str) -> NoReturn:
        super().error(f"{message}\n{PROG}: --help lists every command and flag")


#: The commands as the help lists them. One change is the first four: a command where a person decides something,
#: with the tool's own work inside it. The second group does one step of that work again, by itself.
COMMAND_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Everyday", ("propose", "approve", "verify", "archive", "status", "init")),
    ("To redo one step", ("plan", "check", "rebase", "validate", "new")),
    ("Setup", ("login", "models", "smoke")),
)


class _Top(_Parser):
    """The parser of the command itself, whose help lists the commands in their groups: what most people need
    first, and the rest apart."""

    commands: Any = None

    def format_help(self) -> str:
        formatter = self._get_formatter()
        formatter.add_usage(self.usage, self._actions, self._mutually_exclusive_groups)
        formatter.add_text(self.description)
        listed = {action.dest: action for action in self.commands._get_subactions()}  # argparse's own help rows
        for heading, names in COMMAND_GROUPS:
            formatter.start_section(heading)
            formatter.add_arguments([listed[name] for name in names if name in listed])
            formatter.end_section()
        formatter.start_section("Options")
        formatter.add_arguments([action for action in self._actions if action.option_strings])
        formatter.end_section()
        return formatter.format_help()


def _parser() -> _Top:
    parser = _Top(prog=PROG, description="Spec-driven development on Google ADK.")
    parser.add_argument("--version", action="version", version=f"{PROG} {metadata.version('adk-spec')}")
    parser.add_argument("--root", default=".", help="a folder in the repository to work in (default: this one)")
    commands = parser.commands = parser.add_subparsers(metavar="command", parser_class=_Parser)

    init = commands.add_parser("init", help=f"make the {ROOT_NAME} tree in this repository, and describe its code")
    init.add_argument("--no-explore", action="store_true", help="read none of the repository's code")
    init.add_argument(
        "--refresh",
        action="store_true",
        help="read the code again and rewrite the profile; with --no-explore, add the skill where it is missing",
    )
    init.set_defaults(handler=_init)

    new = commands.add_parser("new", help="start a change: its folder and its state file")
    new.add_argument("id", help="the change's name: lowercase words joined by hyphens")
    new.add_argument("--tier", choices=TIERS, help="how much ceremony it gets (default: the config's)")
    new.set_defaults(handler=_locked(_new))

    validate = commands.add_parser("validate", help="check the structure of the living specs and of open changes")
    validate.add_argument("id", nargs="?", help="one change to check, in place of every open one")
    validate.add_argument("--strict", action="store_true", help="fail on a warning too")
    validate.add_argument("--json", action="store_true", help="print the findings as JSON")
    validate.set_defaults(handler=_validate)

    status = commands.add_parser("status", help="list each open change and what to do next with it")
    status.add_argument("--all", action="store_true", help="list archived changes too")
    status.add_argument("--json", action="store_true", help="print the list as JSON")
    status.set_defaults(handler=_status)

    rebase = commands.add_parser("rebase", help="record anew what a change's deltas are written against")
    rebase.add_argument("id", help="the change")
    rebase.set_defaults(handler=_locked(_rebase))

    approval = commands.add_parser("approve", help="check a change, then record your approval of its files")
    approval.add_argument("id", help="the change")
    approval.add_argument("--by", help="who approves: a recorded claim, not an authentication (default: this account)")
    approval.add_argument("--strict", action="store_true", help="refuse on a warning too")
    approval.add_argument(
        "--override", metavar="REASON", help="approve although the check found something blocking, and record why"
    )
    approval.set_defaults(handler=_locked(_approve))

    archive = commands.add_parser("archive", help="fold a finished change into the living specs")
    archive.add_argument("id", help="the change")
    archive.set_defaults(handler=_locked(_archive))

    propose = commands.add_parser("propose", help="draft a whole change from a request: brief, specs and tasks")
    propose.add_argument("request", help="what is wanted, in a sentence or a paragraph")
    propose.add_argument("--id", help="the change's name (default: made from the brief's title)")
    propose.add_argument("--tier", choices=TIERS, help="how much ceremony (default: the model's call)")
    propose.add_argument("--no-input", action="store_true", help="ask no question: open points stay in the brief")
    propose.add_argument("--no-explore", action="store_true", help="read none of the repository's code")
    propose.add_argument("--with", dest="with_", action="append", default=[], metavar="PATH", help=WITH_HELP)
    propose.set_defaults(handler=_drafting(_propose))

    plan = commands.add_parser("plan", help="draft a change's tasks again, and its design where one is owed")
    plan.add_argument("id", help="the change")
    plan.add_argument(
        "--replace", action="store_true", help="draft anew although a task is ticked, or the design was edited"
    )
    plan.add_argument("--no-explore", action="store_true", help="read none of the repository's code for the plan")
    plan.add_argument("--with", dest="with_", action="append", default=[], metavar="PATH", help=WITH_HELP)
    plan.set_defaults(handler=_drafting(_planned))

    check = commands.add_parser("check", help="check a change's files against each other, as `approve` does")
    check.add_argument("id", help="the change")
    check.add_argument("--no-model", action="store_true", help="run the checks code makes, and call no model")
    check.set_defaults(handler=_drafting(_reviewed))

    verify = commands.add_parser("verify", help="judge the work done against each requirement of a change")
    verify.add_argument("id", help="the change")
    verify.add_argument(
        "--base",
        action="append",
        default=[],
        metavar="REF",
        help="the commit the work started from (default: the approval's); NAME=REF for another repository",
    )
    verify.add_argument(
        "--override", metavar="REASON", help="verify although a requirement is not shown met, and record why"
    )
    verify.set_defaults(handler=_drafting(_verified))

    smoke = commands.add_parser("smoke", help="run the triage stage alone, to prove an arm answers in a schema")
    smoke.add_argument("--model", help="the model for this run alone, in place of the arm's")
    smoke.add_argument("--request", default=SMOKE_REQUEST, help="the change request to size")
    smoke.add_argument("--check", action="store_true", help="say whether the arm is ready, and call no model")
    smoke.add_argument("--json", action="store_true", help="print the result as JSON")
    smoke.set_defaults(handler=_smoke)

    models = commands.add_parser("models", help="list the models the chosen arm serves: one request, no model call")
    models.add_argument("--json", action="store_true", help="print the list as JSON")
    models.set_defaults(handler=_models)

    login = commands.add_parser("login", help="log in to GitHub Copilot once, with GitHub's device flow")
    login.add_argument("--force", action="store_true", help="log in again although a token is cached")
    login.set_defaults(handler=_login)
    return parser


def main(argv: list[str]) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return EXIT_USAGE
    try:
        return handler(args)
    except NotYetError as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return EXIT_FINDINGS
    except (UsageError, GitError, *REFUSALS) as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except OSError as exc:  # a file held open, a folder that cannot be written: said, and never the code for findings
        where = f" {exc.filename}" if exc.filename else ""
        print(f"{PROG}: could not read or write{where}: {exc.strerror or exc}", file=sys.stderr)
        return EXIT_ENGINE


# The commands that call no model, and `approve`, which calls one only for a check a change still owes.


def _locked(handler: Callable[[argparse.Namespace], int]) -> Callable[[argparse.Namespace], int]:
    """`handler` run while this run holds the workspace's lock: one writer at a time."""

    def locked(args: argparse.Namespace) -> int:
        with lock_held(_workspace(args)):
            return handler(args)

    return locked


def _workspace(args: argparse.Namespace) -> Workspace:
    return Workspace.find(Path(args.root).absolute())


def _init(args: argparse.Namespace) -> int:
    """The `.spec` tree made, or found with `--refresh`; then the code read where it can be, a profile of the
    repository written, and the rules already true of the code drafted into the constitution while it is still the
    template. The tree is made first: no model, and no failure of one, ever leaves the person without it, and a
    first `init` ends well whatever the reading came to. A refresh owes the profile, and says where it wrote none;
    with `--no-explore` it writes only what needs no model and is missing, as the skill of a workspace made before it.
    """
    if args.refresh:
        workspace = _workspace(args)
    else:
        workspace = Workspace.init(_unheld(Path(args.root).absolute()))
        print(f"made      {workspace.shown(workspace.home)}")
    _skill(workspace)
    code = EXIT_OK
    if not args.no_explore:
        _load_env()
        with lock_held(workspace):
            kept, code = _described(workspace)
            _drafted(workspace, kept)
    later = f"; `{PROG} init --refresh` reads the code" if args.no_explore else ""
    print(f'next      keep what is true in constitution.md, then run `{PROG} propose "<what you want>"`{later}')
    return code if args.refresh else EXIT_OK


def _skill(workspace: Workspace) -> None:
    """How an assistant uses adk-spec, written where the repository has none: a refresh gives it to a workspace made
    before it. One that cannot be written is a line, never a failed `init`: found by the code review, a `.claude` that
    was a file or a link failed the command after the tree was made, and every refresh after it."""
    try:
        skill = write_skill(workspace.root)
    except (PathError, OSError) as exc:
        why = exc.strerror if isinstance(exc, OSError) and exc.strerror else exc
        print(f"skipped   {workspace.shown(workspace.root.joinpath(*SKILL_PARTS))}: {why}")
        return
    if skill is not None:
        print(f"wrote     {workspace.shown(skill)}")


def _unheld(root: Path) -> Path:
    """`root`, where no folder above it holds a workspace already: `init` there would make a second one, read only
    this folder, and every command run from here would find it instead of the real one."""
    try:
        above = Workspace.find(root)
    except WorkspaceError:
        return root
    if above.root == root:
        return root  # `Workspace.init` says it is there
    raise UsageError(f"{above.home} is already there, above this folder. `{PROG} init --refresh` reads the code again")


def _described(workspace: Workspace) -> tuple[list[Any], int]:
    """The repository's code read, and `profile.md` written from what was kept: the statements a rule may be
    drafted from, which are none where the reading ended early, and how a refresh ends. Each way the code cannot be
    read is one line. The engine is not loaded where there is nothing to read."""
    source = _source(workspace, {})
    if source is None or not source.paths:
        print("not read  no git repository here, or no file in it, to describe")
        return [], EXIT_USAGE
    from ..orchestration.explore import DESCRIBE, MAX_CALLS, ROLES
    from ..orchestration.models import require_ready
    from ..orchestration.stages import BRIEF_TEXT, TREE
    from ..orchestration.stages import CONSTITUTION as RULES

    if why := require_ready(roles=ROLES):
        print(f"not read  {why}. Once a model is set up, `{PROG} init --refresh` reads the code")
        return [], EXIT_USAGE
    print(f"reading   the code, to describe this repository: up to {MAX_CALLS} model calls. --no-explore skips it")
    # No profile and no deltas: a refresh reads the code afresh, not the profile it is about to replace.
    seed = {RULES: constitution_text(workspace), BRIEF_TEXT: DESCRIBE, TREE: source.tree()}
    found, failure = _reading(workspace, "init", None, seed, None, source)
    print(f"explored  {_explored_said(found, 0, failure)}")
    if not found.statements:
        return [], EXIT_ENGINE
    text = _found_text(workspace, PROFILE_HEADING, found, partial=failure, sections=PROFILE_SECTIONS)
    print(f"wrote     {workspace.shown(workspace.write_home(PROFILE, text))}")
    # A rule rests on what the review let stand: a reading it did not finish drafts none.
    return ([] if failure else found.statements), EXIT_OK


def _drafted(workspace: Workspace, statements: Sequence[Any]) -> None:
    """The rules already true of the code drafted into the constitution, only while it is still the template."""
    if workspace.drafted(drafted_rules(statements)):
        count = sum(one.kind == "convention" for one in statements)
        shown = workspace.shown(workspace.home / CONSTITUTION)
        print(f"drafted   {count} rule{'' if count == 1 else 's'} into {shown}: keep, edit or delete each")


def _new(args: argparse.Namespace) -> int:
    workspace = _workspace(args)
    tier = args.tier or workspace.config().default_tier
    folder = workspace.new_change(args.id, tier)
    print(f"made {workspace.shown(folder)}, a {tier} draft: write its brief.md, its deltas and its tasks.md")
    return EXIT_OK


def _prefix(change_id: str) -> str:
    return f"{ROOT_NAME}/{CHANGES}/{change_id}/"


def _from_root(change_id: str, found: list[Finding]) -> list[Finding]:
    """Findings about a change's files, each with its path from the repository's root."""
    return [held.model_copy(update={"path": _prefix(change_id) + (held.path or "")}) for held in found]


def _inside(change_id: str, found: list[Finding]) -> list[Finding]:
    """What `_from_root` gave, each with its path in the change's folder again."""
    prefix = _prefix(change_id)
    return [held.model_copy(update={"path": (held.path or "").removeprefix(prefix)}) for held in found]


@dataclass(frozen=True)
class Assessed:
    """A change as every command reads it."""

    loaded: LoadedChange
    #: Its findings, each with its path from the repository's root.
    findings: list[Finding]
    #: What its approval no longer covers.
    stale: list[str]
    #: What its check still owes an approval, as `check_blockers` gives it, pathed from the root too.
    unchecked: list[Finding]
    #: Whether the work changed since the change was verified.
    drifted: bool = False
    #: The fingerprint of each file of the change, as it was read for this assessment: what an approval records.
    files: dict[str, str] = field(default_factory=dict)
    #: Those, and the fingerprint of what a check reads beside them: what a check is current against.
    seen: dict[str, str] = field(default_factory=dict)

    @property
    def state(self) -> ChangeState:
        return self.loaded.change.state

    @property
    def step(self) -> Step:
        """What happens next with the change, and who makes it happen."""
        tasks = self.loaded.change.tasks or ()
        started = any(task.done for group in tasks for task in group.tasks)
        return next_step(
            self.state, self.findings, self.stale, check=self.unchecked, drifted=self.drifted, started=started
        )


def _assessed(workspace: Workspace, change_id: str, living: dict[str, Spec], *, drift: bool = True) -> Assessed:
    loaded = workspace.load_change(change_id)
    unreadable = set(workspace.capabilities()) - set(living)  # a spec that is there and does not read
    found = _from_root(change_id, findings_of(loaded, living, unreadable))
    files = approval_files(workspace.approval_texts(change_id))
    seen = {**files, **_beside(workspace, loaded.change, living)}
    state = loaded.change.state
    unchecked = _from_root(change_id, check_blockers(state, seen))
    stale, drifted = approval_stale(state, files), drift and _drifted(workspace, state)  # git is asked for drift
    return Assessed(loaded, found, stale, unchecked, drifted, files, seen)


def _beside(workspace: Workspace, change: Any, living: dict[str, Spec]) -> dict[str, str]:
    """The fingerprint of what a check reads beside a change's own files, by its path from the root: the rules of
    the repository, and the living spec of each capability the change touches. A check is of all of it: one that
    found something in the rules is stale once the rules change, as it is once a file of the change does."""
    seen = {f"{ROOT_NAME}/{CONSTITUTION}": sha256_of(constitution_text(workspace))}
    for capability in sorted(change.deltas):
        if capability in living:
            seen[f"{ROOT_NAME}/{SPECS}/{capability}/{SPEC_FILE}"] = sha256_of(render_spec(living[capability]))
    return seen


def _drifted(workspace: Workspace, state: ChangeState) -> bool:
    """Whether the work changed since a change was verified, or cannot be compared with what was: either is not
    what was judged. Asked of git for a verified change alone."""
    return _drift(workspace, state) is not False


def _drift(workspace: Workspace, state: ChangeState) -> bool | None:
    """Whether the work changed since a change was verified: its diff against the same commit is no longer the one
    that was judged. None where the two cannot be compared: a repository gone, or a commit a shallow clone lacks."""
    held = state.verification
    if state.status != "verified" or held is None:
        return False
    try:
        work = _sources(workspace, state.repositories).work(held.base, held.bases)
    except GitError, SourceError:
        return None
    # Or the fingerprint an older adk-spec recorded, of the diff as a stage is shown it: found by the code review,
    # every change it verified read as drifted after the upgrade.
    return held.diff != work.fingerprint and held.diff != sha256_of(work.text)


def _living(workspace: Workspace, refused: str) -> dict[str, Spec]:
    """The living specs, every one of which reads. `NotYetError` where one does not, its faults printed first: a spec
    that does not read would pass for a capability not yet there, and which requirements exist would be unknown."""
    living, unread = workspace.specs()
    if unread:
        _printed(unread)
        raise NotYetError(f"{refused}: a living spec does not read. Fix it first")
    return living


def _say_next(
    workspace: Workspace, change_id: str, living: dict[str, Spec], *, drift: bool = True, plan: str | None = None
) -> None:
    """The line every command that changes a change ends on: what comes next, read from the files as they now are.
    Without `drift`, git is not asked whether the work moved: `verify` has just measured it. A `plan` the step names
    is said as `plan` gives it, with the flags this run's plan goes on with: found by the cleanup review, a second
    wording of the step named a plan its holds refused. Where no approval covers the change's files, a person reads
    it before approving: its view, `reports/review.md`, is written again first."""
    assessed = _assessed(workspace, change_id, living, drift=drift)
    deltas = assessed.loaded.change.deltas
    # A draft, a strict one approved once among them, or an approved change edited since, owes an approval: its view
    # is written for the person who gives it. Found by the code review: a second approver read the view of before.
    owed = assessed.stale or assessed.state.status == "draft"
    if owed and deltas and (view := _view_written(workspace, change_id, deltas, living)):
        shown, overlaps = view
        print(f"review    {shown}: {review_said(deltas, overlaps)}")
    phrase = assessed.step.phrase
    print(f"next      {phrase.replace(f'`{PROG} plan {change_id}`', plan) if plan else phrase}")


def _view_written(
    workspace: Workspace, change_id: str, deltas: Mapping[str, Delta], living: Mapping[str, Spec]
) -> tuple[str, dict[str, list[str]]] | None:
    """The approver's view of a change written again: where it is, as shown, and the overlaps it names. None where it
    cannot be written, a file that will not open or a folder the path rules refuse: the view is an aid, and found by
    the code review, its fault failed commands whose work was done."""
    overlaps = _overlaps(workspace, change_id, deltas)
    try:
        path = workspace.write_report(change_id, REVIEW, render_review(change_id, deltas, living, overlaps))
    except OSError, WorkspaceError:
        return None
    return workspace.shown(path), overlaps


def _overlaps(workspace: Workspace, change_id: str, deltas: Mapping[str, Delta]) -> dict[str, list[str]]:
    """Each requirement this change modifies or removes that another open change modifies or removes too. Nothing
    where another change's delta will not open: the view is the approver's aid, and `archive` still stops."""
    own = {req.id for delta in deltas.values() for req in (*delta.modified, *delta.removed)}
    try:
        touched = workspace.touching(change_id)
    except OSError, WorkspaceError:
        return {}
    return {req_id: others for req_id, others in touched.items() if req_id in own}


def _of_specs(workspace: Workspace) -> tuple[dict[str, Spec], list[Finding]]:
    """The living specs that read, and every finding of the living specs, with its path from the root."""
    living, found = workspace.specs()
    for capability, spec in sorted(living.items()):
        path = f"{ROOT_NAME}/{SPECS}/{capability}/{SPEC_FILE}"
        found += [held.model_copy(update={"path": path}) for held in validate_spec(spec)]
    return living, found


def _printed(found: list[Finding]) -> None:
    for held in found:
        print(f"{held.severity} {held.code} {place(held)}  {held.message}")


def _validate(args: argparse.Namespace) -> int:
    workspace = _workspace(args)
    living, found = _of_specs(workspace)
    if (size := len(constitution_text(workspace))) > CONSTITUTION_MAX_CHARS:
        found.append(
            finding(
                "constitution.long",
                f"The constitution holds {size:,} characters, past {CONSTITUTION_MAX_CHARS:,}. Every stage of every "
                "run reads it: keep the rules, and move the rest elsewhere.",
                path=f"{ROOT_NAME}/{CONSTITUTION}",
            )
        )
    for change_id in [args.id] if args.id else workspace.changes():
        try:
            state = workspace.state(change_id)
        except WorkspaceError as exc:  # one change whose state does not read stops no other's check
            if args.id:
                raise
            unread = workspace.shown(workspace.home / CHANGES / change_id / STATE_FILE)
            found.append(finding("change.unreadable", str(exc), path=unread))
            continue
        if state.status != "archived":  # folded in, an archived change's delta has no base now: nothing to check
            assessed = _assessed(workspace, change_id, living, drift=False)
            found += assessed.findings + _gated(workspace, assessed)
    found += evidence_findings(workspace, living)  # notes: a requirement whose proving lines are gone from the code
    stops = failed(found, strict=args.strict)
    if args.json:
        print(json.dumps({"findings": [held.model_dump() for held in found], "failed": stops}, indent=2))
        return EXIT_FINDINGS if stops else EXIT_OK
    github = os.environ.get("GITHUB_ACTIONS") == "true"
    # GitHub reads no command in the plain lines: found by the code review, a path holding a line break could have it
    # read one, and switch the annotations off.
    token = os.urandom(16).hex()
    if github:
        print(f"::stop-commands::{token}")
    _printed(found)
    errors = sum(held.severity == "ERROR" for held in found)
    warnings = sum(held.severity == "WARNING" for held in found)
    print(f"{errors} error{'' if errors == 1 else 's'}, {warnings} warning{'' if warnings == 1 else 's'}")
    if github:
        print(f"::{token}::")
        _annotated(workspace, found, failed=stops)
    return EXIT_FINDINGS if stops else EXIT_OK


def _gated(workspace: Workspace, assessed: Assessed) -> list[Finding]:
    """What a merge gate reads of a change beyond its own findings, `lifecycle.merge_gate`, pathed from the root."""
    state = assessed.state
    try:
        drift = _drift(workspace, state)
    except ConfigError, NotTextError, OSError:  # a config that does not read: the gate cannot compare, goes on
        drift = None
    found = merge_gate(state, assessed.stale, drift, record=STATE_FILE)
    return _from_root(state.id, found)


def _from_the_top(workspace: Workspace, found: Sequence[Finding]) -> list[Finding]:
    """Findings with their paths from the checkout's top, as GitHub reads an annotation's: found by the code review,
    a `.spec/` below the top was annotated on files GitHub could not find."""
    root = workspace.root.resolve()
    top = Path(os.environ.get("GITHUB_WORKSPACE") or root).resolve()
    if root == top or not root.is_relative_to(top):  # at the top, or not under it: the paths are left as they are
        return list(found)
    below = root.relative_to(top).as_posix()
    return [held.model_copy(update={"path": f"{below}/{held.path}"}) if held.path else held for held in found]


def _annotated(workspace: Workspace, found: Sequence[Finding], *, failed: bool) -> None:
    """In GitHub Actions: each finding as an annotation on its line, and the summary on the run's page, where the
    runner names a file for it. A summary that cannot be written is left out: the annotations are said."""
    found = _from_the_top(workspace, found)
    for line in annotation_lines(found):
        print(line)
    if target := os.environ.get("GITHUB_STEP_SUMMARY"):
        with contextlib.suppress(OSError):
            append_text(Path(target), step_summary(found, failed=failed))


#: How `status` groups changes: by who makes the next step happen.
GROUPS = (("you", "Waiting on you"), ("run", "Ready to run"), ("done", "Done"))


def _status(args: argparse.Namespace) -> int:
    workspace = _workspace(args)
    living, _found = workspace.specs()
    rows = []
    for change_id in workspace.changes():
        try:
            if not args.all and workspace.state(change_id).status == "archived":  # history, which is not read
                continue
            assessed = _assessed(workspace, change_id, living)
        except WorkspaceError as exc:  # one change that does not read stops no other: it is named, and why
            rows.append({"id": change_id, "tier": "-", "status": "unread", "actor": "you", "next": str(exc)})
            continue
        state, step = assessed.state, assessed.step
        row = {"id": change_id, "tier": state.tier, "status": state.status, "actor": step.actor, "next": step.phrase}
        rows.append(row)
    if args.json:
        print(json.dumps({"changes": rows}, indent=2))
    elif not rows:
        print(f'no open changes: run {PROG} propose "<what you want>"')
    else:
        width = max(len(row["id"]) for row in rows)
        groups = [(heading, [row for row in rows if row["actor"] == actor]) for actor, heading in GROUPS]
        for at, (heading, held) in enumerate(group for group in groups if group[1]):
            print(("\n" if at else "") + heading)
            for row in held:
                print(f"  {row['id']:<{width}}  {row['tier']:<8}  {row['status']:<8}  {row['next']}")
    if not args.json:
        _suspects_said(workspace, living)
    return EXIT_OK


def _suspects_said(workspace: Workspace, living: Mapping[str, Spec]) -> None:
    """One line for each capability holding a requirement whose evidence is gone from the code: `validate` names
    them."""
    gone = Counter(held.path for held in evidence_findings(workspace, living) if held.code == "spec.evidence-gone")
    for path, count in sorted(gone.items()):
        capability = Path(path or "").parent.name
        print(f"{capability}: {count} requirement{'' if count == 1 else 's'} suspect ({PROG} validate lists them)")


def _rebase(args: argparse.Namespace) -> int:
    """Record the fingerprint each modified or removed requirement has in the living spec now. New bases void an
    approval, since it was given against the old ones; unchanged bases leave everything as it was."""
    workspace = _workspace(args)
    loaded = workspace.load_change(args.id)
    state = loaded.change.state
    if state.status == "archived":
        print(f"{PROG}: `{args.id}` is archived already: nothing to rebase", file=sys.stderr)
        return EXIT_FINDINGS
    living = _living(workspace, f"`{args.id}` is not rebased")  # or every base on an unread spec would be dropped
    if unread := [
        held for held in loaded.problems if _of_a_delta(held)
    ]:  # found by the code review: a delta not read held no base, all dropped
        _printed(_from_root(args.id, unread))
        raise NotYetError(f"`{args.id}` is not rebased: a delta does not read, and its bases would be dropped")
    held = capture_bases(loaded.change.deltas, living)
    for req_id in sorted(held):
        was = state.bases.get(req_id)
        print(f"{req_id}  {'recorded' if was is None else 'unchanged' if was == held[req_id] else 'was stale'}")
    for req_id in sorted(
        set(state.bases) - set(held)
    ):  # the delta no longer changes it, or the spec no longer holds it
        print(f"{req_id}  dropped")
    if held == state.bases:
        print("nothing to record: every base stands")
    else:
        workspace.save_state(reopened(state, bases=held))
        if state.approval is not None:
            print("the approval is void: the bases were recorded anew")
    _say_next(workspace, args.id, living)  # it ends on what comes next, as every command that moves a change does
    return EXIT_OK


def _based(workspace: Workspace, change_id: str, living: dict[str, Spec]) -> None:
    """A base recorded for each requirement the change modifies or removes that has none: what `rebase` records
    for a change that was never based, so that an approval needs no command before it. A recorded base is left as
    it is. Each one recorded is said: it is what the requirement says now, which a delta written some time ago may
    not have been written against."""
    loaded = workspace.load_change(change_id)
    state = loaded.change.state
    if state.status != "archived" and (missing := missing_bases(state, loaded.change.deltas, living)):
        workspace.save_state(state.model_copy(update={"bases": {**state.bases, **missing}}))
        them = "it" if len(missing) == 1 else "them"
        print(f"based     {', '.join(sorted(missing))} as the living spec holds {them} now")


def _checked_first(
    workspace: Workspace, change_id: str, living: dict[str, Spec], assessed: Assessed, override: str | None
) -> _Checked | None:
    """The check an approval makes of a change whose check is missing or stale, as `check` makes it. Where it cannot
    be made, no provider being ready or more than a model is given to read, the refusal names the way that needs
    none; or nothing, where a model's check found what blocks and the person's reason, on a tier that takes one,
    sets that aside: they were shown it. Found by the code review, twice: else no such change was ever approved."""
    _load_env()
    try:
        return _check_made(workspace, change_id, living, assessed, no_model=False)
    except (UsageError, ContextTooLargeError) as exc:
        tier, held = assessed.state.tier, model_holds(assessed.state, assessed.seen)
        if held and override:  # a tier that takes no reason refused one before this
            print(f"note      the check was not made again: {exc}. Your reason sets aside what the model's check found")
            return None
        # Found by the code review: `check --no-model` was named where it refuses, a model's finding standing.
        way = f"or run `{PROG} check {change_id} --no-model` and approve again"
        if held:
            aside = ", or set it aside with --override and your reason" if DEMANDS[tier].override else ""
            way = f"then approve again{aside}: only a model clears what a model found"
        raise UsageError(f"{exc}. `approve` checks a {tier} change first: put that right, {way}") from exc


def _said_check(made: _Checked, state: ChangeState) -> None:
    """The check an approval made, said: what blocks, how many findings, what was left out, what it cost."""
    stopped = blocking(state, made.findings)
    _printed(stopped)
    count = len(made.findings)
    print(f"checked   {made.report}: {count} finding{'' if count == 1 else 's'}, {len(stopped)} blocking")
    if made.dropped:  # found by the fourth audit: said by `check` alone, never by the check `approve` makes
        print(f"note      {left_out(made.dropped)}")
    print(f"tokens    {_spent(made.ledger)}")


def _refused(change_id: str, blockers: list[Finding]) -> int:
    """An approval refused, by the findings printed above it, which say what to do. Found by the third audit: a
    count of its own, "1 findings block it", read against the check's "2 blocking"."""
    _printed(blockers)
    said = "the findings above block it" if len(blockers) > 1 else "the finding above blocks it"
    print(f"{PROG}: `{change_id}` is not approved: {said}", file=sys.stderr)
    return EXIT_FINDINGS


def _approve(args: argparse.Namespace) -> int:
    """An approval, with what it needs done first: a base recorded where one is missing, and the check made where
    none is current. A person decides once; the tool's own work is no step of theirs."""
    workspace = _workspace(args)
    living = _living(workspace, f"`{args.id}` is not approved")  # coverage is unknown while a spec is unread
    _based(workspace, args.id, living)
    assessed = _assessed(workspace, args.id, living)
    demands = DEMANDS[assessed.state.tier]
    if args.override and not demands.override:
        raise UsageError(f"a {assessed.state.tier} change sets no blocking finding aside: fix it, then approve again")
    by = _approver(args, assessed)  # a name that cannot approve is refused before anything is spent
    # What the files themselves block comes first: no model is asked about files that are going to change.
    if blockers := approve_blockers(assessed.state, assessed.findings, strict=args.strict):
        return _refused(args.id, blockers)
    first = approval_checks_first(assessed.unchecked)
    made = _checked_first(workspace, args.id, living, assessed, args.override) if first else None
    if made is not None:
        if made.failure:
            return _unfinished(f"the check did not finish, and nothing was approved: {made.failure}", made.ledger)
        _said_check(made, assessed.state)
        assessed = _assessed(workspace, args.id, living)
    aside = first and made is None  # a model's check that could not be made again, set aside by a reason
    # A reason sets aside only what a person was shown: a check recorded before this run, never one it made.
    if not aside and (blockers := check_stops(assessed.unchecked, override=bool(args.override) and not first)):
        if args.override and first:
            print(
                f"{PROG}: --override was not applied: this run made the check, so read what it found first, then "
                "approve again with --override",
                file=sys.stderr,
            )
        return _refused(args.id, blockers)
    files = assessed.files  # as they were read for the assessment that found the check current: no later read
    at = datetime.now(UTC).isoformat(timespec="seconds")
    # A reason is recorded only where it set something aside: a blocking finding of the check.
    reason = args.override if aside or any(held.code == "check.blocking" for held in assessed.unchecked) else None
    began, commit = _where_work_begins(workspace, assessed)
    held = approve(assessed.state, files=files, by=by, at=at, override=reason, commit=commit, others=began)
    edited = edited_drafts(assessed.state, files)
    workspace.save_state(held)
    if held.verification is None:  # what a verification said and left to do was of other files, or there was none
        _aids_written(workspace, args.id, dict.fromkeys((REMAINING, "summary.md")))
    _said_approved(held, by, len(files))
    if overlaps := _overlaps(workspace, args.id, assessed.loaded.change.deltas):
        named = "; ".join(f"{req_id} ({', '.join(others)})" for req_id, others in sorted(overlaps.items()))
        print(f"note      also changed by another open change: {named}. The second to archive is stopped: rework it")
    if edited:
        print(
            f"lessons   {', '.join(edited)} edited since drafted: say what you corrected in one line in "
            f".spec/{LESSONS}, and later drafts follow it"
        )
    _say_next(workspace, args.id, living)
    return EXIT_OK


def _approver(args: argparse.Namespace, assessed: Assessed) -> str:
    """Who approves: `--by`, or the account's name. Refused where that name gave the change its first approval and
    another name owes the second."""
    try:
        by = args.by or getpass.getuser()
    except OSError as exc:  # an account with no name, as in a container run under a bare user id
        raise UsageError("this account has no name: name the approver with --by") from exc
    if refused := approver_blockers(assessed.state, assessed.stale, by):
        raise NotYetError(refused[0])
    return by


def _where_work_begins(workspace: Workspace, assessed: Assessed) -> tuple[dict[str, str], str | None]:
    """What each repository of a change has checked out, where this approval approves it: where its work begins. The
    first of two names approves nothing yet, and asks no repository."""
    state = assessed.state
    if DEMANDS[state.tier].approvers > 1 and first_of_two(state, assessed.stale) is None:
        return {}, None
    return _began(workspace, state), _commit(workspace)


def _said_approved(held: ChangeState, by: str, count: int) -> None:
    """What an approval says, in one line: the first of two names, or the approval, with the first name where it is
    the second. Who approves next is the next line's to say."""
    if held.status != "approved":
        said = f"once, by {by}"
    else:
        said = f"by {by}" + (f", after {held.approval.by}" if held.approval and held.approval.second else "")
    print(f"approved `{held.id}` {said}: {count} files recorded")


def _began(workspace: Workspace, state: ChangeState) -> dict[str, str]:
    """Where the work begins in each other repository of a change that has no starting point recorded yet and is
    here: the commit it has checked out. A recorded one is never moved, so none is asked after."""
    unrecorded = {name: path for name, path in state.repositories.items() if name not in state.base_commits}
    if not unrecorded or (source := _source(workspace, unrecorded)) is None:
        return {}
    for missing in source.missing:
        print(f"left out  {missing}: its starting point is not recorded")
    began = {name: commit for name, commit in source.commits().items() if commit}
    for name, commit in began.items() if state.base_commit else ():  # a later approval: the work may have begun
        print(
            f"recorded  {name} starts at {commit[:12]}, after the first approval: where its work began before, "
            f"give verify --base {name}=REF"
        )
    return began


def _commit(workspace: Workspace) -> str | None:
    """The commit checked out where an approval is made, or nothing: no repository here, no commit yet, or no git
    to ask."""
    try:
        return head(workspace.root)
    except GitError:
        return None


def _archive(args: argparse.Namespace) -> int:
    """Every capability's merge is computed before any file is written, and the merged specs and the change's state
    are then written as one set: all of them, or none as far as the file system allows."""
    workspace = _workspace(args)
    living, of_specs = workspace.specs()
    assessed = _assessed(workspace, args.id, living)
    loaded, state = assessed.loaded, assessed.state
    if blockers := archive_blockers(state, assessed.stale, drifted=assessed.drifted):
        for sentence in blockers:
            print(f"{PROG}: {sentence}", file=sys.stderr)
        return EXIT_FINDINGS
    refused = [*of_specs]  # a living spec that does not read would be taken for a capability not yet there
    merged: dict[str, Spec] = {}
    for capability, delta in sorted(loaded.change.deltas.items()):
        path = f"{ROOT_NAME}/{CHANGES}/{args.id}/{SPECS}/{capability}/{SPEC_FILE}"
        try:
            merged[capability] = apply_delta(living.get(capability), delta, bases=state.bases, change=state.id)
        except MergeError as exc:
            refused += [held.model_copy(update={"path": path}) for held in exc.findings]
    if refused:
        _printed(refused)
        print(f"{PROG}: `{args.id}` is not archived, and no spec was written", file=sys.stderr)
        if any(held.code == "delta.base-stale" for held in refused):
            view = _view_written(workspace, args.id, loaded.change.deltas, living)
            shown = view[0] if view else "the current requirement"
            print(
                f"{PROG}: the living spec changed after this delta was based on it: read {shown}, update the delta, "
                f"then run `{PROG} rebase {args.id}` and approve again",
                file=sys.stderr,
            )
        return EXIT_FINDINGS
    # The lines that proved each requirement, beside its living spec: the next change and `validate` read them.
    files, left = evidence_folded(workspace, state, loaded.change.deltas)
    if (logged := _logged(workspace, args.id, loaded.change.deltas)) is None:
        left.append(workspace.shown(workspace.home / CHANGELOG))
    else:
        files[CHANGELOG] = logged
    workspace.write_specs(merged, state=state.model_copy(update={"status": "archived"}), files=files)
    print(f"archived `{args.id}`: folded into {', '.join(sorted(merged)) or 'no spec'}")
    for shown in left:
        print(f"kept      {shown}: it would not read or be written, a link or not UTF-8: nothing was added")
    return EXIT_OK


def _logged(workspace: Workspace, change_id: str, deltas: Mapping[str, Delta]) -> str | None:
    """The changelog with this change's entry first; None where the one there does not read, which is left as it is."""
    path = workspace.home / CHANGELOG
    if not workspace.writable(CHANGELOG):  # a link the archive's write would refuse, and stop on
        return None
    try:
        text = read_text(path) if path.is_file() else None
    except NotTextError, OSError:
        return None
    return with_entry(text, changelog_entry(change_id, date.today().isoformat(), deltas))  # the person's day


# The commands that call a model, or log in to one.


def _env_file() -> Path | None:
    """The `.env` a run reads: the checkout's own, told by the `pyproject.toml` beside the package. An installed
    copy has none beside it and reads the shell alone, never a file that happens to stand near its packages."""
    return CHECKOUT / ".env" if (CHECKOUT / "pyproject.toml").is_file() else None


#: The names the checkout's `.env` added to this process's environment: adk-spec's own, kept from a project's tests.
_FROM_ENV_FILE: set[str] = set()


def _load_env() -> None:
    """The checkout's `.env` read into the environment, the shell winning over the file."""
    path = _env_file()
    if path is not None:
        _FROM_ENV_FILE.update(_loaded(path))


def _loaded(path: Path) -> set[str]:
    """`.env` at `path` read into the environment, never over a variable already set: the names it added."""
    from dotenv import load_dotenv

    before = set(os.environ)
    try:
        load_dotenv(path, override=False, encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise UsageError(f"{path} is not UTF-8. Save it as UTF-8: Windows PowerShell 5.1's `>` writes UTF-16") from exc
    return set(os.environ) - before


def _line() -> str:
    """One line a person typed, or nothing where the input is over, closed, or holds bytes that are no text."""
    try:
        return sys.stdin.readline()
    except OSError, ValueError:  # a closed stream; a `UnicodeDecodeError` is a `ValueError`
        return ""


def _answered(questions: list[dict[str, Any]]) -> list[str]:
    """A round of questions put to the person on the terminal, one at a time: the answer to each, in their order.
    A line is the answer; `=` takes the suggestion; an empty line leaves the point open; the end of the input, or
    no input at all, answers every question still to come with nothing."""
    points = "1 point" if len(questions) == 1 else f"{len(questions)} points"
    print(f"The brief leaves {points} open. A line answers. `=` takes the suggestion, and `yes` one that says yes.")
    print("An empty line leaves the point open.")
    answers: list[str] = []
    ended = sys.stdin is None  # a process started with no terminal and no pipe
    for number, question in enumerate(questions, 1):
        print(f"{number}. {plain(question['question'])}")
        print(f"   suggested: {plain(question['suggested']) or '(none)'}", flush=True)
        line = "" if ended else _line()
        ended = ended or line == ""  # no line at all: the input is over
        typed = line.strip()
        # "yes" takes a suggestion that is itself a yes, as the brief words them. Found by review: taken for any
        # suggestion, "No, keep it" was stored for a person's yes. An answer is read beside its question, so a plain
        # "yes" always says what the person meant.
        takes = typed == "=" or (
            typed.casefold() in ("y", "yes") and question["suggested"].casefold().startswith("yes")
        )
        if typed == "=" and not question["suggested"]:
            print("   nothing is suggested: the point stays open")
        answers.append(question["suggested"] if takes else typed)
    return answers


def _ran(app: Any, seed: dict[str, Any], prompt: str) -> Any:
    """One run of `app`, with the engine's own log quieted for its length: ADK logs a failed node with its whole
    traceback, and the command says the failure in one line."""
    import asyncio
    import logging

    from ..orchestration.run import run_seeded

    engine_log = logging.getLogger("google_adk")
    level = engine_log.level
    engine_log.setLevel(logging.CRITICAL)
    try:
        return asyncio.run(run_seeded(app, state=seed, prompt=prompt))
    finally:
        engine_log.setLevel(level)


def _on_a_terminal() -> bool:
    """Whether a person is watching the error stream. Progress is for them alone: a pipe and a script read what
    they read before."""
    stream = sys.stderr
    return stream is not None and stream.isatty()


def _working(stage: str, again: bool) -> None:
    """One line a model call, as it starts: a command that works for a minute is not silent for a minute."""
    print(f"working   {stage}{', again' if again else ''}", file=sys.stderr, flush=True)


@dataclass
class _Kept:
    """What a command says for its recording: the plugin that hears its calls, the change it is about, and how it
    ended."""

    recorder: Any
    change: str | None
    outcome: str = ""


@contextlib.contextmanager
def _recording(workspace: Workspace, command: str, change: str | None) -> Generator[_Kept]:
    """A command's model calls, kept when it ends, however it ends: well, with a failure, or interrupted. A
    recording that cannot be written costs the command nothing."""
    from ..orchestration.models import serving
    from ..orchestration.recorder import Recorder

    keep = workspace.config().keep_runs
    kept = _Kept(Recorder(heard=_working if _on_a_terminal() else None), change)
    try:
        yield kept
    except KeyboardInterrupt:
        kept.outcome = "interrupted"
        raise
    finally:
        calls = kept.recorder.calls
        if calls:
            at = datetime.now(UTC).isoformat(timespec="seconds")
            outcome = kept.outcome or "failed"
            held = Recording(command=command, change=kept.change, at=at, model=serving(), outcome=outcome, calls=calls)
            with contextlib.suppress(OSError):
                write_run(workspace, held, keep=keep)


def _spent(ledger: Any) -> str:
    """What a command's stages spent, from its ledger: each stage with its calls, then the total."""
    stages = ", ".join(
        f"{name} {row.total:,} in {row.calls} call{'' if row.calls == 1 else 's'}" for name, row in ledger.spent.items()
    )
    return f"{stages}: {ledger.total.total:,} total" if stages else "nothing"


def _propose(args: argparse.Namespace, workspace: Workspace) -> int:
    """`propose`, under the lock from its first read: found by an outside audit, a change read before the lock was
    undone in silence by the revision's older copy, where a command ended in between."""
    change = _revising(workspace, args.id)  # an open change that `--id` names is revised, not taken
    if args.id and change is None:
        workspace.free(args.id)  # a name that cannot be taken is refused before anything is spent
    args.tier = _tier_of(args, change)  # decided once, here: the run starts at the brief where it is known
    # Every role of the whole command, asked before anything is spent. A known tier is not asked of triage.
    from ..orchestration.explore import ROLES as READING
    from ..orchestration.models import require_ready

    drafting = ("brief", "deltas", "design", "tasks", *(() if args.no_explore else READING))
    if why := require_ready(roles=drafting if args.tier else ("triage", *drafting)):
        raise UsageError(why)
    return _proposed(args, workspace, change)


def _drafting(handler: Callable[[argparse.Namespace, Workspace], int]) -> Callable[[argparse.Namespace], int]:
    """`handler` for a command that calls a model on one change: the checkout's `.env` read, and the workspace held
    under its lock for the length of the command."""

    def held(args: argparse.Namespace) -> int:
        _load_env()
        workspace = _workspace(args)
        with lock_held(workspace):
            return handler(args, workspace)

    return held


def _asked(
    workspace: Workspace,
    command: str,
    change_id: str | None,
    build: Callable[[Any, Any], Any],
    seed: dict[str, Any],
    read: Callable[[dict[str, Any]], Any],
    *,
    ledger: Any = None,
) -> tuple[Any, Any, Any, str | None]:
    """One recorded run of an app that `build` makes from the command's ledger and its recorder: the run, the
    answer `read` finds in its state, the ledger, and the failure where there is no answer to use. A command that
    makes more than one pass hands its own `ledger` on, so the ceiling is the command's and not a pass's."""
    from ..orchestration.gate import FAILURE
    from ..orchestration.plugins import UsageLedger

    if ledger is None:
        ledger = UsageLedger(workspace.config().max_tokens or None)
    with _recording(workspace, command, change_id) as kept:
        run = _ran(build(ledger, kept.recorder), seed, command)
        _learned(workspace, run.state)
        answer = read(run.state)
        failure = run.state.get(FAILURE) or run.failure or (answer if isinstance(answer, str) else None)
        kept.outcome = f"failed: {failure}" if failure else "answered"
    return run, (None if failure else answer), ledger, (str(failure) if failure else None)


def _learned(workspace: Workspace, state: Mapping[str, Any]) -> None:
    """What a run's gates sent back that the next try put right, noted in the lessons file. A file that cannot be
    read or written costs the command nothing."""
    from ..orchestration.gate import SENT_BACK

    if sent_back := state.get(SENT_BACK):  # a linked or unreadable file is refused, and costs the run nothing
        with contextlib.suppress(OSError, NotTextError, PathError, WorkspaceError):
            workspace.learn(sent_back)


def _unfinished(sentence: str, ledger: Any) -> int:
    """How a command ends where its model pass gave no answer to use: the sentence, what was spent, and the
    engine's code."""
    print(f"{PROG}: {sentence}", file=sys.stderr)
    print(f"tokens    {_spent(ledger)}")
    return EXIT_ENGINE


def _deltas_text(change: Any) -> str:
    """A change's deltas as a stage reads them: each as its file, in the order of their capabilities."""
    return "\n".join(render_delta(delta) for _capability, delta in sorted(change.deltas.items()))


#: What `--with` says in the help.
WITH_HELP = "another repository the change spans, read with it: PATH, or NAME=PATH (as often as needed)"


def _sources(workspace: Workspace, repositories: Mapping[str, str], *, installed: bool = False) -> Source:
    """The repository's files, as git lists them once for a command, less what a person excluded, and those of the
    other repositories a change names: what a stage is shown the names of, what a reading of the code is made
    through, and what the work is read from. `GitError` where git cannot list them; `SourceError` for a repository
    that can never be read beside this one."""
    return Source.of(workspace.root, exclude=workspace.config().exclude, others=repositories, installed=installed)


def _source(workspace: Workspace, repositories: Mapping[str, str], *, installed: bool = False) -> Source | None:
    """`_sources`, or None where there is no repository here, or no git to ask: a plan is drafted without it."""
    try:
        return _sources(workspace, repositories, installed=installed)
    except GitError:
        return None


def _optional(workspace: Workspace, read: Callable[[Workspace], str], name: str) -> str | None:
    """Optional material as a stage reads it, the profile or the lessons; None where the file is no text, which is
    said, and stops nothing. A person edits it by hand, and may have saved it in another encoding."""
    try:
        return read(workspace)
    except NotTextError:
        print(f"left out  {workspace.shown(workspace.home / name)} is not UTF-8: no stage reads it")
    except OSError as exc:  # found by the code review: the chat left it out, and `propose` stopped on it
        print(f"left out  {workspace.shown(workspace.home / name)} could not be opened: {exc.strerror or exc}")
    return None


def _with_checked(workspace: Workspace, given: Sequence[str], held: Mapping[str, str], here: Path) -> dict[str, str]:
    """A change's repositories, `held`, with each one `--with` names now: its path read from `here`, the folder the
    command was told to work from, as a shell reads one, and recorded from the workspace's root. Each named now is
    checked before anything is spent: `SourceError` for one that can never be read beside this one, `UsageError`
    for one that is not there at all, which a typo would otherwise cost a whole run to find."""
    named = {name: _as_recorded(workspace, here, path) for name, path in repositories_named(given, {}).items()}
    if named and (source := _source(workspace, named)) is not None and source.missing:
        raise UsageError(f"--with names no repository adk-spec can read: {source.missing[0]}")
    return {**held, **named}


def _as_recorded(workspace: Workspace, here: Path, path: str) -> str:
    """A path a person typed, read from `here`, as a change records it: from the workspace's root, with forward
    slashes. One on another drive, which no path from the root reaches, stays whole."""
    target = Path(path) if Path(path).is_absolute() else here.absolute() / path
    try:
        return Path(os.path.relpath(target, workspace.root)).as_posix()
    except ValueError:
        return target.as_posix()


def _said_sources(source: Source | None, repositories: Mapping[str, str]) -> None:
    """Each other repository a command reads, and each it cannot: a change's state is a file a teammate may commit,
    and nothing is read on the strength of it unsaid."""
    for name in source.names if source else ():
        print(f"with      {name} from {repositories[name]}")
    for missing in source.missing if source else ():
        print(f"left out  {missing}")


#: A ticked box of a task list, wherever its line stands: read in the text of a list that no longer parses.
_TICKED = re.compile(r"(?m)^\s*-\s*\[[xX]\]")


def _ticked(workspace: Workspace, change: Change) -> int:
    """How many of a change's tasks are ticked. A list off its grammar reads as none: its boxes are counted in its
    text."""
    if change.tasks is None:
        return len(_TICKED.findall(workspace.approval_texts(change.state.id).get(TASKS_FILE, "")))
    return sum(task.done for group in change.tasks for task in group.tasks)


def _plannable(
    change_id: str, replace: bool, workspace: Workspace, assessed: Assessed, of_specs: list[Finding]
) -> Brief:
    """The brief of a change that is to be planned now. `NotYetError` where it is not: it is no draft, work on its
    task list has begun and replacing it was not asked for, or what the tasks are drafted from does not read."""
    change, state = assessed.loaded.change, assessed.state
    if state.status != "draft":  # new tasks would void what was approved
        way = "Propose a new change for what is still wanted"  # `propose --id` refuses a change whose work was judged
        if state.status == "approved":
            way = (
                f'To change what it asks, run `{PROG} propose "<what changes>" --id {change_id}`; to add a task, write '
                "it in tasks.md, then approve it again"
            )
        raise NotYetError(f"`{change_id}` is {state.status}: a plan is drafted while a change is a draft. {way}")
    started = _ticked(workspace, change)
    if started and not replace:  # work has begun on this list: it is not thrown away unasked
        raise NotYetError(
            f"`{change_id}` has {started} of its tasks ticked. A new plan would replace the list: run "
            f"`{PROG} plan {change_id} --replace` if that is meant"
        )
    if of_specs:  # a task may serve a requirement of any living spec: which exist is unknown while one is unread
        _printed(of_specs)
        raise NotYetError(f"`{change_id}` is not planned: a living spec does not read. Fix it first")
    # What must be right before tasks are worth drafting: everything but the tasks themselves.
    blocking = plan_blockers(assessed.findings)
    if blocking or change.brief is None:
        _printed(blocking)
        raise NotYetError(f"`{change_id}` is not planned: fix the errors above first")
    return change.brief


@dataclass
class _Planned:
    """A plan as it was drafted: each file written, and whether it replaced one; the ledger of the model's pass;
    and why the pass did not end well, where it did not, in which case nothing was written."""

    written: list[tuple[Path, bool]] = field(default_factory=list)
    ledger: Any = None
    failure: str | None = None
    #: What the reading of the code before it came to, in the words a person is shown; empty where none was made.
    explored: str = ""


def _plan_made(
    workspace: Workspace,
    change_id: str,
    specs: dict[str, Spec],
    of_specs: list[Finding],
    *,
    replace: bool,
    ledger: Any = None,
    explore: bool = True,
    repositories: Mapping[str, str] | None = None,
    lessons: str | None = None,
) -> _Planned:
    """A draft change's tasks drafted, and first its design where the brief owes one, from what a reading of the
    repository's code found: one is made first where `explore` allows it and the change has no `context.md` yet.
    What `plan` does, and what `propose` does once its change is written, on the ledger of the whole command. It
    prints only what stops it: `NotYetError` where the change cannot be planned now, with the findings that say
    why."""
    assessed = _assessed(workspace, change_id, specs)
    change, state = assessed.loaded.change, assessed.state
    brief = _plannable(change_id, replace, workspace, assessed, of_specs)
    from ..orchestration.models import require_ready

    # An owed design is drafted, unless a person wrote or edited the one that stands and replacing it was not asked.
    drafts_design = state.needs_design and (replace or not _persons_design(workspace, change_id, state))
    roles = ("design", "tasks") if drafts_design else ("tasks",)
    if why := require_ready(roles=roles):
        raise UsageError(why)
    from ..orchestration.graph import build_plan_app
    from ..orchestration.plugins import UsageLedger
    from ..orchestration.stages import BRIEF_TEXT, CONTEXT_TEXT, DELTAS_TEXT, LESSONS_TEXT, LIVING, PROFILE_TEXT, TREE
    from ..orchestration.stages import CONSTITUTION as RULES
    from ..orchestration.stages.design import read_design
    from ..orchestration.stages.tasks import DESIGN_TEXT, read_tasks

    held = state.repositories if repositories is None else repositories
    source = _source(workspace, held)
    _said_sources(source, held)
    seed = {
        RULES: constitution_text(workspace),
        BRIEF_TEXT: render_brief(brief),
        DELTAS_TEXT: _deltas_text(change),
        LIVING: living_text(specs, sorted(change.deltas)),
        TREE: source.tree() if source else "",
        PROFILE_TEXT: _optional(workspace, profile_text, PROFILE) or "",
        LESSONS_TEXT: (_optional(workspace, lessons_text, LESSONS) or "") if lessons is None else lessons,
    }
    if change.design and not drafts_design:  # a design a person wrote, or one the change does not owe
        seed[DESIGN_TEXT] = change.design.strip()
    serves = {"owed": tasked(change.deltas), "nameable": nameable(change.deltas, specs)}
    if ledger is None:  # one ceiling for the reading and the drafting: they are one command's
        ledger = UsageLedger(workspace.config().max_tokens or None)
    said, context = _read_code(workspace, change_id, seed, ledger, held) if explore else ("", None)
    seed[CONTEXT_TEXT] = context_text(workspace, change_id)
    read = [(context, False)] if context else []

    def build(ledger: Any, recorder: Any) -> Any:
        return build_plan_app(design=drafts_design, ledger=ledger, recorder=recorder, **serves)

    run, tasks, ledger, failure = _asked(workspace, "plan", change_id, build, seed, read_tasks, ledger=ledger)
    if failure:
        return _Planned(ledger=ledger, failure=failure, explored=said)
    files = {TASKS_FILE: render_tasks(to_tasks(tasks))}
    design = read_design(run.state) if drafts_design else None
    if design is not None and not isinstance(design, str):
        files = {DESIGN_FILE: render_design(design), **files}  # the design first: it is what a person reads first
    folder = workspace.home / CHANGES / change_id
    there = {name for name in files if (folder / name).is_file()}
    workspace.rewrite_change(state, files)  # the plan and the state as one set, the plan recorded as drafted
    written = [(folder / name, name in there) for name in files]
    return _Planned([*read, *written], ledger, explored=said)


def _persons_design(workspace: Workspace, change_id: str, state: ChangeState) -> bool:
    """Whether a change's design.md is a person's: written by hand, or edited since adk-spec drafted it."""
    raw = workspace.approval_texts(change_id).get(DESIGN_FILE)
    return raw is not None and state.drafted.get(DESIGN_FILE) != approval_files({DESIGN_FILE: raw})[DESIGN_FILE]


def _read_code(
    workspace: Workspace, change_id: str, seed: dict[str, Any], ledger: Any, repositories: Mapping[str, str]
) -> tuple[str, Path | None]:
    """The repository's code read for a change, and `context.md` written from what was kept: what to say of it, and
    the file where one was written. Nothing is read where the change has a `context.md` already, which is then a
    person's to keep, or where there is no repository or no file in it.

    A reading never stops a plan: one that fails, or keeps nothing, is said in a line, and the plan is drafted
    without it. One that ends early writes what it kept and says that it is partial."""
    kept = workspace.home / CHANGES / change_id / CONTEXT_FILE
    if kept.is_file():
        # A reading that ended early is said each time it is used: nothing else would show that it is no whole one.
        early = PARTIAL in context_text(workspace, change_id)
        return ("kept: context.md is of a reading that ended early. Delete it to read again" if early else ""), None
    from ..orchestration.stages import BRIEF_TEXT, DELTAS_TEXT, PROFILE_TEXT
    from ..orchestration.stages import CONSTITUTION as RULES

    read = _code_read(
        workspace,
        change_id,
        {key: seed[key] for key in (RULES, BRIEF_TEXT, DELTAS_TEXT, PROFILE_TEXT)},
        ledger,
        repositories,
    )
    if read is None:
        return "", None
    return read.said, _context_written(workspace, change_id, read)


@dataclass(frozen=True)
class _Read:
    """What a reading of the code came to, in a line, and what it kept as `context.md` holds it: nothing where it
    kept nothing. Rendered once, at the reading, so the file says when the code was read."""

    said: str
    text: str


#: The heading a reading's text opens with, the change's id set after it once the change has one.
_CONTEXT_TITLE = "Context"


def _code_read(
    workspace: Workspace, change_id: str | None, seed: dict[str, Any], ledger: Any, repositories: Mapping[str, str]
) -> _Read | None:
    """One reading of the repository's code, of its installed libraries and of the repositories a change names,
    seeded with `seed` and the files a stage may name: what it came to. Nothing where there is no repository or no
    file in it. `propose` reads before the brief, `plan` where a change has no `context.md`: one reading, one scope."""
    from ..orchestration.explore import ROLES
    from ..orchestration.models import require_ready
    from ..orchestration.stages import TREE

    source = _source(workspace, repositories, installed=True)
    if source is None or not source.paths:  # found by the fourth audit: said by `init` alone
        print("explored  nothing: no git repository here, or no file in it")
        return None
    # Asked after only once there is code to read: a plan outside a repository needs no reading model.
    if why := require_ready(roles=ROLES):
        raise UsageError(why)
    with ledger.held_to_half("the reading"):
        found, failure = _reading(workspace, "explore", change_id, {**seed, TREE: source.tree()}, ledger, source)
    said = _explored_said(found, len(source.names), failure)
    if not found.statements:
        return _Read(said, "")
    partial = "; ".join(part for part in (failure, *source.missing) if part) or None
    return _Read(said, _found_text(workspace, _CONTEXT_TITLE, found, partial=partial, others=source.commits()))


def _context_said(workspace: Workspace, change_id: str, read: _Read | None) -> None:
    """The reading's `context.md` written for a change propose wrote, and said: a refusal is said beside the change,
    which stands. Found by review: said as "no change was written", with the change there to be proposed twice."""
    try:
        if context := _context_written(workspace, change_id, read):
            print(f"          {workspace.shown(context)}")
    except WorkspaceError as exc:
        print(f"{PROG}: the change is written, and its context.md is not: {exc}", file=sys.stderr)


def _context_written(workspace: Workspace, change_id: str, read: _Read | None) -> Path | None:
    """What a reading kept, written as the change's `context.md` under the change's id: nothing where it kept
    nothing."""
    if read is None or not read.text:
        return None
    titled = read.text.replace(f"# {_CONTEXT_TITLE}\n", f"# {_CONTEXT_TITLE}: {change_id}\n", 1)
    (path,) = workspace.write_into(change_id, {CONTEXT_FILE: titled})
    return path


def _reading(
    workspace: Workspace, label: str, change_id: str | None, seed: dict[str, Any], ledger: Any, source: Source
) -> tuple[Any, str | None]:
    """One recorded reading of the code through `source`, seeded with `seed`: what it kept, as `explored` reads it,
    and why it ended early, where it did. What it kept is in its state, also where it failed."""
    from ..orchestration.explore import build_explore_app, explored

    def build(ledger: Any, recorder: Any) -> Any:
        return build_explore_app(source=source, ledger=ledger, recorder=recorder)

    run, _none, _ledger, failure = _asked(workspace, label, change_id, build, seed, lambda _state: None, ledger=ledger)
    return explored(run.state), failure


def _explored_said(found: Any, others: int, failure: str | None) -> str:
    """What a reading came to, in one line: `9 files in 3 repositories: 14 statements kept, 3 left out, 2 unknown`,
    and why it ended early, where it did; or why it kept nothing."""
    if not found.statements:
        nothing = "no statement quoted what was read" if found.read else "nothing the scout named could be read"
        return f"nothing: {failure or ('the review disputed every statement' if found.disputed else nothing)}"
    files, kept, dropped = len(found.read), len(found.statements), found.dropped + found.disputed
    said = f"{files} file{'' if files == 1 else 's'}" + (f" in {others + 1} repositories" if others else "")
    said += f": {kept} statement{'' if kept == 1 else 's'} kept"
    said += f", {dropped} left out" if dropped else ""
    said += f", {len(found.unknown)} unknown" if found.unknown else ""
    return said + (f"; it ended early: {failure}" if failure else "")


def _found_text(
    workspace: Workspace,
    title: str,
    found: Any,
    *,
    partial: str | None,
    others: Mapping[str, str | None] | None = None,
    sections: Sequence[tuple[str, str]] = SECTIONS,
) -> str:
    """What a reading kept, as the file a stage reads it from: a change's `context.md`, or the profile."""
    return render_context(
        title,
        at=datetime.now(UTC).isoformat(timespec="seconds"),
        commit=_commit(workspace),
        statements=found.statements,
        read=found.read,
        left_out=found.left_out,
        dropped=found.dropped,
        partial=partial,
        others=others,
        unknown=found.unknown,
        disputed=found.disputed,
        sections=sections,
    )


def _planned(args: argparse.Namespace, workspace: Workspace) -> int:
    """The `plan` command: the plan drafted, and what was written said. A repository named with `--with` is added to
    the change first, and checked before anything is spent."""
    named = None
    if args.with_:
        state = workspace.load_change(args.id).change.state
        named = _with_checked(workspace, args.with_, state.repositories, Path(args.root))
        if (workspace.home / CHANGES / args.id / CONTEXT_FILE).is_file():
            print(f"kept      {CONTEXT_FILE} was read before: delete it to read again with what --with named")
    specs, of_specs = workspace.specs()
    made = _plan_made(
        workspace, args.id, specs, of_specs, replace=args.replace, explore=not args.no_explore, repositories=named
    )
    if made.explored:
        print(f"explored  {made.explored}")
    if made.failure:
        return _unfinished(f"no plan was written: {made.failure}", made.ledger)
    if named is not None:  # a plan refused or not made changes nothing of the change
        _widened(workspace, args.id, named)
    for path, replaced in made.written:
        print(f"{'replaced' if replaced else 'wrote':<10}{workspace.shown(path)}")
    print(f"tokens    {_spent(made.ledger)}")
    _say_next(workspace, args.id, specs)
    return EXIT_OK


def _widened(workspace: Workspace, change_id: str, named: Mapping[str, str]) -> None:
    """A change's repositories recorded as `named`. A repository given a new path loses the starting point it had:
    that commit is another repository's."""
    state = workspace.load_change(change_id).change.state
    moved = {name for name, path in named.items() if state.repositories.get(name, path) != path}
    began = {name: commit for name, commit in state.base_commits.items() if name not in moved}
    workspace.save_state(state.model_copy(update={"repositories": dict(named), "base_commits": began}))


@dataclass
class _Checked:
    """A check as it was made: every finding, with its path from the root; where its report stands, as a person is
    shown it; how many of the model's findings pointed at nothing; the ledger of the model's pass, where there was
    one; and why the pass did not end well, where it did not, in which case nothing was written or recorded."""

    findings: list[Finding] = field(default_factory=list)
    report: str = ""
    dropped: int = 0
    ledger: Any = None
    failure: str | None = None


def _check_made(
    workspace: Workspace, change_id: str, specs: dict[str, Spec], assessed: Assessed, *, no_model: bool
) -> _Checked:
    """A change's files checked against each other, with nothing printed: by code always, and by a model where the
    files read and it was not ruled out. The report is written and the check recorded with the fingerprints of what
    was read; where the model's pass does not end well, neither is. What `check` does, and what `approve` does for
    a change whose check is not current."""
    texts = workspace.approval_texts(change_id)
    judged: list[Finding] = []
    dropped, ledger, model = 0, None, None
    if not no_model and not any(held.severity == "ERROR" for held in assessed.findings):
        from ..orchestration.models import serving

        judged, dropped, ledger, failure = _judged(workspace, assessed.loaded.change, specs, texts)
        if failure:
            return _Checked(ledger=ledger, failure=failure)
        model = serving("check")
    at = datetime.now(UTC).isoformat(timespec="seconds")
    every = [*assessed.findings, *_from_root(change_id, judged)]
    warnings_block = DEMANDS[assessed.state.tier].warnings_block
    report = render_check(
        change_id, at, _inside(change_id, every), model=model, dropped=dropped, warnings_block=warnings_block
    )
    read = {**approval_files(texts), **_beside(workspace, assessed.loaded.change, specs)}
    if model is None and model_holds(assessed.state, read):  # its report stands with it: found by the cleanup review
        return _Checked(every, "", dropped, ledger)
    path = workspace.write_report(change_id, "check.md", report)
    workspace.save_state(checked(assessed.state, every, files=read, at=at, model=model, judged=judged))
    return _Checked(every, workspace.shown(path), dropped, ledger)


def _reviewed(args: argparse.Namespace, workspace: Workspace) -> int:
    """The `check` command: the check made, and what it found said."""
    specs = _living(workspace, f"`{args.id}` is not checked")  # coverage is unknown while a spec is unread
    assessed = _assessed(workspace, args.id, specs)
    if assessed.state.status == "archived":
        raise NotYetError(f"`{args.id}` is archived: there is nothing left to check")
    held = assessed.state.check
    errors = [found for found in assessed.findings if found.severity == "ERROR"]
    # An error stands: the check by code alone below says it, and leaves a model's check as it is. Found by the code
    # review: refused here, the error that held the model's pass went unseen.
    if args.no_model and held is not None and not errors and model_holds(assessed.state, assessed.seen):
        if check_stands(assessed.state, assessed.seen):
            why = "its files have not changed since, and a check by code alone does not replace it"
        else:
            why = f"only a model clears what a model found: `{PROG} check {args.id}` asks the model again"
        print(
            f"{PROG}: the check of `{args.id}` by {held.model} stands, with {held.blocking} blocking: {why}",
            file=sys.stderr,
        )
        return EXIT_FINDINGS if held.blocking else EXIT_OK
    if errors:
        print(f"{PROG}: fix what the check lists first: the model's pass waits for files that read", file=sys.stderr)
    made = _check_made(workspace, args.id, specs, assessed, no_model=args.no_model)
    if made.failure:
        return _unfinished(f"the check did not finish, and nothing was recorded: {made.failure}", made.ledger)
    _printed(made.findings)
    if made.report:  # none where a model's check stands, with its report
        print(f"wrote     {made.report}")
    if made.dropped:
        print(f"note      {left_out(made.dropped)}")
    if made.ledger is not None:
        print(f"tokens    {_spent(made.ledger)}")
    _say_next(workspace, args.id, specs)
    return EXIT_FINDINGS if blocking(assessed.state, made.findings) else EXIT_OK


def _judged(
    workspace: Workspace, change: Any, specs: dict[str, Spec], texts: dict[str, str]
) -> tuple[list[Finding], int, Any, str | None]:
    """The model's pass of a check: its findings that point at something, each with its path in the change's
    folder; how many pointed at nothing; the ledger; and the failure, where the pass did not end well."""
    from ..orchestration.models import require_ready

    if why := require_ready(roles=("check",)):
        raise UsageError(why)
    from ..orchestration.graph import build_check_app
    from ..orchestration.stages import CHANGE_FILES, LIVING
    from ..orchestration.stages import CONSTITUTION as RULES
    from ..orchestration.stages.check import read_check

    # What a model is shown and what its quotes are looked for in are one text: every request is scrubbed of
    # secret shapes, so a quote of a scrubbed line is found only in the scrubbed file.
    texts = {path: scrub_lines(text)[0] for path, text in texts.items()}
    seed = {
        RULES: constitution_text(workspace),
        LIVING: living_text(specs, sorted(change.deltas)),
        CHANGE_FILES: files_text(texts),
    }

    def build(ledger: Any, recorder: Any) -> Any:
        return build_check_app(ledger=ledger, recorder=recorder)

    _run, answer, ledger, failure = _asked(workspace, "check", change.state.id, build, seed, read_check)
    if failure:
        return [], 0, ledger, failure
    return *to_findings(answer, texts), ledger, None


def _key_files(held: Sequence[str], then: str) -> str:
    """What is said of the files a diff was shown without: `a.pem: holds a private key, which is never shown`."""
    return f"{', '.join(held)}{then}{'holds' if len(held) == 1 else 'hold'} a private key, which is never shown"


def _bases(given: Sequence[str], state: ChangeState) -> tuple[str | None, dict[str, str]]:
    """`--base` read once: the commit of this repository, where one is named, and another repository's by its name.
    `UsageError` for a name the change does not hold, for one named twice, and for two commits of this one."""
    here: list[str] = []
    named: dict[str, str] = {}
    for one in given:
        name, sep, ref = one.partition("=")
        if not (sep and NAME.fullmatch(name)):
            here.append(one)
        elif name not in state.repositories:
            held = ", ".join(state.repositories) or "none"
            raise UsageError(f"`{name}` is no repository of `{state.id}`. Its repositories: {held}")
        elif name in named:
            raise UsageError(f"--base names the starting point of {name} twice")
        elif not ref:
            raise UsageError(f"--base {name}= names no commit: give one, as {name}=REF")
        else:
            named[name] = ref
    if len(here) > 1:
        raise UsageError("--base names the commit of this repository once; NAME=REF names another repository's")
    return (here[0] if here else None), named


def _starts(named: Mapping[str, str], source: Source, state: ChangeState) -> dict[str, str]:
    """Where the work began in each other repository of a change: as `--base NAME=REF` names it, or as an approval
    recorded it. `UsageError` for one that is not here, or has no starting point: the work cannot be judged on part
    of it."""
    bases: dict[str, str] = {}
    for name in state.repositories:
        if (root := source.root_of(name)) is None:
            raise UsageError(f"{source.why_not(name)}: the work cannot be judged on part of it")
        if not (ref := named.get(name) or state.base_commits.get(name)):
            raise UsageError(
                f"{name} has no starting point: none was recorded when `{state.id}` was approved. Name where its "
                f"work began with --base {name}=REF"
            )
        if (commit := resolves(root, ref, trust=False)) is None:
            raise UsageError(f"`{ref}` names no commit in {name}")
        bases[name] = commit
    return bases


def _work(
    args: argparse.Namespace, workspace: Workspace, state: ChangeState, source: Source
) -> tuple[str, dict[str, str], Work]:
    """The commit a change's work is compared with here and in each other repository it names, and the work since
    them. `UsageError` where there is nothing to compare with; `NotYetError` where nothing was done that can be
    shown."""
    cid, root = state.id, workspace.root
    if not is_repository(root):
        raise UsageError(f"{root} is in no git repository: verify reads what changed since the approval")
    here, others = _bases(args.base, state)
    named = here or state.base_commit
    if not named:
        raise UsageError(
            f"no commit was recorded when `{cid}` was first approved. Name the commit the work started from with --base"
        )
    base = resolves(root, named)
    if base is None:
        raise UsageError(f"`{named}` names no commit in this repository")
    bases = _starts(others, source, state)
    # A file that holds a private key is no part of the work a model is shown, as an excluded path is none.
    work = source.work(base, bases)
    if not work.text.strip():
        beside = f"{_key_files(work.held, ' ')}, and nothing else" if work.held else "nothing"
        raise NotYetError(f"{beside} under {root} changed since {base[:12]}: there is nothing to verify")
    if len(work.text) > DIFF_MAX_CHARS:
        raise UsageError(
            f"the diff since {base[:12]} holds {len(work.text):,} characters, past the {DIFF_MAX_CHARS:,} a stage "
            "is given. It is never cut. Verify a smaller change, or name a later commit with --base"
        )
    return base, bases, work


def _verified(args: argparse.Namespace, workspace: Workspace) -> int:
    """The work judged against the change's requirements, one verdict each. The report is written and the
    verification recorded; the change is `verified` where every requirement is shown met, or a person says so
    with a reason."""
    specs, _of_living = workspace.specs()
    assessed = _assessed(workspace, args.id, specs, drift=False)  # the work is diffed below, once
    change, state = assessed.loaded.change, assessed.state
    if why := verify_blockers(state, assessed.stale):
        raise NotYetError(why[0])
    added, gone = owed(change.deltas), removed(change.deltas)
    if added or gone:  # the model is asked after before the tests are run: a run is paid for in minutes
        from ..orchestration.models import require_ready

        if why := require_ready(roles=("verify",)):
            raise UsageError(why)
    runs, base, bases, work = _tested_work(args, workspace, state)
    verdicts: list[Verdict] = []
    ledger, model = None, None
    if added or gone:  # a change with no delta has no requirement to judge
        from ..orchestration.models import serving

        verdicts, ledger, failure = _verdicts(workspace, change, work.text, added, gone, render_tests(runs))
        if failure:
            return _unfinished(f"the verification did not finish, and nothing was recorded: {failure}", ledger)
        model = serving("verify")
    at = datetime.now(UTC).isoformat(timespec="seconds")
    said = {one.id: one.verdict for one in verdicts}
    ran = {run.name or ".": run.outcome for run in runs}
    after = verified(
        state,
        said,
        base=base,
        diff=work.fingerprint,
        at=at,
        model=model,
        override=args.override,
        bases=bases,
        tests=ran,
    )
    reason = after.verification.override if after.verification else None
    report = render_verify(args.id, at, base, verdicts, model=model, override=reason, bases=bases, tests=runs)
    # The report, the lines that proved each requirement and the record, written as one set: found by the code
    # review, written in turn, a failure between two of them lost a verification paid for, or left the record with
    # an earlier one's evidence, which the archive then took out of the living spec with nothing put in.
    files = {f"{REPORTS}/verify.md": report}
    if proofs := kept(verdicts, added=added, change=args.id, at=at, repositories=state.repositories):
        files[EVIDENCE] = render_evidence(args.id, proofs)
    wrote = workspace.save_state(after, files=files)[:1]
    if not proofs:  # another verification's, which the archive ignores, whether or not it goes
        workspace.drop(args.id, EVIDENCE)
    # What is left, where the next step points, and what a reviewer of the pull request reads, an override's reason
    # with it: aids each, written after the record, so neither loses it.
    touched = frozenset(path for path, _text in parts_of_diff(work.text) if path)
    left = remaining(verdicts, change.tasks or (), touched) if after.status != "verified" else []
    aids = {
        "summary.md": render_summary(change, said, ran, after.approval, override=reason),
        REMAINING: render_remaining(args.id, left, last=DEMANDS[state.tier].closing) if left else None,
    }
    wrote += _aids_written(workspace, args.id, aids)
    for one in verdicts:
        print(f"{one.verdict:<8}  {one.id}  {one.reason}")
    print(f"wrote     {', '.join(workspace.shown(path) for path in wrote)}")
    if ledger is not None:
        print(f"tokens    {_spent(ledger)}")
    _say_next(workspace, args.id, specs, drift=False)  # found by the fourth audit: the diff was made a third time
    return EXIT_OK if after.status == "verified" else EXIT_FINDINGS


def _aids_written(workspace: Workspace, change_id: str, aids: Mapping[str, str | None]) -> list[Path]:
    """Each report of `aids` written under the change's `reports/`, or removed where its text is None; one that
    cannot be written is left out of what is said written, as the command's record is saved already."""
    wrote = []
    for name, text in aids.items():
        with contextlib.suppress(OSError, WorkspaceError):
            if text is None:
                workspace.drop(change_id, f"{REPORTS}/{name}")
            else:
                wrote.append(workspace.write_report(change_id, name, text))
    return wrote


def _tested_work(
    args: argparse.Namespace, workspace: Workspace, state: ChangeState
) -> tuple[list[TestRun], str, dict[str, str], Work]:
    """The work a verification judges, and the runs of the tests before it: refused first where there is nothing
    to judge, then the tests, then the work read again, as it stands after them. A run may write to the work, a
    lock file say: judged and fingerprinted before it, the change would drift the moment it is verified."""
    source = _sources(workspace, state.repositories)
    base, bases, work = _work(args, workspace, state, source)
    for name, commit in bases.items():
        print(f"with      {name} from {state.repositories[name]}, since {commit[:12]}")
    runs = _tested(workspace, source)
    if runs:
        judged = work.text
        base, bases, work = _work(args, workspace, state, _sources(workspace, state.repositories))
        if work.text != judged:
            print("changed   the tests changed the work: it is judged as it stands after them")
    if work.held:
        print(f"left out  {_key_files(work.held, ': ')}")
    return runs, base, bases, work


def _tested(workspace: Workspace, source: Source) -> list[TestRun]:
    """Each test command of the change's repositories run, each said before it runs: the workspace's own, from its
    `.spec/config.toml`, then each other repository's, from its own. Only a command a person wrote in a config is
    ever run."""
    config = workspace.config()
    asked = [("", workspace.root, config.test, config.test_timeout)] if config.test else []
    every = [*asked, *source.tests()]
    if not asked:  # found by the fourth audit: a `met` read as tested, with no test run here
        print(f"tests     none named{' here' if every else ''}: set [verify] test in .spec/config.toml")
    runs = []
    for name, root, argv, timeout in every:
        print(f"testing   {f'{name}: ' if name else ''}{scrub(' '.join(argv))[0]}")
        done = run_tests(root, argv, timeout=timeout, name=name, without=frozenset(_FROM_ENV_FILE))
        took = "" if done.seconds is None else f" in {done.seconds:.1f} s"
        print(f"tests     {f'{name} ' if name else ''}{done.outcome}{took}")
        runs.append(done)
    return runs


def _verdicts(
    workspace: Workspace, change: Any, text: str, added: frozenset[str], gone: frozenset[str], tests: str
) -> tuple[list[Verdict], Any, str | None]:
    """The model's verdicts on a diff, each held to the lines the diff really holds; the ledger; and the failure,
    where the run did not end well."""
    from ..orchestration.graph import build_verify_app
    from ..orchestration.stages import DELTAS_TEXT
    from ..orchestration.stages.verify import DIFF, REQUIRED, TASKS_TEXT, TESTS, read_verify, required_text

    # As in a check: the diff a model is shown and the diff its evidence is looked for in are one text, scrubbed
    # once. The fingerprint of the work is of the diff as it stands, and is taken where the diff is cut.
    text = scrub_lines(text)[0]
    seed = {
        DELTAS_TEXT: _deltas_text(change),
        TASKS_TEXT: render_tasks(change.tasks) if change.tasks else "",
        REQUIRED: required_text(added, gone),
        DIFF: text,
        TESTS: tests,
    }

    def build(ledger: Any, recorder: Any) -> Any:
        return build_verify_app(ledger=ledger, required=added | gone, recorder=recorder)

    _run, answer, ledger, failure = _asked(workspace, "verify", change.state.id, build, seed, read_verify)
    if failure:
        return [], ledger, failure
    return grounded(answer, text, added=added, removed=gone), ledger, None


def _tier_of(args: argparse.Namespace, change: Change | None) -> Tier | None:
    """The tier of a request, decided once: a change being revised keeps its own, and a person's `--tier` is taken
    next. Nothing where the model is to size it."""
    if change is not None:
        state = change.state
        print(f"revising  {state.id}, a {state.tier} {state.status}: its files kept where the request does not reach")
        if args.tier and args.tier != state.tier:
            print(f"          `--tier {args.tier}` is not used: a change keeps its tier")
        return state.tier
    return args.tier


def _of_a_delta(held: Finding) -> bool:
    """Whether a fault is of a change's delta: one that did not read is known to no command that writes the change."""
    return (held.path or "").startswith(f"{SPECS}/")


def _revising(workspace: Workspace, change_id: str | None) -> Change | None:
    """The open change `change_id` names, to be revised by the request, or nothing where it names none. A verified
    or archived change is refused: its work was judged against what it says."""
    if not change_id or change_id not in workspace.changes():
        return None
    loaded = workspace.load_change(change_id)
    change = loaded.change
    # Found by the fourth audit: a delta that did not read was unknown to the revision, which deleted it; and by the
    # code review, a file that would not open read as empty, and was written over.
    if unread := [held for held in loaded.problems if _of_a_delta(held) or held.code == UNREAD]:
        _printed(_from_root(change_id, unread))
        raise NotYetError(
            f"`{change_id}` is not revised: a revision would write over a file that does not read. Fix it first"
        )
    if (status := change.state.status) in ("verified", "archived"):
        raise NotYetError(
            f"`{change_id}` is {status}: a change whose work was judged is not revised. Propose a new change for "
            "what is still wanted"
        )
    return change


def _proposed(args: argparse.Namespace, workspace: Workspace, change: Change | None) -> int:
    """A request drafted into a change, or the open change `change` revised by it."""
    from ..domain.drafts import BriefDraft
    from ..orchestration.gate import FAILURE
    from ..orchestration.graph import Known
    from ..orchestration.plugins import UsageLedger
    from ..orchestration.stages import CAPABILITIES, LESSONS_TEXT, REQUEST, TIER
    from ..orchestration.stages import CONSTITUTION as RULES
    from ..orchestration.stages.brief import KEY as BRIEF_KEY
    from ..orchestration.stages.deltas import KEY as DELTAS_KEY
    from ..orchestration.stages.triage import read_triage

    held = change.state.repositories if change else {}
    repositories = _with_checked(workspace, args.with_, held, Path(args.root))  # checked before any call
    specs = _living(workspace, "nothing was drafted")
    taken = frozenset(workspace.taken(specs))
    known = Known(living=specs, taken=taken, kept=kept_ids(change.deltas) if change else {})
    # One ledger for every run of this command: the count and the ceiling are the command's.
    ledger = UsageLedger(workspace.config().max_tokens or None)
    seed = {REQUEST: args.request, CAPABILITIES: capability_index(specs), RULES: constitution_text(workspace)}
    lessons = _optional(workspace, lessons_text, LESSONS)
    seed |= {LESSONS_TEXT: lessons or "", **_as_it_stands(workspace, change)}
    # A new change's code is read before its brief, and once: the plan keeps what this reading found.
    explore = not args.no_explore and change is None
    with _recording(workspace, "propose", args.id) as kept:
        state, read = _drafts(
            args, workspace, known, ledger, kept.recorder, seed, change, repositories, explore=explore
        )
        tier = state.get(TIER)
        whole = tier == "none" or (state.get(BRIEF_KEY) and state.get(DELTAS_KEY))
        if tier is None or not whole or state.get(FAILURE):
            failure = state.get(FAILURE) or "the run ended before its drafts were whole"
            kept.outcome = f"failed: {failure}"
            print(f"{PROG}: no change was written: {failure}", file=sys.stderr)
            print(f"tokens    {_spent(ledger)}")
            return EXIT_ENGINE
        if tier == "none":
            sized = read_triage(state)
            kept.outcome = "nothing owed"
            print(f"no spec is owed: {sized if isinstance(sized, str) else sized.reason}")
            print(f"tokens    {_spent(ledger)}")
            return EXIT_OK
        try:
            kept.change, changed = _written(args, workspace, known, state, tier, repositories, change)
        except WorkspaceError as exc:  # the calls are paid for by now: say so beside the refusal
            kept.outcome = f"failed: {exc}"
            print(f"{PROG}: no change was written: {exc}", file=sys.stderr)
            print(f"tokens    {_spent(ledger)}")
            return EXIT_USAGE
        kept.outcome = "written"
        _context_said(workspace, kept.change, read)
    keep = _tasks_kept(workspace, change, changed) if change else None
    change_id = kept.change or ""
    # A tier that reads first stops here: the plan is drafted once a person read the brief and the specs. Not an
    # approved change, which `plan` refuses: found by the code review, said to wait beside a step to implement it.
    drafted = workspace.state(change_id).status == "draft"
    review = (
        _plan_command(workspace, change_id, change, args.no_explore) if DEMANDS[tier].read_first and drafted else None
    )
    # The plan reads the lessons again, with any this run learned; a file that is no text was said already.
    planned = {"keep": keep, "review": review, "lessons": "" if lessons is None else None}
    # With no question asked, each open point is printed with its suggestion, for an assistant to put to the person.
    # Found by the third audit: the editor's tools promised them in the output, which held their count alone.
    unasked = questions_of(BriefDraft.model_validate(state[BRIEF_KEY]), every=True) if args.no_input else []
    return _then_planned(workspace, change_id, specs, [], ledger, **planned, unasked=unasked)


def _open_said(unasked: Sequence[Mapping[str, str]]) -> None:
    """Each open point a run asked no one about, and the answer it suggests."""
    for one in unasked:
        print(f"open      {plain(one['question'])}")
        if one["suggested"]:
            print(f"          suggested: {plain(one['suggested'])}")


def _plan_command(workspace: Workspace, change_id: str, change: Change | None, no_explore: bool) -> str:
    """The `plan` that goes on after a stop, with `--no-explore` where the person gave it, the change is revised, or
    a `context.md` is there to keep. Found by review: said always, it kept a plan from reading where propose's reading
    wrote nothing. Never with `--replace`: a ticked list is the person's to throw away, as the `kept` line says."""
    there = (workspace.home / CHANGES / change_id / CONTEXT_FILE).is_file()
    flags = " --no-explore" if no_explore or change is not None or there else ""
    return f"`{PROG} plan {change_id}{flags}`"


def _tasks_kept(workspace: Workspace, change: Change, changed: bool) -> str | None:
    """Why a revised change keeps its task list as it stands, and how to draft it again; nothing where it is drafted
    again. A ticked box is never lost, and a list whose requirements did not change is not paid for again."""
    cid = change.state.id
    if _ticked(workspace, change):
        why, flags = "a task is ticked", " --replace"
    elif not changed and change.tasks is not None:
        why, flags = "no requirement changed", ""
    else:
        return None
    # `plan` drafts for a draft alone: found by the code review, an approved change the revision left as it stood
    # was sent to a `plan` that refused.
    if workspace.state(cid).status == "draft":
        return f"{why}. `{PROG} plan {cid}{flags}` drafts it again"
    return f"{why}: to change it, edit tasks.md, then run `{PROG} approve {cid}` again"


def _then_planned(
    workspace: Workspace,
    change_id: str,
    specs: dict[str, Spec],
    of_specs: list[Finding],
    ledger: Any,
    *,
    keep: str | None,
    review: str | None = None,
    lessons: str | None = None,
    unasked: Sequence[Mapping[str, str]] = (),
) -> int:
    """What `propose` does once its change is written: the plan, in the same command and under the same ceiling.
    An open point comes before it, since its answer shapes the tasks: none is drafted on a guess. A revised change
    keeps its task list where `keep` says why. A change of a tier that reads first stops here for a person to read its
    brief and specs: `review` is the command that goes on."""
    found = _assessed(workspace, change_id, specs).findings
    waiting = [held for held in found if held.code == _OPEN_POINT]
    # Found by the code review: a base kept that no longer holds is an error the plan refuses; asked anyway, the
    # revision ended as an engine failure, naming a `plan` that refused again.
    blocked = plan_blockers(found)
    if waiting or keep or review or blocked:
        count = len(waiting)
        print(f"tokens    {_spent(ledger)}")
        if blocked:
            _printed(blocked)
            print("plan      waits: the errors above are fixed first")
        elif waiting:
            print(f"plan      waits: the brief leaves {count} point{'' if count == 1 else 's'} open")
            _open_said(unasked)
        elif review:
            print("plan      waits: the change is read before it is planned")
        if keep:
            print(f"kept      tasks.md: {keep}")
        _say_next(workspace, change_id, specs, plan=review)  # the step `status` names, with the plan's flags
        return EXIT_FINDINGS if blocked else EXIT_OK
    # The change is written by now: a plan that does not end well leaves it a draft, and `plan` finishes it.
    try:
        made = _plan_made(  # the code was read before the brief, or is not to be: the plan reads none
            workspace, change_id, specs, of_specs, replace=False, ledger=ledger, explore=False, lessons=lessons
        )
    except NotYetError as exc:  # the calls so far are paid for: what stopped the plan is said as any other failure
        made = _Planned(ledger=ledger, failure=str(exc))
    if made.failure:
        return _unfinished(
            f"the brief and the specs are written, and the plan is not: {made.failure}. Run "
            f"`{PROG} plan {change_id}` to finish it",
            ledger,
        )
    for path, _replaced in made.written:
        print(f"          {workspace.shown(path)}")
    print(f"tokens    {_spent(ledger)}")
    print(f"read      {_first_reads(workspace, change_id)} first")
    _say_next(workspace, change_id, specs)
    return EXIT_OK


def _as_it_stands(workspace: Workspace, change: Change | None) -> dict[str, str]:
    """A change being revised, as its files stand, a person's edits included: what the brief and deltas stages
    revise, each delta under its path. Nothing for a new change."""
    if change is None:
        return {}
    from ..orchestration.stages import CURRENT_DELTAS
    from ..orchestration.stages.brief import REPLACES

    texts = workspace.approval_texts(change.state.id)
    deltas = {name: text for name, text in sorted(texts.items()) if name.startswith(f"{SPECS}/")}
    return {REPLACES: change.brief_raw or "", CURRENT_DELTAS: files_text(deltas)}


def _rewritten(
    workspace: Workspace, change: Change, deltas: Mapping[str, Delta], files: Mapping[str, str], fields: dict[str, Any]
) -> bool:
    """A change revised in place: its files and state written anew, a delta of a capability it no longer touches
    taken out, and what changed in its requirements said: whether anything did. An approved change whose files
    changed is a draft again, as after a rebase, and is approved again: what was approved is no longer what it says.
    One the revision wrote as it stood keeps its approval."""
    texts = workspace.approval_texts(change.state.id)  # as they stand on disk: a delta off its grammar too
    gone = sorted(name for name in texts if name.startswith(f"{SPECS}/") and name not in files)
    same = not gone and all(texts.get(name) == text for name, text in files.items())
    same = same and fields["repositories"] == change.state.repositories
    folder = workspace.rewrite_change(
        change.state.model_copy(update=fields) if same else reopened(change.state, **fields), files, gone
    )
    added, changed, dropped = revision(change.deltas, deltas)
    lists = (("added", added), ("changed", changed), ("dropped", dropped))
    said = "; ".join(f"{verb} {', '.join(ids) or 'nothing'}" for verb, ids in lists)
    print(f"revised   {said}")
    if change.state.approval is not None and not same:
        print(f"the approval is void: read what changed, then run `{PROG} approve {change.state.id}` again")
    for name in gone:  # a person's file, taken out: said by name, never in silence
        print(f"removed   {workspace.shown(folder / name)}")
    _said_written(workspace, folder, files, "")
    return bool(added or changed or dropped)


def _said_written(workspace: Workspace, folder: Path, files: Iterable[str], what: str) -> None:
    """The files a command wrote into a change's folder, the first line saying what the change is."""
    print(f"wrote     {workspace.shown(folder)}{what}")
    for path in files:
        print(f"          {workspace.shown(folder)}/{path}")


#: The finding of a point a brief leaves open, which holds a plan back.
_OPEN_POINT = "brief.marker-unresolved"


def _assumed(text: str) -> int:
    """How many assumptions a brief file states, none where it does not read."""
    try:
        return assumption_count(parse_brief(text).assumptions)
    except GrammarError:
        return 0


def _first_reads(workspace: Workspace, change_id: str) -> str:
    """What a person reads first of a change, each with its length: the brief, and the design where there is one.
    Review counts most there, early and short; the task list follows from the two."""
    texts = workspace.approval_texts(change_id)
    first = [f"{name} ({len(lines_of(texts[name]))} lines)" for name in (BRIEF_FILE, DESIGN_FILE) if name in texts]
    # What the brief assumed is read with it: found live, a standard brief assumed where it might have asked.
    if first and first[0].startswith(BRIEF_FILE) and (assumed := _assumed(texts[BRIEF_FILE])):
        first[0] = first[0][:-1] + f", {assumed} assumption{'' if assumed == 1 else 's'})"
    # What a reading could not establish is read before the plan that was drafted around it.
    if unknown := unknown_count(context_text(workspace, change_id)):
        first.append(f"{CONTEXT_FILE} ({unknown} unknown)")
    return " and ".join(first)


def _drafts(
    args: argparse.Namespace,
    workspace: Workspace,
    known: Any,
    ledger: Any,
    recorder: Any,
    seed: dict[str, Any],
    change: Change | None,
    repositories: Mapping[str, str],
    *,
    explore: bool,
) -> tuple[dict[str, Any], _Read | None]:
    """The runs of one `propose`, and what its reading kept: the request sized alone where no tier is known, so that
    one owing no spec spends no reading; the code read, where `explore`; then the brief and the deltas, drafted from
    what the reading kept and what the profile says. Facts are adk-spec's to find; decisions are the person's. A
    revision is drafted from the `context.md` its change keeps."""
    from ..orchestration.gate import FAILURE
    from ..orchestration.stages import BRIEF_TEXT, CONTEXT_TEXT, DELTAS_TEXT, PROFILE_TEXT, REQUEST, SIZED, TIER
    from ..orchestration.stages import CONSTITUTION as RULES
    from ..orchestration.stages.triage import read_triage, sized_text

    tier = args.tier
    if tier is None:
        sized = _sized_first(workspace, ledger, recorder, seed)
        tier = sized.get(TIER)
        if sized.get(FAILURE) or tier in (None, "none"):
            return sized, None
        # The brief starts from the capabilities triage found. Found live: told nothing of them, a brief named three
        # for a two-function change triage had sized as one, and the deltas stage could not fill them.
        if not isinstance(found := read_triage(sized), str):
            seed = {**seed, SIZED: sized_text(found)}
            # Said before the reading spends: a wrong tier is stopped here, and named with --tier.
            print(f"sized     {tier}: {plain(found.reason)}")
    profile = _optional(workspace, profile_text, PROFILE) or ""
    read = None
    if explore:  # aimed by the request, the brief to come
        asked = f"# A change is requested\n\n## The request\n\n{seed[REQUEST].strip()}\n"
        aim = {RULES: seed[RULES], BRIEF_TEXT: asked, DELTAS_TEXT: "", PROFILE_TEXT: profile}
        read = _code_read(workspace, None, aim, ledger, repositories)
        if read is not None:
            print(f"explored  {read.said}")
    context = context_of(read.text) if read is not None and read.text else ""
    if change is not None:
        context = context_text(workspace, change.state.id)
    seed = {**seed, PROFILE_TEXT: profile, CONTEXT_TEXT: context}
    return _rounds(args, workspace, known, ledger, recorder, seed, tier), read


def _sized_first(workspace: Workspace, ledger: Any, recorder: Any, seed: dict[str, Any]) -> dict[str, Any]:
    """The request sized alone: its tier under the state's key, or the failure that stopped it."""
    from ..orchestration.gate import FAILURE
    from ..orchestration.graph import build_triage_app

    run = _ran(build_triage_app(ledger=ledger, recorder=recorder), seed, "propose")
    _learned(workspace, run.state)
    return {**run.state, FAILURE: run.state.get(FAILURE) or run.failure}


def _rounds(
    args: argparse.Namespace,
    workspace: Workspace,
    known: Any,
    ledger: Any,
    recorder: Any,
    seed: dict[str, Any],
    tier: Tier | None,
) -> dict[str, Any]:
    """The runs of one `propose`, and the state the last of them left, a failure of the engine's own under the
    gate's key: the first run, then one more for each round of questions. A run ends on its questions and the
    person answers here, between two runs. Run on the pinned engine: a run paused and resumed runs again, unseen,
    any stage that had answered off its schema. Which run comes next, and seeded with what, is the graph's to say."""
    from ..orchestration.gate import FAILURE
    from ..orchestration.graph import ASKING, build_propose_app, first_run, next_run

    entry, seed = first_run(tier, seed)  # the tier `_tier_of` decided, or triage did, where one is known
    while True:
        app = build_propose_app(known, ask=not args.no_input, entry=entry, ledger=ledger, recorder=recorder)
        run = _ran(app, seed, "propose")
        _learned(workspace, run.state)
        state = {**run.state, FAILURE: run.state.get(FAILURE) or run.failure}
        if state[FAILURE] or state.get(ASKING) is None:
            return state
        if why := ledger.refusal():  # asking costs no call, so nothing else would stop it: no answer could be used
            return {**state, FAILURE: f"{why}, and the brief's open points were not put to you"}
        entry, seed = next_run(seed, state, _answered(state[ASKING]))


def _written(
    args: argparse.Namespace,
    workspace: Workspace,
    known: Any,
    state: dict[str, Any],
    tier: Tier,
    repositories: Mapping[str, str],
    change: Change | None,
) -> tuple[str, bool]:
    """The change a run drafted, written whole, or the open change it revised, written anew: its id, and whether a
    requirement changed."""
    from ..orchestration.graph import drafted, files_of

    made = drafted(state, known)
    files = files_of(made)
    fields: dict[str, Any] = {
        "bases": kept_bases(change.state.bases if change is not None else {}, made.deltas, known.living),
        "needs_design": owes_design(tier, made.needs_design),
        "repositories": dict(repositories),
    }
    if change is not None:
        return change.state.id, _rewritten(workspace, change, made.deltas, files, fields)
    change_id = args.id or slug_of(made.brief.title, workspace.names_held())
    folder = workspace.write_change(ChangeState(id=change_id, tier=tier, **fields), files)
    _said_written(workspace, folder, files, f", a {tier} draft")
    return change_id, True


def _login(args: argparse.Namespace) -> int:
    """The Copilot login, which reads the checkout's `.env` for an enterprise tenant's endpoints as a run does."""
    _load_env()
    from .login import main as login

    return login(["--force"] if args.force else [])


def _models(args: argparse.Namespace) -> int:
    _load_env()
    from ..orchestration.catalog import CatalogError, list_models, shown
    from ..orchestration.models import require_ready

    if why := require_ready(names=False):  # a wrong name is what the list is for
        raise UsageError(why)
    try:
        models = list_models()
    except CatalogError as exc:  # whatever a provider's client raised, said by `list_models`
        print(f"{PROG}: the models could not be listed: {exc}", file=sys.stderr)
        return EXIT_ENGINE
    print(json.dumps({"models": models}, indent=2) if args.json else "\n".join(shown(models)))
    return EXIT_OK


def _smoke(args: argparse.Namespace) -> int:
    """`--model` names the triage role's own model for this run and leaves nothing behind for the next."""
    _load_env()
    held = os.environ.get("SPEC_TRIAGE_MODEL")
    if args.model:
        os.environ["SPEC_TRIAGE_MODEL"] = args.model
    try:
        return _smoked(args)
    finally:
        if args.model:
            if held is None:
                os.environ.pop("SPEC_TRIAGE_MODEL", None)
            else:
                os.environ["SPEC_TRIAGE_MODEL"] = held


def _checked(args: argparse.Namespace) -> int:
    """Readiness alone, for `smoke --check`: nothing is built and nothing is sent."""
    from ..orchestration.models import require_ready, serving

    why = require_ready(roles=("triage",))
    if args.json:
        print(json.dumps({"model": serving("triage") if why is None else None, "ready": why is None, "why": why}))
    elif why is None:
        print(f"ready: {serving('triage')}")
    if why is not None:
        print(f"{PROG}: {why}", file=sys.stderr)
    return EXIT_OK if why is None else EXIT_USAGE


def _smoked(args: argparse.Namespace) -> int:
    from ..orchestration.models import require_ready, serving

    if args.check:
        return _checked(args)
    if why := require_ready(roles=("triage",)):
        raise UsageError(why)
    from ..orchestration.graph import build_smoke_app
    from ..orchestration.stages import CAPABILITIES, REQUEST
    from ..orchestration.stages.triage import KEY, read_triage

    try:  # the capabilities of the workspace this runs in, where it runs in one
        known = capability_index(_workspace(args).specs()[0])
    except WorkspaceError:
        known = ""
    run = _ran(build_smoke_app(), {REQUEST: args.request, CAPABILITIES: known}, KEY)
    answer = read_triage(run.state)
    failure = None
    if isinstance(answer, str):
        failure = run.failure or next(iter(run.errors.values()), None) or answer
    spent = run.usage
    if args.json:
        result = {
            "model": serving("triage"),
            "schema": "invalid" if failure else "valid",
            "triage": None if isinstance(answer, str) else answer.model_dump(),
            "failure": failure,
            "tokens": {"calls": spent.calls, "prompt": spent.prompt, "output": spent.output, "total": spent.total},
            "seconds": round(run.seconds, 1),
        }
        print(json.dumps(result, indent=2))
        return EXIT_ENGINE if failure else EXIT_OK
    lines = [("model", serving("triage"))]
    if isinstance(answer, str):
        lines.append(("schema", f"INVALID: {failure}"))
    else:
        lines += [
            ("schema", "valid"),
            ("tier", answer.tier),
            ("caps", ", ".join(answer.capabilities) or "-"),
            ("reason", answer.reason),
        ]
    calls = "call" if spent.calls == 1 else "calls"
    lines.append(("tokens", f"{spent.prompt} in, {spent.output} out, {spent.total} total, {spent.calls} {calls}"))
    lines.append(("seconds", f"{run.seconds:.1f}"))
    for label, value in lines:
        print(f"{label:<10}{value}")
    return EXIT_ENGINE if failure else EXIT_OK


def run() -> int:
    """The process boundary of the installed `adk-spec`."""
    # A Windows console is not UTF-8 by default, and an answer piped in there is read in the ANSI code page. What
    # is printed has its odd characters replaced; what is read is read strictly, so bytes that are no text raise
    # and are no answer, never a line of replacement marks taken for one.
    for stream, errors in ((sys.stdout, "replace"), (sys.stderr, "replace"), (sys.stdin, "strict")):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors=errors)
    try:
        return main(sys.argv[1:])
    except KeyboardInterrupt:
        print(f"{PROG}: interrupted. `{PROG} status` says where things stand", file=sys.stderr)
        return EXIT_INTERRUPTED
