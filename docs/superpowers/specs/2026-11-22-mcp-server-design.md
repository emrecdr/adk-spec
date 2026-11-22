# adk-spec inside a coding assistant: an MCP server

Design for phase 14 of adk-spec. Written on 22 November 2026.

**What the owner decided, and when.** 22 November 2026, in two dialogs, all as recommended:

- The second way to use adk-spec is **an MCP server for coding assistants**.
- **Add the `mcp` package, 2.3.0**, which resolves with the pinned stack under the three-day cooldown and adds eight
  packages, `pywin32` on Windows alone.
- **A thin server**: each tool runs the command as the terminal does, asking no question, and returns its lines.
  `cli.py` is not split.
- **Every command but `approve` and `archive`** is a tool: approving and archiving record a person's decision, and
  stay a command the person runs.
- **The stages run on adk-spec's own provider**, as from the terminal, not on the assistant's model through MCP
  sampling.

Everything else is the builder's call, listed at the end.

## Intent, and why

Both parent projects live inside coding assistants, and the outside review of 22 November 2026 named it the biggest
gain in daily use on Windows. A person who drafts a change, implements its tasks with an assistant and verifies the
work should not have to leave the editor to ask adk-spec for each step.

## How it works

```
.vscode/mcp.json (VS Code with GitHub Copilot)
{ "servers": { "adk-spec": { "type": "stdio", "command": "uv",
    "args": ["run", "--project", "/path/to/adk_spec", "adk-spec-mcp"] } } }

claude mcp add adk-spec -- uv run --project /path/to/adk_spec adk-spec-mcp      (Claude Code)
```

- **`adk-spec-mcp`**, a second program beside `adk-spec`, serves over stdio from the folder the editor starts it in,
  or `--root`. It is no subcommand: a person names it once, in the editor's settings.
- **Six tools**: `propose` (with `id` naming an open change, it revises it), `plan`, `check`, `verify`, `status`,
  `validate`, with the terminal's own options, less those that record a person's decision: no `--override`.
- **Each tool runs `adk-spec`** in a process of its own, through `workspace/process.py`, with `--no-input`, and returns
  what it printed and how it ended. The workspace's lock, its recordings, its token ceiling and its next line are the
  terminal's, unchanged.
- **Open points come back as text.** The assistant asks the person, then revises the change with `propose` and its id.
- **The server's instructions** tell the assistant that `approve` and `archive` are the person's: it names the command
  for them to run in the editor's terminal.

## Anti-goals

- An assistant approves or archives a change, or sets a finding aside with a reason of its own.
- A tool behaves otherwise than the command it runs.
- A command's output reaches the protocol's own stream.

## Decided by the builder, for the owner to check

1. The program is `adk-spec-mcp`, beside `adk-spec`, and runs `python -m adk_spec` for each tool.
2. A tool waits up to an hour for its command; a client may give up sooner, and its own setting decides.
3. `verify` keeps `--base`, and leaves `--override` to the person.

## How it is proven

Offline: the server lists the six tools and no others; each tool builds the command line the terminal would take,
`--no-input` on `propose`; `status` and `validate` run end to end on a seeded workspace; `python -m adk_spec` runs the
command.
