"""`adk-spec-mcp`: six of adk-spec's commands served to a coding assistant over MCP, each run as the terminal runs
it. Approving and archiving stay a person's command."""

from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import sys
import textwrap
from pathlib import Path

import anyio
import pytest
from conftest import seeded
from mcp.server.mcpserver.exceptions import ToolError

from adk_spec.interfaces import cli, mcp_server
from adk_spec.interfaces.mcp_server import INSTRUCTIONS, build_server
from adk_spec.workspace.lock import _alive

ROOT = Path(__file__).resolve().parents[1]


def _sleeper(marker: Path) -> str:
    """A program that writes its pid to `marker` and then waits a minute: a command that runs long."""
    return f"import os, time\nopen({str(marker)!r}, 'w').write(str(os.getpid()))\ntime.sleep(60)\n"


async def _its_pid(marker: Path) -> int:
    written = anyio.Path(marker)
    for _ in range(200):
        if await written.exists() and (text := await written.read_text()):
            return int(text)
        await asyncio.sleep(0.05)
    pytest.fail("the command never started")


async def _ended(pid: int) -> bool:
    """Whether process `pid` ends within five seconds, asked as the lock asks it: on Windows too, where `os.kill`
    would end the process it asks about."""
    for _ in range(100):
        if not _alive(pid):
            return True
        await asyncio.sleep(0.05)
    return False


def _run_python(monkeypatch, code: str) -> None:
    monkeypatch.setattr(mcp_server, "command", lambda _root, *_args: [sys.executable, "-c", code])


@pytest.mark.asyncio
async def test_the_server_offers_six_tools_and_leaves_approving_and_archiving_to_the_person(tmp_path) -> None:
    """The owner's choice: approving and archiving record a person's decision, and stay a command the person runs."""
    names = sorted(tool.name for tool in await build_server(tmp_path).list_tools())
    assert names == ["check", "plan", "propose", "status", "validate", "verify"]
    assert "adk-spec approve" in INSTRUCTIONS and "adk-spec archive" in INSTRUCTIONS


@pytest.mark.asyncio
async def test_each_tool_hands_the_command_what_the_terminal_would(tmp_path, monkeypatch) -> None:
    """Each tool's arguments become the command's own, each value one argument and the request after `--`, as the
    command's own parser reads them: a request that opens with a dash is a request."""
    asked: list[list[str]] = []

    async def heard(_root, argv: list[str]) -> str:
        asked.append(argv)
        return "done"

    monkeypatch.setattr(mcp_server, "ran", heard)
    server = build_server(tmp_path)
    request = '-starts with a dash, and "quotes"'
    calls = {
        "propose": {"request": request, "id": "pk", "tier": "strict"},
        "plan": {"id": "pk", "replace": True, "no_explore": True},
        "check": {"id": "pk", "no_model": True},
        "verify": {"id": "pk", "bases": ["api=abc"]},
        "status": {"include_archived": True},
        "validate": {"id": "pk", "strict": True},
    }
    for name, arguments in calls.items():
        await server.call_tool(name, arguments)
    read = {argv[0]: vars(cli._parser().parse_args(argv)) for argv in asked}
    assert read["propose"]["request"] == request and read["propose"]["no_input"]
    assert (read["propose"]["id"], read["propose"]["tier"]) == ("pk", "strict")
    assert (read["plan"]["replace"], read["plan"]["no_explore"]) == (True, True)
    assert read["check"]["no_model"] and read["verify"]["base"] == ["api=abc"] and read["verify"]["override"] is None
    assert read["status"]["all"] and read["validate"]["strict"] and read["validate"]["id"] == "pk"


@pytest.mark.asyncio
async def test_status_and_validate_run_through_the_server_as_in_the_terminal(tmp_path) -> None:
    """End to end, with no model: each tool runs the command in a process of its own and returns its lines."""
    seeded(tmp_path)
    server = build_server(tmp_path)
    status, validated = await server.call_tool("status", {}), await server.call_tool("validate", {"id": "passkeys"})
    listed, checked = (" ".join(part.text for part in result.content) for result in (status, validated))
    assert "passkeys" in listed and "ended with exit" not in listed
    assert "did not finish" not in checked and "ended with exit 2" not in checked, "the change after `--` was read"


@pytest.mark.asyncio
async def test_a_module_in_the_repository_never_stands_in_for_one_the_command_imports(tmp_path) -> None:
    """Found by review: `python -m` puts the folder it starts in first on the import path, and the server starts
    each command in the person's repository, where a `json.py` would be imported in place of Python's own."""
    seeded(tmp_path)
    (tmp_path / "json.py").write_text("raise SystemExit('the repository was imported')\n", encoding="utf-8")
    listed = await mcp_server.ran(tmp_path, ["status"])
    assert "the repository was imported" not in listed and "passkeys" in listed


@pytest.mark.asyncio
async def test_a_call_the_assistant_cancels_stops_the_command(tmp_path, monkeypatch) -> None:
    """Found by review: a cancelled call left its command running for up to an hour, spending tokens."""
    marker = tmp_path / "pid"
    _run_python(monkeypatch, _sleeper(marker))
    call = asyncio.create_task(mcp_server.ran(tmp_path, ["status"]))
    pid = await _its_pid(marker)
    call.cancel()
    with pytest.raises(asyncio.CancelledError):
        await call
    assert await _ended(pid), "the command still runs after its call was cancelled"
    assert not mcp_server.RUNNING


@pytest.mark.skipif(os.name == "nt", reason="Windows ends a process with no signal it could hear")
@pytest.mark.asyncio
async def test_a_server_the_editor_stops_stops_the_commands_it_runs(tmp_path) -> None:
    """Found by review: each command runs in a session of its own, which hears no signal sent to the server, and an
    editor reloading its window stopped the server and left its command running, spending and holding the lock."""
    marker = tmp_path / "pid"
    server = textwrap.dedent(f"""
        import asyncio, sys
        from pathlib import Path
        from adk_spec.interfaces import mcp_server
        mcp_server.command = lambda _root, *_args: [sys.executable, "-c", {_sleeper(marker)!r}]
        mcp_server.stop_on_signals()
        asyncio.run(mcp_server.ran(Path("."), ["propose"]))
    """)
    running = subprocess.Popen([sys.executable, "-c", server], cwd=ROOT)  # noqa: ASYNC220 - the server, at once
    try:
        pid = await _its_pid(marker)
        running.send_signal(signal.SIGTERM)
        assert running.wait(timeout=10) != 0
        assert await _ended(pid), "the command still runs after its server was stopped"
    finally:
        running.kill()


@pytest.mark.asyncio
async def test_a_command_that_fails_is_a_failed_call_and_says_how_it_ended(tmp_path, monkeypatch) -> None:
    """Found by review: a failed command came back as a call that succeeded, its end only a parenthesis an assistant
    could pass over. It is now a failed call, with all the command said."""
    _run_python(monkeypatch, "print('two findings block it')\nraise SystemExit(1)")
    with pytest.raises(ToolError) as failed:
        await mcp_server.ran(tmp_path, ["check", "--", "pk"])
    assert "two findings block it" in str(failed.value) and "ended with exit 1" in str(failed.value)


@pytest.mark.asyncio
async def test_a_command_stopped_at_its_time_keeps_what_it_had_printed(tmp_path, monkeypatch) -> None:
    """Found by review: a command's standard out, to a pipe, waited in its buffer, and a stop at the time limit lost
    it; standard error, written at once, came out ahead of it."""
    _run_python(monkeypatch, "print('drafted the brief')\nimport time\ntime.sleep(60)")
    monkeypatch.setattr(mcp_server, "TOOL_TIMEOUT_S", 2.0)
    with pytest.raises(ToolError) as failed:
        await mcp_server.ran(tmp_path, ["propose", "--", "x"])
    assert "drafted the brief" in str(failed.value) and "did not finish" in str(failed.value)


@pytest.mark.asyncio
async def test_a_command_that_printed_nothing_still_says_it_finished(tmp_path, monkeypatch) -> None:
    """Found by review: a quiet success returned nothing, and an assistant could only guess how it ended."""
    _run_python(monkeypatch, "pass")
    assert "finished" in await mcp_server.ran(tmp_path, ["validate"])


@pytest.mark.asyncio
async def test_a_command_that_cannot_be_started_says_why(tmp_path, monkeypatch) -> None:
    """Found by review: on Windows a request past the command line's 32,767 characters fails to start, and the SDK
    shows an assistant an unforeseen error only as its tool's name."""

    def too_long(*_args, **_kwargs):
        raise OSError(206, "The filename or extension is too long")

    monkeypatch.setattr(mcp_server, "started", too_long)
    with pytest.raises(ToolError, match=r"could not be started.*too long"):
        await mcp_server.ran(tmp_path, ["propose", "--", "x" * 40_000])


def test_importing_the_packages_main_runs_no_command(monkeypatch) -> None:
    """Found by review: a process that imports it, as multiprocessing's spawn does the main module, ran the command
    and exited."""
    import importlib

    monkeypatch.setattr(sys, "argv", ["adk-spec", "--help"])
    monkeypatch.delitem(sys.modules, "adk_spec.__main__", raising=False)
    importlib.import_module("adk_spec.__main__")


@pytest.mark.asyncio
async def test_no_tool_lets_the_assistant_name_another_repository(tmp_path) -> None:
    """The owner's choice, after an outside audit: an assistant misled by text it read could have pointed adk-spec at
    another repository of the person's and sent its code to a model. A change spanning repositories starts in a
    terminal; the tools keep the repositories a change already names."""
    tools = {tool.name: tool for tool in await build_server(tmp_path).list_tools()}
    for name in ("propose", "plan"):
        assert "with_repositories" not in tools[name].input_schema["properties"]
    assert "--with" in INSTRUCTIONS


@pytest.mark.asyncio
async def test_the_tools_say_which_only_read_and_which_call_a_model(tmp_path) -> None:
    """Found by an outside audit: with no annotations, an editor took every tool to change files and call out."""
    tools = {tool.name: tool.annotations for tool in await build_server(tmp_path).list_tools()}
    for name in ("status", "validate"):
        assert tools[name].read_only_hint and not tools[name].open_world_hint
    for name in ("propose", "plan", "check", "verify"):
        assert not tools[name].read_only_hint and tools[name].open_world_hint
    assert tools["check"].destructive_hint is False, "check writes its own report alone"
    assert tools["propose"].destructive_hint is not False, "propose may rewrite a change's files"


@pytest.mark.asyncio
async def test_every_parameter_says_what_it_is_and_the_assistant_is_told_how_to_implement(tmp_path) -> None:
    """Found by the third audit: no parameter had a description, and the instructions said nothing of implementing
    from the change's folder, of ticking tasks, or of what a `propose` costs."""
    tools = await build_server(tmp_path).list_tools()
    for tool in tools:
        for name, held in tool.input_schema["properties"].items():
            assert held.get("description"), f"{tool.name}.{name}"
    for said in ("tasks.md", "tick", "voids the approval", "minutes"):
        assert said in INSTRUCTIONS, said
