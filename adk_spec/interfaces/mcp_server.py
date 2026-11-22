"""`adk-spec-mcp`: six of adk-spec's commands as the tools of an MCP server, for a coding assistant.

The owner's choices, 22 November 2026: a thin server, each tool running the command as the terminal runs it, asking
no question, and returning what it printed; every command but `approve` and `archive`, which record a person's
decision and stay a command the person runs; and the stages on adk-spec's own provider, as from the terminal.

Each tool runs `python -m adk_spec` in a process of its own, through `workspace/process.py`, so the workspace's lock,
its recordings, its token ceiling and its next line are the terminal's, and nothing a command prints reaches the
protocol's own stream. Arguments reach the command as the terminal takes them: options as `--name=value`, and the
request or the change after `--`, so a request that opens with a dash is a request.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Literal

from mcp.server.mcpserver import MCPServer

from ..workspace.process import TimedOut, run

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

Tier = Literal["lean", "standard", "strict"]


def command(root: Path, *args: str) -> list[str]:
    """The command line that runs adk-spec on the workspace at `root`."""
    return [sys.executable, "-m", "adk_spec", "--root", str(root), *args]


def ran(root: Path, argv: list[str]) -> str:
    """What the command printed, standard out and standard error together, and how it ended where not well."""
    try:
        done = run(command(root, *argv), env=os.environ, timeout=TOOL_TIMEOUT_S, cwd=root, merged=True)
    except TimedOut as exc:
        text = (exc.output or b"").decode("utf-8", errors="replace").strip()
        return f"{text}\n(adk-spec did not finish within {TOOL_TIMEOUT_S:g} s, and was stopped)".strip()
    text = done.stdout.decode("utf-8", errors="replace").strip()
    return text if done.returncode == 0 else f"{text}\n(adk-spec ended with exit {done.returncode})".strip()


def propose_argv(
    request: str,
    id: str | None = None,
    tier: Tier | None = None,
    with_repositories: list[str] | None = None,
    no_explore: bool = False,
) -> list[str]:
    argv = ["propose", "--no-input", *([f"--id={id}"] if id else []), *([f"--tier={tier}"] if tier else [])]
    argv += [f"--with={path}" for path in with_repositories or ()]
    return [*argv, *(["--no-explore"] if no_explore else []), "--", request]


def plan_argv(
    id: str, replace: bool = False, no_explore: bool = False, with_repositories: list[str] | None = None
) -> list[str]:
    argv = ["plan", *(["--replace"] if replace else []), *(["--no-explore"] if no_explore else [])]
    return [*argv, *(f"--with={path}" for path in with_repositories or ()), "--", id]


def check_argv(id: str, no_model: bool = False) -> list[str]:
    return ["check", *(["--no-model"] if no_model else []), "--", id]


def verify_argv(id: str, bases: list[str] | None = None) -> list[str]:
    return ["verify", *(f"--base={base}" for base in bases or ()), "--", id]


def status_argv(include_archived: bool = False) -> list[str]:
    return ["status", *(["--all"] if include_archived else [])]


def validate_argv(id: str | None = None, strict: bool = False) -> list[str]:
    return ["validate", *(["--strict"] if strict else []), *(["--", id] if id else [])]


def build_server(root: Path) -> MCPServer:
    """The server for the workspace at `root`, with its six tools."""
    server = MCPServer(name="adk-spec", instructions=INSTRUCTIONS)

    @server.tool(description="Draft a change from a request, or revise the open change `id` names. Asks nothing.")
    def propose(
        request: str,
        id: str | None = None,
        tier: Tier | None = None,
        with_repositories: list[str] | None = None,
        no_explore: bool = False,
    ) -> str:
        return ran(root, propose_argv(request, id, tier, with_repositories, no_explore))

    @server.tool(description="Draft a change's tasks again, and its design where one is owed.")
    def plan(
        id: str, replace: bool = False, no_explore: bool = False, with_repositories: list[str] | None = None
    ) -> str:
        return ran(root, plan_argv(id, replace, no_explore, with_repositories))

    @server.tool(description="Check a change's files against each other and against the repository's rules.")
    def check(id: str, no_model: bool = False) -> str:
        return ran(root, check_argv(id, no_model))

    @server.tool(description="Run the project's tests and judge the work against each requirement of a change.")
    def verify(id: str, bases: list[str] | None = None) -> str:
        return ran(root, verify_argv(id, bases))

    @server.tool(description="List each open change and what comes next with it.")
    def status(include_archived: bool = False) -> str:
        return ran(root, status_argv(include_archived))

    @server.tool(description="Check the structure of the living specs and of the open changes, or of one.")
    def validate(id: str | None = None, strict: bool = False) -> str:
        return ran(root, validate_argv(id, strict))

    return server


def main(argv: list[str] | None = None) -> None:
    """The process boundary of the installed `adk-spec-mcp`: the server, over stdio, for the workspace it is started
    in, or `--root`."""
    parser = argparse.ArgumentParser(prog="adk-spec-mcp", description="adk-spec's commands as MCP tools, over stdio.")
    parser.add_argument("--root", default=".", help="a folder in the repository to work in (default: this one)")
    args = parser.parse_args(argv)
    build_server(Path(args.root).resolve()).run("stdio")
