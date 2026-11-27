# MCP setup written by init: phase 28

Designed on 27 November 2026. The owner asked "can we simplify mcp installation on vs code with github copilot on
windows os?", and chose it over a terminal UI. Until now a person wrote `.vscode/mcp.json` by hand, with the path of
their adk-spec checkout: on Windows a `C:\...` path whose every backslash JSON needs escaped.

## The owner's decisions

1. **`init` writes the entry, always**, into `.mcp.json` at the repository's root, as it writes the Agent Skill, and
   the repository commits it. VS Code's documentation (read on 27 November 2026) calls `.vscode/mcp.json` its older
   format and a root `.mcp.json` the one to share through source control; Claude Code reads the same file.
2. **The entry runs `adk-spec-mcp` from PATH**, the same on every machine, never one person's folder. Where it is
   not on PATH, `init` prints the one command that puts it there, `uv tool install --editable <adk-spec's folder>`.

## Goals

- `init` and `init --refresh` (with or without `--no-explore`) add `{"type": "stdio", "command": "adk-spec-mcp"}`
  under `mcpServers` as `adk-spec`. No argument: the server's root defaults to the folder an editor starts it in,
  the workspace's.
- The servers a `.mcp.json` holds are kept, and its other keys; an `adk-spec` entry in other words is the person's,
  kept and said; a file that is no JSON object of servers (one with a comment, say) is left and said; a link is not
  written through.
- Where `.vscode/mcp.json` starts `adk-spec-mcp` already, no second entry is written, which VS Code would start twice.
- None of it fails `init`, as the skill's write never does.

## Calls made in the design (the builder's)

- **The PATH hint** is said where the entry is adk-spec's (written, added, or there already), not where a person's
  own entry or file stands, which may start it another way.
- **The file is written again in canonical JSON** (two spaces) where an entry is added: a `.mcp.json` holds no
  comments, which would not have read.
