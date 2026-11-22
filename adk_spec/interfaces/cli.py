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
from collections.abc import Callable, Generator, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any, NoReturn, get_args

from ..domain.brief_md import render_brief
from ..domain.check import nameable, owed, removed
from ..domain.context_md import PARTIAL, render_context
from ..domain.convert import render_design, slug_of, to_findings, to_tasks
from ..domain.delta_md import render_delta
from ..domain.lifecycle import (
    Step,
    approval_checks_first,
    approval_files,
    approval_stale,
    approve,
    approve_blockers,
    archive_blockers,
    capture_bases,
    check_blockers,
    check_stands,
    check_stops,
    checked,
    missing_bases,
    next_step,
    verified,
    verify_blockers,
)
from ..domain.merge import MergeError, apply_delta
from ..domain.model import Brief, ChangeState, Finding, Spec, Tier
from ..domain.report_md import left_out, place, render_check, render_verify
from ..domain.secrets import scrub_lines
from ..domain.spec_md import render_spec
from ..domain.tasks_md import render_tasks
from ..domain.text import lines_of, plain, sha256_of
from ..domain.validate import failed, finding, validate_spec
from ..domain.verify import Verdict, grounded
from ..workspace.config import ConfigError
from ..workspace.context import (
    CONSTITUTION_MAX_CHARS,
    ContextTooLargeError,
    capability_index,
    constitution_text,
    context_text,
    files_text,
    living_text,
    tree_text,
)
from ..workspace.files import NotTextError
from ..workspace.git import DIFF_MAX_CHARS, GitError, diff, head, is_repository, resolves
from ..workspace.layout import BRIEF as BRIEF_FILE
from ..workspace.layout import (
    CHANGES,
    CONSTITUTION,
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
from ..workspace.layout import TASKS as TASKS_FILE
from ..workspace.lock import held as lock_held
from ..workspace.paths import PathError
from ..workspace.runs import Recording
from ..workspace.runs import write as write_run
from ..workspace.source import Source

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
REFUSALS = (WorkspaceError, ConfigError, PathError, NotTextError)


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

    init = commands.add_parser("init", help=f"make the {ROOT_NAME} tree in this repository")
    init.set_defaults(handler=_init)

    new = commands.add_parser("new", help="start a change: its folder and its state file")
    new.add_argument("id", help="the change's name: lowercase words joined by hyphens")
    new.add_argument("--tier", choices=get_args(Tier), help="how much ceremony it gets (default: the config's)")
    new.set_defaults(handler=_new)

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
    propose.add_argument("--tier", choices=("lean", "standard"), help="how much ceremony (default: the model's call)")
    propose.add_argument("--no-input", action="store_true", help="ask no question: open points stay in the brief")
    propose.add_argument("--no-explore", action="store_true", help="read none of the repository's code for the plan")
    propose.set_defaults(handler=_propose)

    plan = commands.add_parser("plan", help="draft a change's tasks again, and its design where one is owed")
    plan.add_argument("id", help="the change")
    plan.add_argument("--replace", action="store_true", help="draft anew although a task of the list is ticked")
    plan.add_argument("--no-explore", action="store_true", help="read none of the repository's code for the plan")
    plan.set_defaults(handler=_drafting(_planned))

    check = commands.add_parser("check", help="check a change's files against each other, as `approve` does")
    check.add_argument("id", help="the change")
    check.add_argument("--no-model", action="store_true", help="run the checks code makes, and call no model")
    check.set_defaults(handler=_drafting(_reviewed))

    verify = commands.add_parser("verify", help="judge the work done against each requirement of a change")
    verify.add_argument("id", help="the change")
    verify.add_argument("--base", metavar="REF", help="the commit the work started from (default: the approval's)")
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
    workspace = Workspace.init(Path(args.root).absolute())
    made = workspace.shown(workspace.home)
    print(f'made {made}: write its constitution.md, then run `{PROG} propose "<what you want>"`')
    return EXIT_OK


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
        return next_step(self.state, self.findings, self.stale, check=self.unchecked, drifted=self.drifted)


def _assessed(workspace: Workspace, change_id: str, living: dict[str, Spec]) -> Assessed:
    loaded = workspace.load_change(change_id)
    unreadable = set(workspace.capabilities()) - set(living)  # a spec that is there and does not read
    found = _from_root(change_id, findings_of(loaded, living, unreadable))
    files = approval_files(workspace.approval_texts(change_id))
    seen = {**files, **_beside(workspace, loaded.change, living)}
    state = loaded.change.state
    unchecked = _from_root(change_id, check_blockers(state, seen))
    stale, drifted = approval_stale(state, files), _drifted(workspace, state)
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
    """Whether the work changed since a change was verified: its diff against the same commit is no longer the one
    that was judged. True too where the two cannot be compared. Asked of git for a verified change alone."""
    held = state.verification
    if state.status != "verified" or held is None:
        return False
    try:
        return sha256_of(diff(workspace.root, held.base, exclude=workspace.config().exclude)) != held.diff
    except GitError:
        return True


def _say_next(workspace: Workspace, change_id: str, living: dict[str, Spec]) -> None:
    """The line every command that changes a change ends on: what comes next, read from the files as they now are."""
    print(f"next      {_assessed(workspace, change_id, living).step.phrase}")


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
        assessed = _assessed(workspace, change_id, living)
        if assessed.state.status != "archived":  # an archived change is folded in: its delta has no base now
            found += assessed.findings
    stops = failed(found, strict=args.strict)
    if args.json:
        print(json.dumps({"findings": [held.model_dump() for held in found], "failed": stops}, indent=2))
        return EXIT_FINDINGS if stops else EXIT_OK
    _printed(found)
    errors = sum(held.severity == "ERROR" for held in found)
    print(f"{errors} errors, {sum(held.severity == 'WARNING' for held in found)} warnings")
    return EXIT_FINDINGS if stops else EXIT_OK


#: How `status` groups changes: by who makes the next step happen.
GROUPS = (("you", "Waiting on you"), ("run", "Ready to run"), ("done", "Done"))


def _status(args: argparse.Namespace) -> int:
    workspace = _workspace(args)
    living, _found = workspace.specs()
    rows = []
    for change_id in workspace.changes():
        assessed = _assessed(workspace, change_id, living)
        state, step = assessed.state, assessed.step
        if state.status == "archived" and not args.all:
            continue
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
    return EXIT_OK


def _rebase(args: argparse.Namespace) -> int:
    """Record the fingerprint each modified or removed requirement has in the living spec now. New bases void an
    approval, since it was given against the old ones; unchanged bases leave everything as it was."""
    workspace = _workspace(args)
    state = workspace.load_change(args.id).change.state
    if state.status == "archived":
        print(f"{PROG}: `{args.id}` is archived already: nothing to rebase", file=sys.stderr)
        return EXIT_FINDINGS
    living, of_specs = workspace.specs()
    if of_specs:  # a spec that does not read would pass for one not there, and every base on it would be dropped
        _printed(of_specs)
        print(f"{PROG}: `{args.id}` is not rebased: a living spec does not read. Fix it first", file=sys.stderr)
        return EXIT_FINDINGS
    held = capture_bases(workspace.load_change(args.id).change.deltas, living)
    for req_id in sorted(held):
        was = state.bases.get(req_id)
        print(f"{req_id}  {'recorded' if was is None else 'unchanged' if was == held[req_id] else 'was stale'}")
    for req_id in sorted(
        set(state.bases) - set(held)
    ):  # the delta no longer changes it, or the spec no longer holds it
        print(f"{req_id}  dropped")
    if held == state.bases:
        print("nothing to record: every base stands")
        return EXIT_OK
    workspace.save_state(state.model_copy(update={"bases": held, "status": "draft", "approval": None}))
    if state.approval is not None:
        print(f"the approval is void: read what was stale, then run `{PROG} approve {args.id}` again")
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


def _checked_first(workspace: Workspace, change_id: str, living: dict[str, Spec], assessed: Assessed) -> _Checked:
    """The check an approval makes of a change whose check is missing or stale, as `check` makes it. Where no
    provider is ready, the refusal names the way that needs none."""
    _load_env()
    try:
        return _check_made(workspace, change_id, living, assessed, no_model=False)
    except (UsageError, ContextTooLargeError) as exc:  # no provider, or more than a model is given to read
        raise UsageError(
            f"{exc}. `approve` checks a {assessed.state.tier} change first: put that right, or run "
            f"`{PROG} check {change_id} --no-model` and approve again"
        ) from exc


def _refused(change_id: str, blockers: list[Finding]) -> int:
    _printed(blockers)
    print(f"{PROG}: `{change_id}` is not approved: {len(blockers)} findings block it", file=sys.stderr)
    return EXIT_FINDINGS


def _approve(args: argparse.Namespace) -> int:
    """An approval, with what it needs done first: a base recorded where one is missing, and the check made where
    none is current. A person decides once; the tool's own work is no step of theirs."""
    workspace = _workspace(args)
    living, of_specs = workspace.specs()
    if of_specs:  # the code's check of coverage steps aside while a living spec is unread: nothing is approved so
        _printed(of_specs)
        raise NotYetError(f"`{args.id}` is not approved: a living spec does not read. Fix it first")
    _based(workspace, args.id, living)
    assessed = _assessed(workspace, args.id, living)
    # What the files themselves block comes first: no model is asked about files that are going to change.
    if blockers := approve_blockers(assessed.state, assessed.findings, strict=args.strict):
        return _refused(args.id, blockers)
    first = approval_checks_first(assessed.unchecked)
    if first:
        made = _checked_first(workspace, args.id, living, assessed)
        if made.failure:
            return _unfinished(f"the check did not finish, and nothing was approved: {made.failure}", made.ledger)
        blocking = [held for held in made.findings if held.severity == "ERROR"]
        _printed(blocking)
        count = len(made.findings)
        print(f"checked   {made.report}: {count} finding{'' if count == 1 else 's'}, {len(blocking)} blocking")
        print(f"tokens    {_spent(made.ledger)}")
        assessed = _assessed(workspace, args.id, living)
    # A reason sets aside only what a person was shown: a check recorded before this run, never one it made.
    if blockers := check_stops(assessed.unchecked, override=bool(args.override) and not first):
        if args.override and first:
            print(
                f"{PROG}: --override was not applied: this run made the check, so read what it found first, then "
                "approve again with --override",
                file=sys.stderr,
            )
        return _refused(args.id, blockers)
    files = assessed.files  # as they were read for the assessment that found the check current: no later read
    try:
        by = args.by or getpass.getuser()
    except OSError as exc:  # an account with no name, as in a container run under a bare user id
        raise UsageError("this account has no name: name the approver with --by") from exc
    at = datetime.now(UTC).isoformat(timespec="seconds")
    # A reason is recorded only where it set something aside: a blocking finding of the check.
    reason = args.override if any(held.code == "check.blocking" for held in assessed.unchecked) else None
    workspace.save_state(approve(assessed.state, files=files, by=by, at=at, override=reason, commit=_commit(workspace)))
    print(f"approved `{args.id}` by {by}: {len(files)} files recorded")
    _say_next(workspace, args.id, living)
    return EXIT_OK


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
        print(f"{PROG}: `{args.id}` is not archived, and no file was written", file=sys.stderr)
        if any(held.code == "delta.base-stale" for held in refused):
            print(
                f"{PROG}: the living spec changed after this delta was based on it: read the current requirement, "
                f"update the delta, then run {PROG} rebase and approve again",
                file=sys.stderr,
            )
        return EXIT_FINDINGS
    workspace.write_specs(merged, state=state.model_copy(update={"status": "archived"}))
    print(f"archived `{args.id}`: folded into {', '.join(sorted(merged)) or 'no spec'}")
    return EXIT_OK


# The commands that call a model, or log in to one.


def _env_file() -> Path | None:
    """The `.env` a run reads: the checkout's own, told by the `pyproject.toml` beside the package. An installed
    copy has none beside it and reads the shell alone, never a file that happens to stand near its packages."""
    return CHECKOUT / ".env" if (CHECKOUT / "pyproject.toml").is_file() else None


def _load_env() -> None:
    """The checkout's `.env` read into the environment, the shell winning over the file."""
    path = _env_file()
    if path is None:
        return
    from dotenv import load_dotenv

    try:
        load_dotenv(path, override=False, encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise UsageError(f"{path} is not UTF-8. Save it as UTF-8: Windows PowerShell 5.1's `>` writes UTF-16") from exc


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
    print(f"The brief leaves {points} open. A line answers. `=` takes the suggestion.")
    print("An empty line leaves the point open.")
    answers: list[str] = []
    ended = sys.stdin is None  # a process started with no terminal and no pipe
    for number, question in enumerate(questions, 1):
        print(f"{number}. {plain(question['question'])}")
        print(f"   suggested: {plain(question['suggested']) or '(none)'}", flush=True)
        line = "" if ended else _line()
        ended = ended or line == ""  # no line at all: the input is over
        typed = line.strip()
        if typed == "=" and not question["suggested"]:
            print("   nothing is suggested: the point stays open")
        answers.append(question["suggested"] if typed == "=" else typed)
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


def _propose(args: argparse.Namespace) -> int:
    _load_env()
    workspace = _workspace(args)
    if args.id:
        workspace.free(args.id)  # a name that cannot be taken is refused before anything is spent
    from ..orchestration.models import require_ready

    # Every role of the whole command, asked before anything is spent. A tier given by hand is not asked of triage.
    drafting = ("brief", "deltas", "design", "tasks", *(() if args.no_explore else ("scout", "survey")))
    if why := require_ready(roles=drafting if args.tier else ("triage", *drafting)):
        raise UsageError(why)
    with lock_held(workspace):
        return _proposed(args, workspace)


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
    change_id: str,
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
        answer = read(run.state)
        failure = run.state.get(FAILURE) or run.failure or (answer if isinstance(answer, str) else None)
        kept.outcome = f"failed: {failure}" if failure else "answered"
    return run, (None if failure else answer), ledger, (str(failure) if failure else None)


def _unfinished(sentence: str, ledger: Any) -> int:
    """How a command ends where its model pass gave no answer to use: the sentence, what was spent, and the
    engine's code."""
    print(f"{PROG}: {sentence}", file=sys.stderr)
    print(f"tokens    {_spent(ledger)}")
    return EXIT_ENGINE


def _deltas_text(change: Any) -> str:
    """A change's deltas as a stage reads them: each as its file, in the order of their capabilities."""
    return "\n".join(render_delta(delta) for _capability, delta in sorted(change.deltas.items()))


def _of_tasks(found: Finding) -> bool:
    """Whether a finding is about the task list alone, which `plan` is about to replace."""
    return found.code.startswith("tasks.") or (found.path or "").rsplit("/", 1)[-1] == TASKS_FILE


def _source(workspace: Workspace) -> Source | None:
    """The repository's files, as git lists them once for a command, less what a person excluded: what a stage is
    shown the names of, and what a reading of the code is made through. None where there is no repository here, or
    no git to ask."""
    try:
        return Source.of(workspace.root, exclude=workspace.config().exclude)
    except GitError:
        return None


#: A ticked box of a task list, wherever its line stands: read in the text of a list that no longer parses.
_TICKED = re.compile(r"(?m)^\s*-\s*\[[xX]\]")


def _plannable(
    change_id: str, replace: bool, workspace: Workspace, assessed: Assessed, of_specs: list[Finding]
) -> Brief:
    """The brief of a change that is to be planned now. `NotYetError` where it is not: it is no draft, work on its
    task list has begun and replacing it was not asked for, or what the tasks are drafted from does not read."""
    change, state = assessed.loaded.change, assessed.state
    if state.status != "draft":  # new tasks would void what was approved
        raise NotYetError(f"`{change_id}` is {state.status}: a plan is drafted while a change is a draft")
    started = sum(task.done for group in change.tasks or () for task in group.tasks)
    if change.tasks is None:  # a list off its grammar reads as none: its boxes are counted in its text
        started = len(_TICKED.findall(workspace.approval_texts(change_id).get(TASKS_FILE, "")))
    if started and not replace:  # work has begun on this list: it is not thrown away unasked
        raise NotYetError(
            f"`{change_id}` has {started} of its tasks ticked. A new plan would replace the list: run "
            f"`{PROG} plan {change_id} --replace` if that is meant"
        )
    if of_specs:  # a task may serve a requirement of any living spec: which exist is unknown while one is unread
        _printed(of_specs)
        raise NotYetError(f"`{change_id}` is not planned: a living spec does not read. Fix it first")
    # What must be right before tasks are worth drafting: everything but the tasks themselves.
    blocking = [held for held in assessed.findings if held.severity == "ERROR" and not _of_tasks(held)]
    if blocking or change.brief is None:
        _printed(blocking)
        raise NotYetError(f"`{change_id}` is not planned: its brief and deltas have errors. Fix them first")
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

    roles = ("design", "tasks") if state.needs_design else ("tasks",)
    if why := require_ready(roles=roles):
        raise UsageError(why)
    from ..orchestration.graph import build_plan_app
    from ..orchestration.plugins import UsageLedger
    from ..orchestration.stages import BRIEF_TEXT, CONTEXT_TEXT, DELTAS_TEXT, LIVING, TREE
    from ..orchestration.stages import CONSTITUTION as RULES
    from ..orchestration.stages.design import read_design
    from ..orchestration.stages.tasks import DESIGN_TEXT, read_tasks

    source = _source(workspace)
    seed = {
        RULES: constitution_text(workspace),
        BRIEF_TEXT: render_brief(brief),
        DELTAS_TEXT: _deltas_text(change),
        LIVING: living_text(specs, sorted(change.deltas)),
        TREE: tree_text(source.paths) if source else "",
    }
    if change.design and not state.needs_design:  # a design a person wrote, where the brief owed none
        seed[DESIGN_TEXT] = change.design.strip()
    serves = {"owed": owed(change.deltas), "nameable": nameable(change.deltas, specs)}
    if ledger is None:  # one ceiling for the reading and the drafting: they are one command's
        ledger = UsageLedger(workspace.config().max_tokens or None)
    said, context = _read_code(workspace, change_id, seed, ledger, source) if explore else ("", None)
    seed[CONTEXT_TEXT] = context_text(workspace, change_id)
    read = [(context, False)] if context else []

    def build(ledger: Any, recorder: Any) -> Any:
        return build_plan_app(design=state.needs_design, ledger=ledger, recorder=recorder, **serves)

    run, tasks, ledger, failure = _asked(workspace, "plan", change_id, build, seed, read_tasks, ledger=ledger)
    if failure:
        return _Planned(ledger=ledger, failure=failure, explored=said)
    files = {TASKS_FILE: render_tasks(to_tasks(tasks))}
    design = read_design(run.state) if state.needs_design else None
    if design is not None and not isinstance(design, str):
        files = {DESIGN_FILE: render_design(design), **files}  # the design first: it is what a person reads first
    folder = workspace.home / CHANGES / change_id
    there = {name for name in files if (folder / name).is_file()}
    paths = workspace.write_into(change_id, files)
    drafted = [(path, name in there) for name, path in zip(files, paths, strict=True)]
    return _Planned([*read, *drafted], ledger, explored=said)


def _read_code(
    workspace: Workspace, change_id: str, seed: dict[str, Any], ledger: Any, source: Source | None
) -> tuple[str, Path | None]:
    """The repository's code read for a change, through `source`, and `context.md` written from what was kept:
    what to say of it, and the file where one was written. Nothing is read where the change has a `context.md`
    already, which is then a person's to keep, or where there is no repository or no file in it.

    A reading never stops a plan: one that fails, or keeps nothing, is said in a line, and the plan is drafted
    without it. One that ends early writes what it kept and says that it is partial."""
    kept = workspace.home / CHANGES / change_id / CONTEXT_FILE
    if kept.is_file():
        # A reading that ended early is said each time it is used: nothing else would show that it is no whole one.
        early = PARTIAL in context_text(workspace, change_id)
        return ("kept: context.md is of a reading that ended early. Delete it to read again" if early else ""), None
    if source is None or not source.paths:
        return "", None
    from ..orchestration.explore import build_explore_app, explored
    from ..orchestration.models import require_ready
    from ..orchestration.stages import BRIEF_TEXT, DELTAS_TEXT, TREE
    from ..orchestration.stages import CONSTITUTION as RULES

    if why := require_ready(roles=("scout", "survey")):
        raise UsageError(why)

    def build(ledger: Any, recorder: Any) -> Any:
        return build_explore_app(source=source, ledger=ledger, recorder=recorder)

    reading = {key: seed[key] for key in (RULES, BRIEF_TEXT, DELTAS_TEXT, TREE)}
    nothing_to_read_back = lambda _state: None  # noqa: E731 -- what a reading kept is in its state, also where it failed
    run, _none, _ledger, failure = _asked(
        workspace, "explore", change_id, build, reading, nothing_to_read_back, ledger=ledger
    )
    found = explored(run.state)
    if not found.statements:
        nothing = "nothing the scout named could be read" if not found.read else "no statement quoted what was read"
        return f"nothing: {failure or nothing}", None
    at = datetime.now(UTC).isoformat(timespec="seconds")
    text = render_context(
        change_id,
        at=at,
        commit=_commit(workspace),
        statements=found.statements,
        read=found.read,
        left_out=found.left_out,
        dropped=found.dropped,
        partial=failure,
    )
    (path,) = workspace.write_into(change_id, {CONTEXT_FILE: text})
    files, kept = len(found.read), len(found.statements)
    said = f"{files} file{'' if files == 1 else 's'}: {kept} statement{'' if kept == 1 else 's'} kept"
    said += f", {found.dropped} left out" if found.dropped else ""
    return said + (f"; it ended early: {failure}" if failure else ""), path


def _planned(args: argparse.Namespace, workspace: Workspace) -> int:
    """The `plan` command: the plan drafted, and what was written said."""
    specs, of_specs = workspace.specs()
    made = _plan_made(workspace, args.id, specs, of_specs, replace=args.replace, explore=not args.no_explore)
    if made.explored:
        print(f"explored  {made.explored}")
    if made.failure:
        return _unfinished(f"no plan was written: {made.failure}", made.ledger)
    for path, replaced in made.written:
        print(f"{'replaced' if replaced else 'wrote':<10}{workspace.shown(path)}")
    print(f"tokens    {_spent(made.ledger)}")
    _say_next(workspace, args.id, specs)
    return EXIT_OK


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
    report = render_check(change_id, at, _inside(change_id, every), model=model, dropped=dropped)
    path = workspace.write_report(change_id, "check.md", report)
    read = {**approval_files(texts), **_beside(workspace, assessed.loaded.change, specs)}
    workspace.save_state(checked(assessed.state, every, files=read, at=at, model=model))
    return _Checked(every, workspace.shown(path), dropped, ledger)


def _reviewed(args: argparse.Namespace, workspace: Workspace) -> int:
    """The `check` command: the check made, and what it found said."""
    specs, of_specs = workspace.specs()
    if of_specs:  # which requirements exist is unknown while a living spec is unread: coverage cannot be checked
        _printed(of_specs)
        raise NotYetError(f"`{args.id}` is not checked: a living spec does not read. Fix it first")
    assessed = _assessed(workspace, args.id, specs)
    if assessed.state.status == "archived":
        raise NotYetError(f"`{args.id}` is archived: there is nothing left to check")
    held = assessed.state.check
    if args.no_model and held is not None and check_stands(assessed.state, assessed.seen):
        print(
            f"{PROG}: the check of `{args.id}` by {held.model} stands, with {held.blocking} blocking: its files have "
            "not changed since, and a check by code alone does not replace it",
            file=sys.stderr,
        )
        return EXIT_FINDINGS if held.blocking else EXIT_OK
    if any(held.severity == "ERROR" for held in assessed.findings):
        print(f"{PROG}: fix what the check lists first: the model's pass waits for files that read", file=sys.stderr)
    made = _check_made(workspace, args.id, specs, assessed, no_model=args.no_model)
    if made.failure:
        return _unfinished(f"the check did not finish, and nothing was recorded: {made.failure}", made.ledger)
    _printed(made.findings)
    print(f"wrote     {made.report}")
    if made.dropped:
        print(f"note      {left_out(made.dropped)}")
    if made.ledger is not None:
        print(f"tokens    {_spent(made.ledger)}")
    _say_next(workspace, args.id, specs)
    return EXIT_FINDINGS if any(held.severity == "ERROR" for held in made.findings) else EXIT_OK


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


def _work(args: argparse.Namespace, workspace: Workspace, state: ChangeState) -> tuple[str, str, tuple[str, ...]]:
    """The commit a change's work is compared with, the diff from it to the working tree as a stage may be shown
    it, and the files left out of that diff for holding a private key. `UsageError` where there is nothing to
    compare with; `NotYetError` where nothing was done that can be shown."""
    cid, root = state.id, workspace.root
    if not is_repository(root):
        raise UsageError(f"{root} is in no git repository: verify reads what changed since the approval")
    named = args.base or state.base_commit
    if not named:
        raise UsageError(
            f"no commit was recorded when `{cid}` was first approved. Name the commit the work started from with --base"
        )
    base = resolves(root, named)
    if base is None:
        raise UsageError(f"`{named}` names no commit in this repository")
    exclude = workspace.config().exclude
    # A file that holds a private key is no part of the work a model is shown, as an excluded path is none.
    text, held = Source.of(root, exclude=exclude).without_keys(diff(root, base, exclude=exclude))
    if not text.strip():
        beside = f"{_key_files(held, ' ')}, and nothing else" if held else "nothing"
        raise NotYetError(f"{beside} under {root} changed since {base[:12]}: there is nothing to verify")
    if len(text) > DIFF_MAX_CHARS:
        raise UsageError(
            f"the diff since {base[:12]} holds {len(text):,} characters, past the {DIFF_MAX_CHARS:,} a stage is "
            "given. It is never cut. Verify a smaller change, or name a later commit with --base"
        )
    return base, text, held


def _verified(args: argparse.Namespace, workspace: Workspace) -> int:
    """The work judged against the change's requirements, one verdict each. The report is written and the
    verification recorded; the change is `verified` where every requirement is shown met, or a person says so
    with a reason."""
    specs, _of_living = workspace.specs()
    assessed = _assessed(workspace, args.id, specs)
    change, state = assessed.loaded.change, assessed.state
    if why := verify_blockers(state, assessed.stale):
        raise NotYetError(why[0])
    base, text, held = _work(args, workspace, state)
    if held:
        print(f"left out  {_key_files(held, ': ')}")
    added, gone = owed(change.deltas), removed(change.deltas)
    verdicts: list[Verdict] = []
    ledger, model = None, None
    if added or gone:  # a change with no delta has no requirement to judge
        from ..orchestration.models import serving

        verdicts, ledger, failure = _verdicts(workspace, change, text, added, gone)
        if failure:
            return _unfinished(f"the verification did not finish, and nothing was recorded: {failure}", ledger)
        model = serving("verify")
    at = datetime.now(UTC).isoformat(timespec="seconds")
    said = {one.id: one.verdict for one in verdicts}
    after = verified(state, said, base=base, diff=sha256_of(text), at=at, model=model, override=args.override)
    reason = after.verification.override if after.verification else None
    report = render_verify(args.id, at, base, verdicts, model=model, override=reason)
    path = workspace.write_report(args.id, "verify.md", report)
    workspace.save_state(after)
    for one in verdicts:
        print(f"{one.verdict:<8}  {one.id}  {one.reason}")
    print(f"wrote     {workspace.shown(path)}")
    if ledger is not None:
        print(f"tokens    {_spent(ledger)}")
    _say_next(workspace, args.id, specs)
    return EXIT_OK if after.status == "verified" else EXIT_FINDINGS


def _verdicts(
    workspace: Workspace, change: Any, text: str, added: frozenset[str], gone: frozenset[str]
) -> tuple[list[Verdict], Any, str | None]:
    """The model's verdicts on a diff, each held to the lines the diff really holds; the ledger; and the failure,
    where the run did not end well."""
    from ..orchestration.models import require_ready

    if why := require_ready(roles=("verify",)):
        raise UsageError(why)
    from ..orchestration.graph import build_verify_app
    from ..orchestration.stages import DELTAS_TEXT
    from ..orchestration.stages.verify import DIFF, REQUIRED, TASKS_TEXT, read_verify, required_text

    # As in a check: the diff a model is shown and the diff its evidence is looked for in are one text, scrubbed
    # once. The fingerprint of the work is of the diff as it stands, and is taken where the diff is cut.
    text = scrub_lines(text)[0]
    seed = {
        DELTAS_TEXT: _deltas_text(change),
        TASKS_TEXT: render_tasks(change.tasks) if change.tasks else "",
        REQUIRED: required_text(added, gone),
        DIFF: text,
    }

    def build(ledger: Any, recorder: Any) -> Any:
        return build_verify_app(ledger=ledger, required=added | gone, recorder=recorder)

    _run, answer, ledger, failure = _asked(workspace, "verify", change.state.id, build, seed, read_verify)
    if failure:
        return [], ledger, failure
    return grounded(answer, text, added=added, removed=gone), ledger, None


def _proposed(args: argparse.Namespace, workspace: Workspace) -> int:
    from ..orchestration.gate import FAILURE
    from ..orchestration.graph import Known
    from ..orchestration.plugins import UsageLedger
    from ..orchestration.stages import CAPABILITIES, REQUEST, TIER
    from ..orchestration.stages import CONSTITUTION as RULES
    from ..orchestration.stages.brief import KEY as BRIEF_KEY
    from ..orchestration.stages.deltas import KEY as DELTAS_KEY
    from ..orchestration.stages.triage import read_triage

    specs, of_specs = workspace.specs()
    if of_specs:  # a spec that does not read would pass for a capability not yet there
        _printed(of_specs)
        print(f"{PROG}: nothing was drafted: a living spec does not read. Fix it first", file=sys.stderr)
        return EXIT_FINDINGS
    known = Known(living=specs, taken=frozenset(workspace.taken(specs)))
    # One ledger for every run of this command: the count and the ceiling are the command's.
    ledger = UsageLedger(workspace.config().max_tokens or None)
    seed = {REQUEST: args.request, CAPABILITIES: capability_index(specs), RULES: constitution_text(workspace)}
    with _recording(workspace, "propose", args.id) as kept:
        state = _rounds(args, known, ledger, kept.recorder, seed)
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
            kept.change = _written(args, workspace, known, state, tier)
        except WorkspaceError as exc:  # the calls are paid for by now: say so beside the refusal
            kept.outcome = f"failed: {exc}"
            print(f"{PROG}: no change was written: {exc}", file=sys.stderr)
            print(f"tokens    {_spent(ledger)}")
            return EXIT_USAGE
        kept.outcome = "written"
    change_id = kept.change or ""
    # An open point comes before the plan, since its answer shapes the tasks: none is drafted on a guess.
    waiting = [held for held in _assessed(workspace, change_id, specs).findings if held.code == _OPEN_POINT]
    if waiting:
        count = len(waiting)
        print(f"tokens    {_spent(ledger)}")
        print(f"plan      waits: the brief leaves {count} point{'' if count == 1 else 's'} open")
        _say_next(workspace, change_id, specs)
        return EXIT_OK
    # The plan, in the same command and under the same ceiling. The change is written by now: a plan that does not
    # end well leaves it a draft, and `plan` finishes it.
    try:
        made = _plan_made(
            workspace, change_id, specs, of_specs, replace=False, ledger=ledger, explore=not args.no_explore
        )
    except NotYetError as exc:  # the calls so far are paid for: what stopped the plan is said as any other failure
        made = _Planned(ledger=ledger, failure=str(exc))
    if made.explored:
        print(f"explored  {made.explored}")
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


#: The finding of a point a brief leaves open, which holds a plan back.
_OPEN_POINT = "brief.marker-unresolved"


def _first_reads(workspace: Workspace, change_id: str) -> str:
    """What a person reads first of a change, each with its length: the brief, and the design where there is one.
    Review counts most there, early and short; the task list follows from the two."""
    texts = workspace.approval_texts(change_id)
    return " and ".join(
        f"{name} ({len(lines_of(texts[name]))} lines)" for name in (BRIEF_FILE, DESIGN_FILE) if name in texts
    )


def _rounds(args: argparse.Namespace, known: Any, ledger: Any, recorder: Any, seed: dict[str, Any]) -> dict[str, Any]:
    """The runs of one `propose`, and the state the last of them left, a failure of the engine's own under the
    gate's key: the first run, then one more for each round of questions. A run ends on its questions and the
    person answers here, between two runs. Run on the pinned engine: a run paused and resumed runs again, unseen,
    any stage that had answered off its schema. Which run comes next, and seeded with what, is the graph's to say."""
    from ..orchestration.gate import FAILURE
    from ..orchestration.graph import ASKING, build_propose_app, first_run, next_run

    entry, seed = first_run(args.tier, seed)
    while True:
        app = build_propose_app(known, ask=not args.no_input, entry=entry, ledger=ledger, recorder=recorder)
        run = _ran(app, seed, "propose")
        state = {**run.state, FAILURE: run.state.get(FAILURE) or run.failure}
        if state[FAILURE] or state.get(ASKING) is None:
            return state
        if why := ledger.refusal():  # asking costs no call, so nothing else would stop it: no answer could be used
            return {**state, FAILURE: f"{why}, and the brief's open points were not put to you"}
        entry, seed = next_run(seed, state, _answered(state[ASKING]))


def _written(args: argparse.Namespace, workspace: Workspace, known: Any, state: dict[str, Any], tier: Tier) -> str:
    """The change a run drafted, written whole: its id."""
    from ..orchestration.graph import drafted, files_of

    made = drafted(state, known)
    change_id = args.id or slug_of(made.brief.title, workspace.names_held())
    held = ChangeState(
        id=change_id, tier=tier, bases=capture_bases(made.deltas, known.living), needs_design=made.needs_design
    )
    files = files_of(made)
    folder = workspace.write_change(held, files)
    print(f"wrote     {workspace.shown(folder)}, a {tier} draft")
    for path in files:
        print(f"          {workspace.shown(folder)}/{path}")
    return change_id


def _login(args: argparse.Namespace) -> int:
    """The Copilot login, which reads the checkout's `.env` for an enterprise tenant's endpoints as a run does."""
    _load_env()
    from .login import main as login

    return login(["--force"] if args.force else [])


def _models(args: argparse.Namespace) -> int:
    _load_env()
    from ..orchestration.catalog import CatalogError, list_models, shown
    from ..orchestration.models import require_ready

    if why := require_ready():
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
        print(f"{PROG}: interrupted", file=sys.stderr)
        return EXIT_INTERRUPTED
