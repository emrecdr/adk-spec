"""`adk-spec-mcp`: six of adk-spec's commands served to a coding assistant over MCP, each run as the terminal runs
it. Approving and archiving stay a person's command."""

from __future__ import annotations

import asyncio
import os
import sys

import pytest
from conftest import seeded

from adk_spec.interfaces import cli, mcp_server
from adk_spec.interfaces.mcp_server import INSTRUCTIONS, build_server


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
        "propose": {"request": request, "id": "pk", "tier": "strict", "with_repositories": ["web=../web"]},
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
    assert (read["propose"]["id"], read["propose"]["tier"], read["propose"]["with_"]) == (
        "pk",
        "strict",
        ["web=../web"],
    )
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
    sleeper = f"import os, time\nopen({str(marker)!r}, 'w').write(str(os.getpid()))\ntime.sleep(60)\n"
    monkeypatch.setattr(mcp_server, "command", lambda _root, *_args: [sys.executable, "-c", sleeper])
    call = asyncio.create_task(mcp_server.ran(tmp_path, ["status"]))
    for _ in range(100):
        if marker.exists() and marker.read_text():
            break
        await asyncio.sleep(0.05)
    call.cancel()
    with pytest.raises(asyncio.CancelledError):
        await call
    pid = int(marker.read_text())
    for _ in range(100):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        await asyncio.sleep(0.05)
    pytest.fail("the command still runs after its call was cancelled")
