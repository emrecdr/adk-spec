"""`adk-spec-mcp`: six of adk-spec's commands as the tools of an MCP server, for a coding assistant.

The owner's choices, 22 November 2026: a thin server, each tool running the command as the terminal runs it, asking
no question, and returning what it printed; every command but `approve` and `archive`, which record a person's
decision and stay a command the person runs; and the stages on adk-spec's own provider, as from the terminal.

Each tool runs `python -P -m adk_spec` in a process of its own, through `workspace/process.py`, so the workspace's
lock, its recordings, its token ceiling and its next line are the terminal's, nothing a command prints reaches the
protocol's own stream, and no module in the repository stands in for one the command imports. A call the assistant
cancels stops its command, and what it started. Arguments reach the command as the terminal takes them: options as
`--name=value`, and the request or the change after `--`, so a request that opens with a dash is a request.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import anyio
from mcp.server.mcpserver import MCPServer

from ..domain.model import Tier
from ..workspace.process import TimedOut, started, stop, waited

#: How long a tool waits for its command: a `propose` that reads the code takes minutes. A client may give up sooner.
TOOL_TIMEOUT_S = 3600.0
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
    """What the command printed, standard out and standard error together, and how it ended where not well. A call
    the assistant cancels stops the command's whole tree: it would otherwise run on, and spend, for an hour."""
    process = started(command(root, *argv), env=os.environ, cwd=root, merged=True)
    try:
        done = await anyio.to_thread.run_sync(lambda: waited(process, TOOL_TIMEOUT_S), abandon_on_cancel=True)
    except TimedOut as exc:
        text, note = exc.output or b"", f"adk-spec did not finish within {TOOL_TIMEOUT_S:g} s, and was stopped"
    except BaseException:  # the call cancelled: nothing waits for the answer any longer
        stop(process)
        raise
    else:
        text, note = done.stdout, "" if done.returncode == 0 else f"adk-spec ended with exit {done.returncode}"
    said = text.decode("utf-8", errors="replace").strip()
    return f"{said}\n({note})".strip() if note else said


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
    build_server(Path(args.root).resolve()).run("stdio")
