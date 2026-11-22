"""`python -m adk_spec`: the command, as the installed `adk-spec` runs it. The MCP server starts each tool's command
this way, in a process of its own."""

from __future__ import annotations

import sys

from .interfaces.cli import run

sys.exit(run())
