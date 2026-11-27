"""The MCP server's entry `init` writes into the repository: `.mcp.json` at its root, which GitHub Copilot in VS Code
and Claude Code both read, so that an assistant has adk-spec's tools with no JSON written by hand.

The owner's choices, 27 November 2026: it is written always, as the skill is, and committed with the repository; the
entry runs `adk-spec-mcp` from PATH, the same on every machine, and never a folder of one person's (`init` names the
install where it is not on PATH). VS Code's documentation calls `.vscode/mcp.json` its older format, and a `.mcp.json`
at the root the one to share through source control.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from .files import read_text, write_text
from .paths import inside

#: The file, from the repository's root, and adk-spec's entry in it: no argument, as the server's root is the folder
#: an editor starts it in, the workspace's.
MCP_FILE = ".mcp.json"
SERVER, ENTRY = "adk-spec", {"type": "stdio", "command": "adk-spec-mcp"}

#: VS Code's older file, which the README once had a person write by hand.
OLDER_PARTS = (".vscode", "mcp.json")

Done = Literal["wrote", "added", "kept", "skipped", "elsewhere"]


def write_mcp(root: Path) -> Done | None:
    """adk-spec's entry in the `.mcp.json` of the repository at `root`: `wrote` where there was no file, `added`
    beside the servers it holds, `kept` where it names adk-spec in other words, which are the person's, `skipped` where
    it is no JSON object of servers, left as it is, and `elsewhere` where `.vscode/mcp.json` starts adk-spec already,
    which VS Code would start twice; nothing where it holds the entry now. `PathError` where the file is a link."""
    path = inside(root, MCP_FILE)
    existed = path.exists()
    try:
        held = json.loads(read_text(path)) if existed else {}
    except json.JSONDecodeError:  # a comment too, which plain JSON has none of
        return "skipped"
    servers = held.get("mcpServers", {}) if isinstance(held, dict) else None
    if not isinstance(servers, dict):
        return "skipped"
    if SERVER in servers:
        return None if servers[SERVER] == ENTRY else "kept"
    older = root.joinpath(*OLDER_PARTS)
    if older.is_file() and ENTRY["command"] in read_text(older):
        return "elsewhere"
    write_text(path, json.dumps({**held, "mcpServers": {**servers, SERVER: ENTRY}}, indent=2) + "\n")
    return "added" if existed else "wrote"
