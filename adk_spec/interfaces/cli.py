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
import sys
from collections.abc import Callable, Generator
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any, NoReturn, get_args

from ..domain.brief_md import render_brief
from ..domain.check import nameable, owed
from ..domain.convert import render_design, slug_of, to_findings, to_tasks
from ..domain.delta_md import render_delta
from ..domain.lifecycle import (
    approval_files,
    approval_stale,
    approve,
    approve_blockers,
    archive_blockers,
    capture_bases,
    check_blockers,
    next_action,
)
from ..domain.merge import MergeError, apply_delta
from ..domain.model import ChangeState, Checked, Finding, Spec, Tier, Verification
from ..domain.report_md import render_check, render_verify
from ..domain.tasks_md import render_tasks
from ..domain.text import sha256_of
from ..domain.validate import failed, finding, validate_spec
from ..domain.verify import Verdict, grounded
from ..workspace.config import ConfigError
from ..workspace.context import (
    CONSTITUTION_MAX_CHARS,
    capability_index,
    constitution_text,
    files_text,
    living_text,
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
from ..workspace.layout import DESIGN as DESIGN_FILE
from ..workspace.layout import TASKS as TASKS_FILE
from ..workspace.lock import held as lock_held
from ..workspace.paths import PathError
from ..workspace.runs import Recording
from ..workspace.runs import write as write_run

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


def _parser() -> argparse.ArgumentParser:
    parser = _Parser(prog=PROG, description="Spec-driven development on Google ADK.")
    parser.add_argument("--version", action="version", version=f"{PROG} {metadata.version('adk-spec')}")
    parser.add_argument("--root", default=".", help="a folder in the repository to work in (default: this one)")
    commands = parser.add_subparsers(metavar="command", parser_class=_Parser)

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

    rebase = commands.add_parser("rebase", help="record what a change's deltas are written against")
    rebase.add_argument("id", help="the change")
    rebase.set_defaults(handler=_locked(_rebase))

    approval = commands.add_parser("approve", help="record an approval of a change's files as they stand")
    approval.add_argument("id", help="the change")
    approval.add_argument("--by", help="who approves: a recorded claim, not an authentication (default: this account)")
    approval.add_argument("--strict", action="store_true", help="refuse on a warning too")
    approval.add_argument(
        "--override", metavar="REASON", help="approve although the check found something blocking, and record why"
    )
    approval.set_defaults(handler=_locked(_approve))

    archive = commands.add_parser("archive", help="fold an approved change's deltas into the living specs")
    archive.add_argument("id", help="the change")
    archive.set_defaults(handler=_locked(_archive))

    propose = commands.add_parser("propose", help="draft a change from a request: its brief and its deltas")
    propose.add_argument("request", help="what is wanted, in a sentence or a paragraph")
    propose.add_argument("--id", help="the change's name (default: made from the brief's title)")
    propose.add_argument("--tier", choices=("lean", "standard"), help="how much ceremony (default: the model's call)")
    propose.add_argument("--no-input", action="store_true", help="ask no question: open points stay in the brief")
    propose.set_defaults(handler=_propose)

    plan = commands.add_parser("plan", help="draft a change's tasks, and its design where one is owed")
    plan.add_argument("id", help="the change")
    plan.set_defaults(handler=_plan)

    check = commands.add_parser("check", help="check a change's files against each other, before it is approved")
    check.add_argument("id", help="the change")
    check.add_argument("--no-model", action="store_true", help="run the checks code makes, and call no model")
    check.set_defaults(handler=_check)

    verify = commands.add_parser("verify", help="judge what changed in the repository against a change's requirements")
    verify.add_argument("id", help="the change")
    verify.add_argument("--base", metavar="REF", help="the commit the work started from (default: the approval's)")
    verify.add_argument(
        "--override", metavar="REASON", help="verify although a requirement is not shown met, and record why"
    )
    verify.set_defaults(handler=_verify)

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
    except (UsageError, *REFUSALS) as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except OSError as exc:  # a file held open, a folder that cannot be written: said, and never the code for findings
        where = f" {exc.filename}" if exc.filename else ""
        print(f"{PROG}: could not read or write{where}: {exc.strerror or exc}", file=sys.stderr)
        return EXIT_ENGINE


# The commands that call no model.


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
    print(f"made {workspace.shown(workspace.home)}: write its constitution.md, then run `{PROG} new <id>`")
    return EXIT_OK


def _new(args: argparse.Namespace) -> int:
    workspace = _workspace(args)
    tier = args.tier or workspace.config().default_tier
    folder = workspace.new_change(args.id, tier)
    print(f"made {workspace.shown(folder)}, a {tier} draft: write its brief.md, its deltas and its tasks.md")
    return EXIT_OK


def _from_root(change_id: str, found: list[Finding]) -> list[Finding]:
    """Findings about a change's files, each with its path from the repository's root."""
    prefix = f"{ROOT_NAME}/{CHANGES}/{change_id}/"
    return [held.model_copy(update={"path": prefix + (held.path or "")}) for held in found]


def _assessed(
    workspace: Workspace, change_id: str, living: dict[str, Spec]
) -> tuple[LoadedChange, list[Finding], list[str], list[Finding]]:
    """A change as every command reads it: loaded, its findings with their paths from the root, what its approval
    no longer covers, and what its check still owes an approval."""
    loaded = workspace.load_change(change_id)
    unreadable = set(workspace.capabilities()) - set(living)  # a spec that is there and does not read
    found = _from_root(change_id, findings_of(loaded, living, unreadable))
    files = approval_files(workspace.approval_texts(change_id))
    stale = approval_stale(loaded.change.state, files)
    return loaded, found, stale, _from_root(change_id, check_blockers(loaded.change.state, files))


def _of_specs(workspace: Workspace) -> tuple[dict[str, Spec], list[Finding]]:
    """The living specs that read, and every finding of the living specs, with its path from the root."""
    living, found = workspace.specs()
    for capability, spec in sorted(living.items()):
        path = f"{ROOT_NAME}/{SPECS}/{capability}/{SPEC_FILE}"
        found += [held.model_copy(update={"path": path}) for held in validate_spec(spec)]
    return living, found


def _printed(found: list[Finding]) -> None:
    for held in found:
        place = f"{held.path}:{held.line}" if held.line else (held.path or "")
        print(f"{held.severity} {held.code} {place}  {held.message}")


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
        loaded, of_change, _stale, _owed = _assessed(workspace, change_id, living)
        if loaded.change.state.status != "archived":  # an archived change is folded in: its delta has no base now
            found += of_change
    stops = failed(found, strict=args.strict)
    if args.json:
        print(json.dumps({"findings": [held.model_dump() for held in found], "failed": stops}, indent=2))
        return EXIT_FINDINGS if stops else EXIT_OK
    _printed(found)
    errors = sum(held.severity == "ERROR" for held in found)
    print(f"{errors} errors, {sum(held.severity == 'WARNING' for held in found)} warnings")
    return EXIT_FINDINGS if stops else EXIT_OK


def _status(args: argparse.Namespace) -> int:
    workspace = _workspace(args)
    living, _found = workspace.specs()
    rows = []
    for change_id in workspace.changes():
        loaded, found, stale, owed = _assessed(workspace, change_id, living)
        state = loaded.change.state
        if state.status == "archived" and not args.all:
            continue
        step = next_action(state, found, stale, check=owed)
        rows.append({"id": change_id, "tier": state.tier, "status": state.status, "next": step})
    if args.json:
        print(json.dumps({"changes": rows}, indent=2))
    elif not rows:
        print(f"no open changes: run {PROG} new <id>")
    else:
        width = max(len(row["id"]) for row in rows)
        for row in rows:
            print(f"{row['id']:<{width}}  {row['tier']:<8}  {row['status']:<8}  {row['next']}")
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


def _approve(args: argparse.Namespace) -> int:
    workspace = _workspace(args)
    living, _found = workspace.specs()
    loaded, found, _stale, owed = _assessed(workspace, args.id, living)
    # A reason given sets a blocking finding of the check aside, and nothing else: a check never run, or run on
    # other files, is still owed.
    overridden = bool(args.override) and any(held.code == "check.blocking" for held in owed)
    blockers = approve_blockers(loaded.change.state, found, strict=args.strict)
    blockers += [held for held in owed if not (overridden and held.code == "check.blocking")]
    if blockers:
        _printed(blockers)
        print(f"{PROG}: `{args.id}` is not approved: {len(blockers)} findings block it", file=sys.stderr)
        return EXIT_FINDINGS
    files = approval_files(workspace.approval_texts(args.id))
    try:
        by = args.by or getpass.getuser()
    except OSError as exc:  # an account with no name, as in a container run under a bare user id
        raise UsageError("this account has no name: name the approver with --by") from exc
    at = datetime.now(UTC).isoformat(timespec="seconds")
    override = args.override if overridden else None
    recorded = approve(loaded.change.state, files=files, by=by, at=at, override=override, commit=_commit(workspace))
    workspace.save_state(recorded)
    print(f"approved `{args.id}` by {by}: {len(files)} files recorded")
    return EXIT_OK


def _commit(workspace: Workspace) -> str | None:
    """The commit checked out where an approval is made, or nothing: no repository here, or no git to ask."""
    try:
        return head(workspace.root) if is_repository(workspace.root) else None
    except GitError:
        return None


def _archive(args: argparse.Namespace) -> int:
    """Every capability's merge is computed before any file is written, and the merged specs and the change's state
    are then written as one set: all of them, or none as far as the file system allows."""
    workspace = _workspace(args)
    living, of_specs = workspace.specs()
    loaded, _found, stale, _owed = _assessed(workspace, args.id, living)
    state = loaded.change.state
    if blockers := archive_blockers(state, stale):
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


def _plain(text: str) -> str:
    """A model's text as a terminal may be handed it: every character that is no printable one, an escape or a bell
    among them, shown as a space."""
    return "".join(char if char.isprintable() else " " for char in text)


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
        print(f"{number}. {_plain(question['question'])}")
        print(f"   suggested: {_plain(question['recommended'])}", flush=True)
        line = "" if ended else _line()
        ended = ended or line == ""  # no line at all: the input is over
        typed = line.strip()
        answers.append(question["recommended"] if typed == "=" else typed)
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
    kept = _Kept(Recorder(), change)
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

    drafting = ("brief", "questions", "deltas")  # a tier given by hand is not asked of triage
    if why := require_ready(roles=drafting if args.tier else ("triage", *drafting)):
        raise UsageError(why)
    with lock_held(workspace):
        return _proposed(args, workspace)


def _plan(args: argparse.Namespace) -> int:
    _load_env()
    workspace = _workspace(args)
    with lock_held(workspace):
        return _planned(args, workspace)


def _of_tasks(found: Finding) -> bool:
    """Whether a finding is about the task list alone, which `plan` is about to replace."""
    return found.code.startswith("tasks.") or (found.path or "").rsplit("/", 1)[-1] == TASKS_FILE


def _planned(args: argparse.Namespace, workspace: Workspace) -> int:
    specs, _of_living = workspace.specs()
    loaded, found, _stale, _owed = _assessed(workspace, args.id, specs)
    change, state = loaded.change, loaded.change.state
    if state.status != "draft":  # new tasks would void what was approved
        print(f"{PROG}: `{args.id}` is {state.status}: a plan is drafted while a change is a draft", file=sys.stderr)
        return EXIT_FINDINGS
    # What must be right before tasks are worth drafting: everything but the tasks themselves.
    blocking = [held for held in found if held.severity == "ERROR" and not _of_tasks(held)]
    if blocking or change.brief is None:
        _printed(blocking)
        print(f"{PROG}: `{args.id}` is not planned: its brief and deltas have errors. Fix them first", file=sys.stderr)
        return EXIT_FINDINGS
    from ..orchestration.models import require_ready

    roles = ("design", "tasks") if state.needs_design else ("tasks",)
    if why := require_ready(roles=roles):
        raise UsageError(why)
    from ..orchestration.gate import FAILURE
    from ..orchestration.graph import build_plan_app
    from ..orchestration.plugins import UsageLedger
    from ..orchestration.stages import BRIEF_TEXT, DELTAS_TEXT, LIVING
    from ..orchestration.stages import CONSTITUTION as RULES
    from ..orchestration.stages.design import read_design
    from ..orchestration.stages.tasks import read_tasks

    seed = {
        RULES: constitution_text(workspace),
        BRIEF_TEXT: render_brief(change.brief),
        DELTAS_TEXT: "\n".join(render_delta(delta) for _capability, delta in sorted(change.deltas.items())),
        LIVING: living_text(specs, sorted(change.deltas)),
    }
    ledger = UsageLedger(workspace.config().max_tokens or None)
    serves = {"owed": owed(change.deltas), "nameable": nameable(change.deltas, specs)}
    with _recording(workspace, "plan", args.id) as kept:
        app = build_plan_app(design=state.needs_design, ledger=ledger, recorder=kept.recorder, **serves)
        run = _ran(app, seed, "plan")
        tasks = read_tasks(run.state)
        failure = run.state.get(FAILURE) or run.failure or (tasks if isinstance(tasks, str) else None)
        kept.outcome = f"failed: {failure}" if failure else "written"
    if failure or isinstance(tasks, str):
        print(f"{PROG}: no plan was written: {failure}", file=sys.stderr)
        print(f"tokens    {_spent(ledger)}")
        return EXIT_ENGINE
    files = {TASKS_FILE: render_tasks(to_tasks(tasks))}
    design = read_design(run.state) if state.needs_design else None
    if design is not None and not isinstance(design, str):
        files[DESIGN_FILE] = render_design(design)
    for path in workspace.write_into(args.id, files):
        print(f"wrote     {workspace.shown(path)}")
    print(f"tokens    {_spent(ledger)}")
    loaded, found, stale, unchecked = _assessed(workspace, args.id, specs)
    print(f"next      {next_action(loaded.change.state, found, stale, check=unchecked)}")
    return EXIT_OK


def _check(args: argparse.Namespace) -> int:
    _load_env()
    workspace = _workspace(args)
    with lock_held(workspace):
        return _reviewed(args, workspace)


def _reviewed(args: argparse.Namespace, workspace: Workspace) -> int:
    """A change's files checked against each other: by code always, and by a model where the files read and the
    person did not say otherwise. The report is written and the check recorded with the fingerprints of what was
    read; where the model's pass does not end well, neither is."""
    specs, _of_living = workspace.specs()
    loaded, found, _stale, _owed = _assessed(workspace, args.id, specs)
    state = loaded.change.state
    if state.status == "archived":
        print(f"{PROG}: `{args.id}` is archived: there is nothing left to check", file=sys.stderr)
        return EXIT_FINDINGS
    texts = workspace.approval_texts(args.id)
    judged: list[Finding] = []
    dropped, ledger, model = 0, None, None
    if any(held.severity == "ERROR" for held in found):
        print(f"{PROG}: fix what the check lists first: the model's pass waits for files that read", file=sys.stderr)
    elif not args.no_model:
        from ..orchestration.models import serving

        judged, dropped, ledger, failure = _judged(workspace, loaded.change, specs, texts)
        if failure:
            print(f"{PROG}: the check did not finish, and nothing was recorded: {failure}", file=sys.stderr)
            print(f"tokens    {_spent(ledger)}")
            return EXIT_ENGINE
        model = serving("check")
    at = datetime.now(UTC).isoformat(timespec="seconds")
    every = [*found, *_from_root(args.id, judged)]
    blocking = sum(held.severity == "ERROR" for held in every)
    inside_change = [held.model_copy(update={"path": (held.path or "").split(f"/{args.id}/", 1)[-1]}) for held in every]
    report = workspace.write_report(
        args.id, "check.md", render_check(args.id, at, inside_change, model=model, dropped=dropped)
    )
    held = Checked(at=at, files=approval_files(texts), blocking=blocking, model=model)
    workspace.save_state(state.model_copy(update={"check": held}))
    _printed(every)
    print(f"wrote     {workspace.shown(report)}")
    if dropped:
        were = "finding of the model was" if dropped == 1 else "findings of the model were"
        print(f"note      {dropped} {were} left out: the text quoted is not in the file named")
    if ledger is not None:
        print(f"tokens    {_spent(ledger)}")
    loaded, found, stale, owed = _assessed(workspace, args.id, specs)
    print(f"next      {next_action(loaded.change.state, found, stale, check=owed)}")
    return EXIT_FINDINGS if blocking else EXIT_OK


def _judged(
    workspace: Workspace, change: Any, specs: dict[str, Spec], texts: dict[str, str]
) -> tuple[list[Finding], int, Any, str | None]:
    """The model's pass of a check: its findings that point at something, each with its path in the change's
    folder; how many pointed at nothing; the ledger; and the failure, where the pass did not end well."""
    from ..orchestration.models import require_ready

    if why := require_ready(roles=("check",)):
        raise UsageError(why)
    from ..orchestration.gate import FAILURE
    from ..orchestration.graph import build_check_app
    from ..orchestration.plugins import UsageLedger
    from ..orchestration.stages import CHANGE_FILES, LIVING
    from ..orchestration.stages import CONSTITUTION as RULES
    from ..orchestration.stages.check import read_check

    seed = {
        RULES: constitution_text(workspace),
        LIVING: living_text(specs, sorted(change.deltas)),
        CHANGE_FILES: files_text(texts),
    }
    ledger = UsageLedger(workspace.config().max_tokens or None)
    with _recording(workspace, "check", change.state.id) as kept:
        run = _ran(build_check_app(ledger=ledger, recorder=kept.recorder), seed, "check")
        answer = read_check(run.state)
        failure = run.state.get(FAILURE) or run.failure or (answer if isinstance(answer, str) else None)
        kept.outcome = f"failed: {failure}" if failure else "written"
    if failure or isinstance(answer, str):
        return [], 0, ledger, str(failure)
    judged, dropped = to_findings(answer, texts)
    return judged, dropped, ledger, None


def _verify(args: argparse.Namespace) -> int:
    _load_env()
    workspace = _workspace(args)
    with lock_held(workspace):
        try:
            return _verified(args, workspace)
        except NotYetError as exc:
            print(f"{PROG}: {exc}", file=sys.stderr)
            return EXIT_FINDINGS
        except GitError as exc:
            raise UsageError(str(exc)) from exc


def _implementation(
    args: argparse.Namespace, workspace: Workspace, state: ChangeState, stale: list[str]
) -> tuple[str, str]:
    """The commit a change's work is compared with, and the diff from it to the working tree. `NotYetError` where
    the change is not ready to be verified or nothing was done; `UsageError` where there is nothing to compare."""
    cid, root = state.id, workspace.root
    if state.status == "archived":
        raise NotYetError(f"`{cid}` is archived already")
    if state.approval is None or state.status == "draft":
        raise NotYetError(f"`{cid}` is not approved: run `adk-spec approve {cid}` first")
    if stale:
        raise NotYetError(
            f"the approval of `{cid}` is void: {', '.join(stale)} changed since. Run `adk-spec approve {cid}` again"
        )
    if not is_repository(root):
        raise UsageError(f"{root} is in no git repository: verify reads what changed since the approval")
    named = args.base or state.approval.commit
    if not named:
        raise UsageError(
            f"no commit was recorded when `{cid}` was approved. Name the commit the work started from with --base"
        )
    base = resolves(root, named)
    if base is None:
        raise UsageError(f"`{named}` names no commit in this repository")
    text = diff(root, base)
    if not text.strip():
        raise NotYetError(f"nothing under {root} changed since {base[:12]}: there is nothing to verify")
    if len(text) > DIFF_MAX_CHARS:
        raise UsageError(
            f"the diff since {base[:12]} holds {len(text):,} characters, past the {DIFF_MAX_CHARS:,} a stage is "
            "given. It is never cut. Verify a smaller change, or name a later commit with --base"
        )
    return base, text


def _verified(args: argparse.Namespace, workspace: Workspace) -> int:
    """The work judged against the change's requirements, one verdict each. The report is written and the
    verification recorded; the change is `verified` where every requirement is shown met, or a person says so
    with a reason."""
    specs, _of_living = workspace.specs()
    loaded, _found, stale, _owed = _assessed(workspace, args.id, specs)
    change, state = loaded.change, loaded.change.state
    base, text = _implementation(args, workspace, state, stale)
    added = owed(change.deltas)
    removed = frozenset(gone.id for delta in change.deltas.values() for gone in delta.removed)
    verdicts: list[Verdict] = []
    ledger, model = None, None
    if added or removed:  # a change with no delta has no requirement to judge
        from ..orchestration.models import serving

        verdicts, ledger, failure = _verdicts(workspace, change, text, added, removed)
        if failure:
            print(f"{PROG}: the verification did not finish, and nothing was recorded: {failure}", file=sys.stderr)
            print(f"tokens    {_spent(ledger)}")
            return EXIT_ENGINE
        model = serving("verify")
    at = datetime.now(UTC).isoformat(timespec="seconds")
    met = all(one.verdict == "met" for one in verdicts)
    override = None if met else (args.override or None)
    verified = met or override is not None
    report = render_verify(args.id, at, base, verdicts, model=model, override=override)
    path = workspace.write_report(args.id, "verify.md", report)
    held = Verification(
        at=at,
        base=base,
        diff=sha256_of(text),
        verdicts={v.id: v.verdict for v in verdicts},
        override=override,
        model=model,
    )
    status = "verified" if verified else "approved"
    workspace.save_state(state.model_copy(update={"verification": held, "status": status}))
    for one in verdicts:
        print(f"{one.verdict:<8}  {one.id}  {one.reason}")
    print(f"wrote     {workspace.shown(path)}")
    if ledger is not None:
        print(f"tokens    {_spent(ledger)}")
    loaded, found, stale, unchecked = _assessed(workspace, args.id, specs)
    print(f"next      {next_action(loaded.change.state, found, stale, check=unchecked)}")
    return EXIT_OK if verified else EXIT_FINDINGS


def _verdicts(
    workspace: Workspace, change: Any, text: str, added: frozenset[str], removed: frozenset[str]
) -> tuple[list[Verdict], Any, str | None]:
    """The model's verdicts on a diff, each held to the lines the diff really holds; the ledger; and the failure,
    where the run did not end well."""
    from ..orchestration.models import require_ready

    if why := require_ready(roles=("verify",)):
        raise UsageError(why)
    from ..orchestration.gate import FAILURE
    from ..orchestration.graph import build_verify_app
    from ..orchestration.plugins import UsageLedger
    from ..orchestration.stages import DELTAS_TEXT
    from ..orchestration.stages.verify import DIFF, REQUIRED, TASKS_TEXT, read_verify

    sides = [
        ("added or modified, shown by lines the diff adds", added),
        ("removed, shown by lines the diff removes", removed),
    ]
    seed = {
        DELTAS_TEXT: "\n".join(render_delta(delta) for _capability, delta in sorted(change.deltas.items())),
        TASKS_TEXT: render_tasks(change.tasks) if change.tasks else "",
        REQUIRED: "\n".join(f"{what}: {', '.join(sorted(ids))}" for what, ids in sides if ids),
        DIFF: text,
    }
    ledger = UsageLedger(workspace.config().max_tokens or None)
    with _recording(workspace, "verify", change.state.id) as kept:
        app = build_verify_app(ledger=ledger, required=added | removed, recorder=kept.recorder)
        run = _ran(app, seed, "verify")
        answer = read_verify(run.state)
        failure = run.state.get(FAILURE) or run.failure or (answer if isinstance(answer, str) else None)
        kept.outcome = f"failed: {failure}" if failure else "written"
    if failure or isinstance(answer, str):
        return [], ledger, str(failure)
    return grounded(answer, text, added=added, removed=removed), ledger, None


def _proposed(args: argparse.Namespace, workspace: Workspace) -> int:
    from ..orchestration.gate import FAILURE
    from ..orchestration.graph import UNWORDED, Known
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
        if why := state.get(UNWORDED):
            print(f"note      the brief's open points were not put to you ({why}). They stay in the brief")
        try:
            kept.change = _written(args, workspace, known, state, tier)
        except WorkspaceError as exc:  # the calls are paid for by now: say so beside the refusal
            kept.outcome = f"failed: {exc}"
            print(f"{PROG}: no change was written: {exc}", file=sys.stderr)
            print(f"tokens    {_spent(ledger)}")
            return EXIT_USAGE
        kept.outcome = "written"
    print(f"tokens    {_spent(ledger)}")
    loaded, found, stale, owed = _assessed(workspace, kept.change, specs)
    print(f"next      {next_action(loaded.change.state, found, stale, check=owed)}")
    return EXIT_OK


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
        entry, seed = next_run(seed, state, _answered(state[ASKING]))


def _written(args: argparse.Namespace, workspace: Workspace, known: Any, state: dict[str, Any], tier: Tier) -> str:
    """The change a run drafted, written whole: its id."""
    from ..orchestration.graph import drafted

    made = drafted(state, known)
    change_id = args.id or slug_of(made.brief.title, workspace.names_held())
    held = ChangeState(
        id=change_id, tier=tier, bases=capture_bases(made.deltas, known.living), needs_design=made.needs_design
    )
    files = {BRIEF_FILE: render_brief(made.brief)}
    files.update(
        {f"{SPECS}/{capability}/{SPEC_FILE}": render_delta(delta) for capability, delta in made.deltas.items()}
    )
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
