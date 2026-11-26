"""`adk-spec-mcp`: six of adk-spec's commands as the tools of an MCP server, for a coding assistant.

The owner's choices, 22 November 2026: a thin server, each tool running the command as the terminal runs it, asking
no question, and returning what it printed; every command but `approve` and `archive`, which record a person's
decision and stay a command the person runs; and the stages on adk-spec's own provider, as from the terminal. After
an outside audit, no tool names another repository: an assistant misled by text it read could have pointed adk-spec
at any repository of the person's and sent its code to a model. A change spanning repositories starts in a terminal,
and the tools keep the repositories it names. That narrows what a tool takes, not what an assistant can do: one that
edits `change.json`, or runs a terminal, is held by the editor's own approval of each step.

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
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated

import anyio
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from ..domain.model import Tier
from ..workspace.process import TOOL_CALL, Started, TimedOut, started, stop, waited

#: A tool's parameter that names a change.
_Change = Annotated[str, Field(description="The change")]
#: How long a tool waits for its command: a `propose` that reads the code takes minutes. A client may give up sooner.
TOOL_TIMEOUT_S = 3600.0
#: The commands running now. Each runs in a session of its own, which hears no signal sent to the server: where the
#: server is stopped, it stops them.
RUNNING: set[Started] = set()
#: What each tool does, for the editor to weigh: `status` and `validate` only read; `check` calls a model and writes
#: its report alone; the drafting tools call a model and write a change's files.
READS = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
REPORTS = ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=True)
WRITES = ToolAnnotations(read_only_hint=False, open_world_hint=True)
INSTRUCTIONS = """\
adk-spec drafts and checks spec-driven changes in the repository this server was started in, on adk-spec's own
models. propose drafts a change from a request, or, given the id of an open change, revises it; it asks no question:
points the brief leaves open come back in its output, so ask the person, then revise with propose and the change's
id. plan drafts a change's tasks again; check checks its files; verify judges the work against each requirement;
status lists the open changes and what comes next; validate checks the files' structure. propose and plan call a
model several times and take minutes, propose the most: call them once per request, never to poll. A strict change's
plan waits for the person to read its brief and specs: call plan for it once they say so. A change that
spans other repositories is started by the person in a terminal, with `adk-spec propose --with`; the tools then keep
them.

A change lives in `.spec/changes/<id>/`. Approving and archiving are the person's decisions: when a change is ready,
tell them to run `adk-spec approve <id>` in a terminal, and once it is verified `adk-spec archive <id>`. Never
approve, archive or set a finding aside for them. Once it is approved, implement it: read brief.md, the specs,
context.md and design.md in its folder, then work through tasks.md in order, test first, and tick each task's box,
`- [x]`, when it is done. Ticking a box keeps the approval; any other edit of the change's files voids the approval.
Then call status and do the step it names: verify, where the change owes a verification. Put
.spec/changes/<id>/reports/summary.md, which verify writes, in the pull request."""


#: What each way a command ends says to an assistant. Found by the fourth audit: exit 1, findings or a refusal, is
#: the command's answer, and was read as a failure and asked again.
_ENDINGS = {
    1: ", which is an answer: act on what it says before calling it again",
    2: ": refused, by a setting, by git, or for no model set up: put that right before calling again",
    3: ": the model or its provider failed, or a file could not be read or written",
}


def command(root: Path, *args: str) -> list[str]:
    """The command line that runs adk-spec on the workspace at `root`: `-P` keeps the folder it starts in, the
    person's repository, off the import path."""
    return [sys.executable, "-P", "-m", "adk_spec", "--root", str(root), *args]


def child_environment(argv: Sequence[str]) -> dict[str, str]:
    """The environment a command runs in: this server's, unbuffered, marked as a tool's call (`TOOL_CALL`: `verify` then
    runs only a committed test command), and for `validate` without a CI run's variables. Found by the code review:
    inside Copilot's cloud agent, which runs on GitHub Actions, `validate` annotated its tool result and wrote the
    job's summary at each call; another command, `verify`'s run of the tests, keeps them."""
    ci = ("GITHUB_ACTIONS", "GITHUB_STEP_SUMMARY") if argv and argv[0] == "validate" else ()
    held = {name: value for name, value in os.environ.items() if name not in ci}
    return {**held, "PYTHONUNBUFFERED": "1", TOOL_CALL: "1"}


async def ran(root: Path, argv: list[str]) -> str:
    """What the command printed, standard out and standard error together, in the order written. A command that
    fails, or does not finish, raises `ToolError`, which the assistant reads as a failed call with all it said. A call
    the assistant cancels stops the command's whole tree: it would otherwise run on, and spend, for an hour."""
    try:  # unbuffered: what it printed is kept to a stop at the time limit, and in order with what it warned
        process = started(command(root, *argv), env=child_environment(argv), cwd=root, merged=True)
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
        with anyio.CancelScope(shield=True):  # asked to stop, a command is given time, which blocks no other call
            await anyio.to_thread.run_sync(stop, process)
        raise
    finally:
        RUNNING.discard(process)
    if done.returncode != 0:
        raise ToolError(
            _said(done.stdout, f"adk-spec ended with exit {done.returncode}{_ENDINGS.get(done.returncode, '')}")
        )
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
    stop(*RUNNING)
    os._exit(128 + signum)  # at once, as the signal's own action: a thread reading the protocol would hold an exit


def _flag(on: bool, *words: str) -> list[str]:
    return list(words) if on else []


def build_server(root: Path) -> MCPServer:
    """The server for the workspace at `root`, with its six tools."""
    server = MCPServer(name="adk-spec", instructions=INSTRUCTIONS)

    @server.tool(
        description="Draft a change from a request, or revise the open change `id` names. Asks nothing.",
        annotations=WRITES,
    )
    async def propose(
        request: Annotated[str, Field(description="What is wanted, in a sentence or a paragraph")],
        id: Annotated[
            str | None, Field(description="An open change to revise by the request, or a new one's name")
        ] = None,
        tier: Annotated[
            Tier | None, Field(description="How much ceremony; left out, a model sizes the request")
        ] = None,
        no_explore: Annotated[
            bool, Field(description="Read none of the repository's code: cheaper, less grounded")
        ] = False,
    ) -> str:
        named = [*_flag(bool(id), f"--id={id}"), *_flag(bool(tier), f"--tier={tier}")]
        return await ran(root, ["propose", "--no-input", *named, *_flag(no_explore, "--no-explore"), "--", request])

    @server.tool(description="Draft a change's tasks again, and its design where one is owed.", annotations=WRITES)
    async def plan(
        id: _Change,
        replace: Annotated[
            bool, Field(description="Draft anew although a task is ticked, or a design was edited")
        ] = False,
        no_explore: Annotated[bool, Field(description="Read none of the repository's code for the plan")] = False,
    ) -> str:
        return await ran(root, ["plan", *_flag(replace, "--replace"), *_flag(no_explore, "--no-explore"), "--", id])

    @server.tool(
        description="Check a change's files against each other and against the repository's rules.",
        annotations=REPORTS,
    )
    async def check(
        id: _Change,
        no_model: Annotated[bool, Field(description="Run the checks code makes, and call no model")] = False,
    ) -> str:
        return await ran(root, ["check", *_flag(no_model, "--no-model"), "--", id])

    @server.tool(
        description="Run the project's tests and judge the work against each requirement of a change.",
        annotations=WRITES,
    )
    async def verify(id: _Change) -> str:
        # From the approval's base, always: found by the audit of 25 November, the tool's `bases` let the work being
        # judged choose where its diff starts. A person passes `--base` in a terminal.
        return await ran(root, ["verify", "--", id])

    @server.tool(description="List each open change and what comes next with it.", annotations=READS)
    async def status(
        include_archived: Annotated[bool, Field(description="List archived changes too")] = False,
    ) -> str:
        return await ran(root, ["status", *_flag(include_archived, "--all")])

    @server.tool(
        description="Check the structure of the living specs and of the open changes, or of one.", annotations=READS
    )
    async def validate(
        id: Annotated[str | None, Field(description="One change to check, in place of every open one")] = None,
        strict: Annotated[bool, Field(description="Fail on a warning too")] = False,
    ) -> str:
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
        stop(*RUNNING)
