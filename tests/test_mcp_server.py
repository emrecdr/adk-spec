"""`adk-spec-mcp`: six of adk-spec's commands served to a coding assistant over MCP, each run as the terminal runs
it. Approving and archiving stay a person's command."""

from __future__ import annotations

import subprocess
import sys

from conftest import ROOT


def test_python_m_adk_spec_runs_the_command() -> None:
    """The server runs each tool's command as `python -m adk_spec`, in a process of its own."""
    done = subprocess.run([sys.executable, "-m", "adk_spec", "--help"], cwd=ROOT, capture_output=True, check=False)
    assert done.returncode == 0 and b"Everyday:" in done.stdout
