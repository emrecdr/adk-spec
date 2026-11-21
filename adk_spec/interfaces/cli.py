"""The `adk-spec` command. `main` is a function of its arguments and returns the exit code; `run` is the process
boundary, which sets the console's encoding once and turns Ctrl-C into a sentence.

The engine is never imported at the top: a handler that calls a model imports it inside itself, so `--version`, a
usage error and every command that calls no model start without it.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any, NoReturn, get_args

from ..domain.brief_md import render_brief
from ..domain.convert import slug_of
from ..domain.delta_md import render_delta
from ..domain.ids import slug_problem
from ..domain.lifecycle import (
    approval_files,
    approval_stale,
    approve,
    approve_blockers,
    archive_blockers,
    capture_bases,
    next_action,
)
from ..domain.merge import MergeError, apply_delta
from ..domain.model import ChangeState, Finding, Spec, Tier
from ..domain.validate import failed, finding, validate_spec
from ..workspace.config import ConfigError
from ..workspace.context import CONSTITUTION_MAX_CHARS, capability_index, constitution_text
from ..workspace.files import NotTextError
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
from ..workspace.lock import held as lock_held
from ..workspace.paths import PathError

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


def _assessed(
    workspace: Workspace, change_id: str, living: dict[str, Spec]
) -> tuple[LoadedChange, list[Finding], list[str]]:
    """A change as every command reads it: loaded, its findings with their paths from the root, and what its
    approval no longer covers."""
    loaded = workspace.load_change(change_id)
    prefix = f"{ROOT_NAME}/{CHANGES}/{change_id}/"
    unreadable = set(workspace.capabilities()) - set(living)  # a spec that is there and does not read
    of_change = findings_of(loaded, living, unreadable)
    found = [held.model_copy(update={"path": prefix + (held.path or "")}) for held in of_change]
    stale = approval_stale(loaded.change.state, approval_files(workspace.approval_texts(change_id)))
    return loaded, found, stale


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
        loaded, of_change, _stale = _assessed(workspace, change_id, living)
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
        loaded, found, stale = _assessed(workspace, change_id, living)
        state = loaded.change.state
        if state.status == "archived" and not args.all:
            continue
        step = next_action(state, found, stale)
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
    loaded, found, _stale = _assessed(workspace, args.id, living)
    if blockers := approve_blockers(loaded.change.state, found, strict=args.strict):
        _printed(blockers)
        print(f"{PROG}: `{args.id}` is not approved: {len(blockers)} findings block it", file=sys.stderr)
        return EXIT_FINDINGS
    files = approval_files(workspace.approval_texts(args.id))
    try:
        by = args.by or getpass.getuser()
    except OSError as exc:  # an account with no name, as in a container run under a bare user id
        raise UsageError("this account has no name: name the approver with --by") from exc
    at = datetime.now(UTC).isoformat(timespec="seconds")
    workspace.save_state(approve(loaded.change.state, files=files, by=by, at=at))
    print(f"approved `{args.id}` by {by}: {len(files)} files recorded")
    return EXIT_OK


def _archive(args: argparse.Namespace) -> int:
    """Every capability's merge is computed before any file is written, and the merged specs and the change's state
    are then written as one set: all of them, or none as far as the file system allows."""
    workspace = _workspace(args)
    living, of_specs = workspace.specs()
    loaded, _found, stale = _assessed(workspace, args.id, living)
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


def _answered(payload: dict[str, Any]) -> dict[str, Any]:
    """A round of questions put to the person on the terminal, one at a time. A line is the answer; `=` takes the
    suggestion; an empty line leaves the point open; the end of the input answers every question still to come with
    nothing. The answers go back as data, never as text a run could take for a new request."""
    questions = payload.get("questions") or []
    print(f"The brief leaves {len(questions)} open. A line answers. `=` takes the suggestion.")
    print("An empty line leaves the point open.")
    answers: list[str] = []
    ended = False
    for number, question in enumerate(questions, 1):
        print(f"{number}. {question.get('question', '')}")
        print(f"   suggested: {question.get('recommended', '')}", flush=True)
        line = "" if ended else sys.stdin.readline()
        ended = ended or line == ""  # no line at all: the input is over
        typed = line.strip()
        answers.append(str(question.get("recommended", "")) if typed == "=" else typed)
    return {"answers": answers}


def _ran(
    app: Any, seed: dict[str, Any], prompt: str, answer: Callable[[dict[str, Any]], dict[str, Any]] | None = None
) -> Any:
    """One run of `app`, with the engine's own log quieted for its length: ADK logs a failed node with its whole
    traceback, and the command says the failure in one line."""
    import asyncio
    import logging

    from ..orchestration.run import run_seeded

    engine_log = logging.getLogger("google_adk")
    level = engine_log.level
    engine_log.setLevel(logging.CRITICAL)
    try:
        return asyncio.run(run_seeded(app, state=seed, prompt=prompt, answer=answer))
    finally:
        engine_log.setLevel(level)


def _spent(app: Any) -> str:
    """What a run's stages spent, from the app's ledger: each stage, then the total."""
    from ..orchestration.plugins import UsageLedger

    ledger = next(plugin for plugin in app.plugins if isinstance(plugin, UsageLedger))
    stages = ", ".join(f"{name} {row.total:,}" for name, row in ledger.spent.items())
    return f"{stages}: {ledger.total.total:,} total" if stages else "nothing"


def _propose(args: argparse.Namespace) -> int:
    _load_env()
    workspace = _workspace(args)
    if args.id:  # refused before anything is spent
        if why := slug_problem(args.id):
            raise UsageError(f"a change cannot be named so: {why}")
        if args.id in workspace.changes():
            raise UsageError(f"the change `{args.id}` exists already")
    from ..orchestration.models import require_ready

    if why := require_ready(roles=("triage", "brief", "questions", "deltas")):
        raise UsageError(why)
    with lock_held(workspace):
        return _proposed(args, workspace)


def _proposed(args: argparse.Namespace, workspace: Workspace) -> int:
    from ..orchestration.gate import FAILURE
    from ..orchestration.graph import TIER, Known, build_propose_app, drafted
    from ..orchestration.stages import CAPABILITIES, REQUEST
    from ..orchestration.stages.brief import CONSTITUTION as RULES
    from ..orchestration.stages.triage import read_triage

    specs, of_specs = workspace.specs()
    if of_specs:  # a spec that does not read would pass for a capability not yet there
        _printed(of_specs)
        print(f"{PROG}: nothing was drafted: a living spec does not read. Fix it first", file=sys.stderr)
        return EXIT_FINDINGS
    taken = {capability: frozenset(workspace.taken_ids(capability)) for capability in specs}
    known = Known(living=specs, taken=taken, ceiling=workspace.config().max_tokens or None)
    seed = {REQUEST: args.request, CAPABILITIES: capability_index(workspace), RULES: constitution_text(workspace)}
    app = build_propose_app(known, tier=args.tier, ask=not args.no_input)
    run = _ran(app, seed, "propose", None if args.no_input else _answered)
    if failure := run.state.get(FAILURE) or run.failure:
        print(f"{PROG}: no change was written: {failure}", file=sys.stderr)
        print(f"tokens    {_spent(app)}")
        return EXIT_ENGINE
    tier = run.state.get(TIER)
    if tier == "none":
        sized = read_triage(run.state)
        print(f"no spec is owed: {sized if isinstance(sized, str) else sized.reason}")
        print(f"tokens    {_spent(app)}")
        return EXIT_OK
    made = drafted(run.state, known)
    change_id = args.id or slug_of(made.brief.title, workspace.changes())
    state = ChangeState(
        id=change_id, tier=tier, bases=capture_bases(made.deltas, specs), needs_design=made.draft.design_needed
    )
    files = {"brief.md": render_brief(made.brief)}
    files.update(
        {f"{SPECS}/{capability}/{SPEC_FILE}": render_delta(delta) for capability, delta in made.deltas.items()}
    )
    folder = workspace.write_change(state, files)
    print(f"wrote     {workspace.shown(folder)}, a {tier} draft")
    for path in files:
        print(f"          {workspace.shown(folder)}/{path}")
    print(f"tokens    {_spent(app)}")
    loaded, found, stale = _assessed(workspace, change_id, specs)
    print(f"next      {next_action(loaded.change.state, found, stale)}")
    return EXIT_OK


def _login(args: argparse.Namespace) -> int:
    """The Copilot login, which reads the checkout's `.env` for an enterprise tenant's endpoints as a run does."""
    _load_env()
    from .login import main as login

    return login(["--force"] if args.force else [])


def _models(args: argparse.Namespace) -> int:
    _load_env()
    import httpx

    from ..orchestration.catalog import CatalogError, list_models, shown
    from ..orchestration.models import require_ready

    if why := require_ready():
        raise UsageError(why)
    try:
        models = list_models()
    except (CatalogError, httpx.HTTPError) as exc:
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
    from ..orchestration.stages.triage import CAPABILITIES, KEY, REQUEST, read_triage

    try:  # the capabilities of the workspace this runs in, where it runs in one
        known = capability_index(_workspace(args))
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
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")  # a Windows console is not UTF-8 by default
    try:
        return main(sys.argv[1:])
    except KeyboardInterrupt:
        print(f"{PROG}: interrupted", file=sys.stderr)
        return EXIT_INTERRUPTED
