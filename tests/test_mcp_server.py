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
from adk_spec.interfaces.mcp_server import INSTRUCTIONS, build_server, child_environment
from adk_spec.workspace.lock import _alive
from adk_spec.workspace.skill import SKILL_TEXT

ROOT = Path(__file__).resolve().parents[1]
_posix_only = pytest.mark.skipif(os.name == "nt", reason="Windows ends a process with no signal it could hear")


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
        "verify": {"id": "pk"},
        "status": {"include_archived": True},
        "validate": {"id": "pk", "strict": True},
    }
    for name, arguments in calls.items():
        await server.call_tool(name, arguments)
    read = {argv[0]: vars(cli._parser().parse_args(argv)) for argv in asked}
    assert read["propose"]["request"] == request and read["propose"]["no_input"]
    assert (read["propose"]["id"], read["propose"]["tier"]) == ("pk", "strict")
    assert (read["plan"]["replace"], read["plan"]["no_explore"]) == (True, True)
    assert read["check"]["no_model"] and read["verify"]["base"] == [] and read["verify"]["override"] is None
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


@_posix_only
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
    # Found by the fourth audit: exit 1 is a command's answer, findings or a refusal, and was read as a failure.
    assert "an answer: act on what it says before calling it again" in str(failed.value)


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


def test_the_skill_init_writes_keeps_the_rules_the_server_gives() -> None:
    """Found by the cleanup review: the two texts that tell an assistant how to use adk-spec, one for the server's
    tools and one for a terminal, had drifted, and the skill left naming another repository to the assistant."""
    for said in ("adk-spec approve", "adk-spec archive", "--with", "tasks.md", "- [x]", "context.md", "voids"):
        assert said in INSTRUCTIONS and said in SKILL_TEXT, said
    # Found by the fourth audit: a `propose` measured at 321 s outlasts an assistant's shell, 120 s by default; a lean
    # change owes no verification; and a strict change's plan waits for the person to read its brief.
    for said in ("take minutes", "status", "strict"):
        assert said in INSTRUCTIONS and said in SKILL_TEXT, said
    assert "background" in SKILL_TEXT and "Then call verify" not in INSTRUCTIONS


def test_validate_the_server_runs_is_not_told_it_runs_in_github_actions(monkeypatch) -> None:
    """Found by the code review: inside Copilot's cloud agent, which runs on GitHub Actions, `validate` annotated its
    tool result and wrote the job's summary each time an assistant asked it."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", "/tmp/summary.md")
    held = child_environment(["validate"])
    assert "GITHUB_ACTIONS" not in held and "GITHUB_STEP_SUMMARY" not in held and held["PYTHONUNBUFFERED"] == "1"
    assert "GITHUB_ACTIONS" not in child_environment(("validate", "--strict")), "found by the closing code review"


def test_only_validate_is_kept_from_github_actions(monkeypatch) -> None:
    """Found by the code review: `verify`'s run of the project's tests lost the CI variables its suite may read."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    assert child_environment(["verify", "x"])["GITHUB_ACTIONS"] == "true"


def _testing(marker: Path) -> str:
    """A command that hears a stop as `adk-spec` does, then runs a test run that waits a minute, its pid in `marker`:
    a `verify` stopped while the project's tests run."""
    return textwrap.dedent(f"""
        import os, sys
        from adk_spec.interfaces.cli import interrupt_on_signals
        from adk_spec.workspace.process import run_kept
        interrupt_on_signals()
        run_kept([sys.executable, "-c", {_sleeper(marker)!r}], env=dict(os.environ), timeout=120, keep=1000)
    """)


@_posix_only
@pytest.mark.asyncio
async def test_a_cancelled_call_stops_the_tests_its_command_started(tmp_path, monkeypatch) -> None:
    """Found by the audit of 25 November: the tests run in a session of their own, and a cancel that stopped the
    command outright left them running, with no timeout kept."""
    marker = tmp_path / "pid"
    _run_python(monkeypatch, _testing(marker))
    call = asyncio.create_task(mcp_server.ran(tmp_path, ["verify", "--", "pk"]))
    pid = await _its_pid(marker)
    call.cancel()
    with pytest.raises(asyncio.CancelledError):
        await call
    assert await _ended(pid), "the tests still run after the call that started them was cancelled"


@_posix_only
@pytest.mark.parametrize("heard", ["SIGHUP", "SIGTERM"])
@pytest.mark.asyncio
async def test_a_command_hung_up_on_stops_its_tests(tmp_path, heard: str) -> None:
    """Found by the audit of 25 November: a terminal closed (SIGHUP), or a `kill` (SIGTERM), ended the command and
    left its tests running."""
    marker = tmp_path / "pid"
    running = subprocess.Popen([sys.executable, "-c", _testing(marker)], cwd=ROOT)  # noqa: ASYNC220 - at once
    try:
        pid = await _its_pid(marker)
        running.send_signal(getattr(signal, heard))
        assert running.wait(timeout=10) != 0
        assert await _ended(pid), "the tests still run after their command was stopped"
    finally:
        running.kill()


@pytest.mark.asyncio
async def test_the_verify_tool_diffs_from_the_approvals_base_and_says_it_runs_for_a_tool(tmp_path) -> None:
    """Found by the audit of 25 November: the tool's `bases` let the work being judged choose where its diff starts;
    and the command is told it runs for a tool, so that it runs only a committed test command."""
    tools = {tool.name: tool for tool in await build_server(tmp_path).list_tools()}
    assert "bases" not in tools["verify"].input_schema["properties"]
    assert child_environment(["verify", "--", "pk"])["SPEC_TOOL_CALL"] == "1"


@_posix_only
def test_a_signal_ignored_before_the_command_started_stays_ignored() -> None:
    """Found by the code review of phase 20: `nohup adk-spec verify` stopped when its terminal closed, the ignored
    SIGHUP turned into an interrupt."""
    held = {number: signal.getsignal(number) for number in (signal.SIGHUP, signal.SIGTERM)}
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    try:
        cli.interrupt_on_signals()
        assert signal.getsignal(signal.SIGHUP) is signal.SIG_IGN
        # Found by the second code review: kept ignored, a SIGTERM went unheard and the tests outlived the SIGKILL.
        assert signal.getsignal(signal.SIGTERM) is signal.default_int_handler
    finally:
        for number, handler in held.items():
            signal.signal(number, handler)


@_posix_only
def test_an_interrupt_while_a_command_is_given_time_still_stops_it() -> None:
    """Found by the code review of phase 20: an interrupt in the wait after SIGTERM skipped the stop that follows, and
    a command that does not hear SIGTERM ran on."""
    from adk_spec.workspace.process import started, stop

    deaf = (
        "import signal, time\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)\nprint('ready', flush=True)\ntime.sleep(60)"
    )
    process = started([sys.executable, "-c", deaf], env=dict(os.environ))
    assert process.stdout is not None and process.stdout.readline() == b"ready\n"

    def interrupted(timeout=None):  # noqa: ARG001 - Popen.wait's own
        raise KeyboardInterrupt

    process.wait = interrupted  # pyrefly: ignore[bad-assignment] - an interrupt in the wait, as a second Ctrl-C
    with pytest.raises(KeyboardInterrupt):
        stop(process)
    del process.wait
    assert process.wait(timeout=5) != 0
