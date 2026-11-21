"""The `adk-spec` command. `main` is a function of its arguments and returns the exit code; `run` is the process
boundary, which sets the console's encoding once and turns Ctrl-C into a sentence.

The engine is never imported at the top: a handler that calls a model imports it inside itself, so `--version`, a
usage error and every command that calls no model start without it.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from importlib import metadata
from pathlib import Path
from typing import NoReturn, get_args

from ..domain.lifecycle import approval_files, approval_stale, next_action
from ..domain.model import Finding, Spec, Tier
from ..domain.validate import failed, validate_spec
from ..workspace.config import ConfigError
from ..workspace.files import NotTextError
from ..workspace.layout import (
    CHANGES,
    ROOT_NAME,
    SPEC_FILE,
    SPECS,
    LoadedChange,
    Workspace,
    WorkspaceError,
    findings_of,
)
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

    smoke = commands.add_parser("smoke", help="run the triage stage alone, to prove an arm answers in a schema")
    smoke.add_argument("--model", help="the model for this run alone, in place of the arm's")
    smoke.add_argument("--request", default=SMOKE_REQUEST, help="the change request to size")
    smoke.add_argument("--json", action="store_true", help="print the result as JSON")
    smoke.set_defaults(handler=_smoke)

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


# The commands that call no model.


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
    found = [held.model_copy(update={"path": prefix + (held.path or "")}) for held in findings_of(loaded, living)]
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


# The commands that call a model, or log in to one.


def _load_env() -> None:
    """The checkout's `.env` read into the environment, the shell winning over the file."""
    from dotenv import load_dotenv

    try:
        load_dotenv(CHECKOUT / ".env", override=False, encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise UsageError(
            f"{CHECKOUT / '.env'} is not UTF-8. Save it as UTF-8: Windows PowerShell 5.1's `>` writes UTF-16"
        ) from exc


def _login(args: argparse.Namespace) -> int:
    """The Copilot login, which reads the checkout's `.env` for an enterprise tenant's endpoints as a run does."""
    _load_env()
    from .login import main as login

    return login(["--force"] if args.force else [])


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


def _smoked(args: argparse.Namespace) -> int:
    import asyncio
    import logging

    from ..orchestration.models import require_ready, serving

    if why := require_ready(roles=("triage",)):
        raise UsageError(why)
    from ..orchestration.graph import build_smoke_app
    from ..orchestration.run import run_seeded
    from ..orchestration.stages.triage import CAPABILITIES, KEY, REQUEST, read_triage

    # ADK logs a failed node with its whole traceback; the failure is said below, in one line.
    logging.getLogger("google_adk").setLevel(logging.CRITICAL)
    run = asyncio.run(run_seeded(build_smoke_app(), state={REQUEST: args.request, CAPABILITIES: ""}, prompt=KEY))
    answer = read_triage(run.state)
    failure = None
    if isinstance(answer, str):
        failure = run.failure or next(iter(run.errors.values()), None) or answer
    spent = run.usage
    tokens = {"calls": spent.calls, "prompt": spent.prompt, "output": spent.output, "total": spent.total}
    if args.json:
        result = {
            "model": serving("triage"),
            "schema": "invalid" if failure else "valid",
            "triage": None if isinstance(answer, str) else answer.model_dump(),
            "failure": failure,
            "tokens": tokens,
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
