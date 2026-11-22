"""`adk-spec-mcp`: six of adk-spec's commands as the tools of an MCP server, for a coding assistant.

The owner's choices, 22 November 2026: a thin server, each tool running the command as the terminal runs it, asking
no question, and returning what it printed; every command but `approve` and `archive`, which record a person's
decision and stay a command the person runs; and the stages on adk-spec's own provider, as from the terminal.

Each tool runs `python -P -m adk_spec` in a process of its own, through `workspace/process.py`, so the workspace's
lock, its recordings, its token ceiling and its next line are the terminal's, nothing a command prints reaches the
protocol's own stream, and no module in the repository stands in for one the command imports. A call the assistant
cancels stops its command, and what it started; so does stopping the server. A command that fails, or does not
finish, is a failed call, with all it printed. Arguments reach the command as the terminal takes them: options as
`--name=value`, and the request or the change after `--`, so a request that opens with a dash is a request.
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
from pathlib import Path

import anyio
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from ..domain.model import Tier
from ..workspace.process import Started, TimedOut, started, stop, waited

#: How long a tool waits for its command: a `propose` that reads the code takes minutes. A client may give up sooner.
TOOL_TIMEOUT_S = 3600.0
#: The commands running now. Each runs in a session of its own, which hears no signal sent to the server: where the
#: server is stopped, it stops them.
RUNNING: set[Started] = set()
INSTRUCTIONS = """\
adk-spec drafts and checks spec-driven changes in the repository this server was started in, on adk-spec's own
models. propose drafts a change from a request, or, given the id of an open change, revises it; it asks no question:
points the brief leaves open come back in its output, so ask the person, then revise with propose and the change's
id. plan drafts a change's tasks again; check checks its files; verify judges the work against each requirement;
status lists the open changes and what comes next; validate checks the files' structure.

Approving and archiving are the person's decisions: when a change is ready, tell them to run `adk-spec approve <id>`
in a terminal, and once it is verified `adk-spec archive <id>`. Never approve, archive or set a finding aside for
them."""


def command(root: Path, *args: str) -> list[str]:
    """The command line that runs adk-spec on the workspace at `root`: `-P` keeps the folder it starts in, the
    person's repository, off the import path."""
    return [sys.executable, "-P", "-m", "adk_spec", "--root", str(root), *args]


async def ran(root: Path, argv: list[str]) -> str:
    """What the command printed, standard out and standard error together, in the order written. A command that
    fails, or does not finish, raises `ToolError`, which the assistant reads as a failed call with all it said. A call
    the assistant cancels stops the command's whole tree: it would otherwise run on, and spend, for an hour."""
    try:  # unbuffered: what it printed is kept to a stop at the time limit, and in order with what it warned
        process = started(command(root, *argv), env={**os.environ, "PYTHONUNBUFFERED": "1"}, cwd=root, merged=True)
    except OSError as exc:  # on Windows, a request past the command line's 32,767 characters, say
        raise ToolError(f"adk-spec could not be started: {exc}") from exc
    RUNNING.add(process)
    try:
        done = await anyio.to_thread.run_sync(lambda: waited(process, TOOL_TIMEOUT_S), abandon_on_cancel=True)
    except TimedOut as exc:
        raise ToolError(
            _said(exc.output, f"adk-spec did not finish within {TOOL_TIMEOUT_S:g} s, and was stopped")
        ) from None
    except BaseException:  # the call cancelled: nothing waits for the answer any longer
        stop(process)
        raise
    finally:
        RUNNING.discard(process)
    if done.returncode != 0:
        raise ToolError(_said(done.stdout, f"adk-spec ended with exit {done.returncode}"))
    return _said(done.stdout, "") or "(adk-spec finished, and printed nothing)"


def _said(output: bytes | None, note: str) -> str:
    said = (output or b"").decode("utf-8", errors="replace").strip()
    return f"{said}\n({note})".strip() if note else said


def stop_on_signals() -> None:
    """Stopping the server, as an editor does reloading its window, stops the commands it runs first. Windows ends a
    process with no signal it could hear."""
    for name in ("SIGTERM", "SIGHUP"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), _stopped_by)


def _stopped_by(signum: int, _frame: object) -> None:
    for process in list(RUNNING):
        stop(process)
    os._exit(128 + signum)  # at once, as the signal's own action: a thread reading the protocol would hold an exit


def _flag(on: bool, *words: str) -> list[str]:
    return list(words) if on else []


def build_server(root: Path) -> MCPServer:
    """The server for the workspace at `root`, with its six tools."""
    server = MCPServer(name="adk-spec", instructions=INSTRUCTIONS)

    @server.tool(description="Draft a change from a request, or revise the open change `id` names. Asks nothing.")
    async def propose(
        request: str,
        id: str | None = None,
        tier: Tier | None = None,
        with_repositories: list[str] | None = None,
        no_explore: bool = False,
    ) -> str:
        named = [*_flag(bool(id), f"--id={id}"), *_flag(bool(tier), f"--tier={tier}")]
        widened = [f"--with={path}" for path in with_repositories or ()]
        return await ran(
            root, ["propose", "--no-input", *named, *widened, *_flag(no_explore, "--no-explore"), "--", request]
        )

    @server.tool(description="Draft a change's tasks again, and its design where one is owed.")
    async def plan(
        id: str, replace: bool = False, no_explore: bool = False, with_repositories: list[str] | None = None
    ) -> str:
        widened = [f"--with={path}" for path in with_repositories or ()]
        return await ran(
            root, ["plan", *_flag(replace, "--replace"), *_flag(no_explore, "--no-explore"), *widened, "--", id]
        )

    @server.tool(description="Check a change's files against each other and against the repository's rules.")
    async def check(id: str, no_model: bool = False) -> str:
        return await ran(root, ["check", *_flag(no_model, "--no-model"), "--", id])

    @server.tool(description="Run the project's tests and judge the work against each requirement of a change.")
    async def verify(id: str, bases: list[str] | None = None) -> str:
        return await ran(root, ["verify", *(f"--base={base}" for base in bases or ()), "--", id])

    @server.tool(description="List each open change and what comes next with it.")
    async def status(include_archived: bool = False) -> str:
        return await ran(root, ["status", *_flag(include_archived, "--all")])

    @server.tool(description="Check the structure of the living specs and of the open changes, or of one.")
    async def validate(id: str | None = None, strict: bool = False) -> str:
        return await ran(root, ["validate", *_flag(strict, "--strict"), *_flag(bool(id), "--", id or "")])

    return server


def main(argv: list[str] | None = None) -> None:
    """The process boundary of the installed `adk-spec-mcp`: the server, over stdio, for the workspace it is started
    in, or `--root`."""
    parser = argparse.ArgumentParser(prog="adk-spec-mcp", description="adk-spec's commands as MCP tools, over stdio.")
    parser.add_argument("--root", default=".", help="a folder in the repository to work in (default: this one)")
    args = parser.parse_args(argv)
    stop_on_signals()
    try:
        build_server(Path(args.root).resolve()).run("stdio")
    finally:  # the editor closed the protocol's stream: what still runs is stopped
        for process in list(RUNNING):
            stop(process)
