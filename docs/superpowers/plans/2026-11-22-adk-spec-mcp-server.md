# adk-spec as an MCP Server: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `adk-spec-mcp` serves six of adk-spec's commands as MCP tools to a coding assistant, each running the
command as the terminal does and returning its lines.

**Architecture:** `adk_spec/__main__.py` makes `python -m adk_spec` the command; `adk_spec/interfaces/mcp_server.py`
builds an `MCPServer` whose tools turn their arguments into the command's argv and run it through `process.run`.

**Spec:** `docs/superpowers/specs/2026-11-22-mcp-server-design.md`

## Global Constraints

- `mcp==2.3.0`. No subcommand of `adk-spec`. No live model call in the build. Gate after each task.

## Review Focus

1. A request or path holding a quote, a space or a dash first: it reaches the command as one argument. Task 2.
2. A command that prints nothing, or fails: the tool says how it ended. Task 2.
3. No tool offers `approve`, `archive` or `--override`. Task 2.

---

### Task 1: The package, and `python -m adk_spec`

- [ ] Failing test; `uv add mcp==2.3.0`; `adk_spec/__main__.py`; gate; commit.

### Task 2: The server and its six tools

- [ ] Failing tests; `adk_spec/interfaces/mcp_server.py`; `adk-spec-mcp` in `[project.scripts]`; gate; commit.

### Task 3: How to set it up

- [ ] README section, usage guide, roadmap; commit.
