"""`adk-spec-mcp`: six of adk-spec's commands served to a coding assistant over MCP, each run as the terminal runs
it. Approving and archiving stay a person's command."""

from __future__ import annotations

import subprocess
import sys

import pytest
from conftest import ROOT


def test_python_m_adk_spec_runs_the_command() -> None:
    """The server runs each tool's command as `python -m adk_spec`, in a process of its own."""
    done = subprocess.run([sys.executable, "-m", "adk_spec", "--help"], cwd=ROOT, capture_output=True, check=False)
    assert done.returncode == 0 and b"Everyday:" in done.stdout


def server_on(root):
    from adk_spec.interfaces.mcp_server import build_server

    return build_server(root)


@pytest.mark.asyncio
async def test_the_server_offers_six_tools_and_leaves_approving_and_archiving_to_the_person(tmp_path) -> None:
    """The owner's choice: approving and archiving record a person's decision, and stay a command the person runs."""
    from adk_spec.interfaces.mcp_server import INSTRUCTIONS

    names = sorted(tool.name for tool in await server_on(tmp_path).list_tools())
    assert names == ["check", "plan", "propose", "status", "validate", "verify"]
    assert "adk-spec approve" in INSTRUCTIONS and "adk-spec archive" in INSTRUCTIONS


def test_each_tool_takes_the_command_line_the_terminal_would(tmp_path) -> None:
    from adk_spec.interfaces import mcp_server as server

    request = '-starts with a dash, and "quotes"'
    propose = server.propose_argv(request, id="pk", tier="strict", with_repositories=["../api", "web=../web"])
    assert propose == [
        "propose",
        "--no-input",
        "--id=pk",
        "--tier=strict",
        "--with=../api",
        "--with=web=../web",
        "--",
        request,
    ]
    assert server.propose_argv("x", no_explore=True) == ["propose", "--no-input", "--no-explore", "--", "x"]
    assert server.plan_argv("pk", replace=True) == ["plan", "--replace", "--", "pk"]
    assert server.verify_argv("pk", bases=["api=abc"]) == ["verify", "--base=api=abc", "--", "pk"]
    assert server.check_argv("pk", no_model=True) == ["check", "--no-model", "--", "pk"]
    assert server.status_argv(include_archived=True) == ["status", "--all"]
    assert server.validate_argv("pk", strict=True) == ["validate", "--strict", "--", "pk"]
    assert server.command(tmp_path, "status")[-3:] == ["--root", str(tmp_path), "status"]


@pytest.mark.asyncio
async def test_status_and_validate_run_through_the_server_as_in_the_terminal(tmp_path) -> None:
    """End to end, with no model: each tool runs `python -m adk_spec` in a process of its own and returns its lines."""
    from conftest import seeded

    seeded(tmp_path)
    server = server_on(tmp_path)
    status = await server.call_tool("status", {})
    validated = await server.call_tool("validate", {"id": "passkeys"})
    said = [part.text for result in (status, validated) for part in result.content]
    assert "passkeys" in said[0] and "next" not in said[0].lower().split("passkeys")[0]
    assert "(adk-spec ended with exit 2)" not in said[1], "the change named after `--` reached the command"
