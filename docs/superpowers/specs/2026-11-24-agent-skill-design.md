# The Agent Skill `init` writes

A small change, decided by the owner on 23 November 2026 after the third audit.

## Intent

A coding assistant should know how to use adk-spec in a repository that uses it, with nothing set up. The MCP server
(phase 14) does this for an editor configured for it; most assistants are not. The open Agent Skills form
(agentskills.io, donated to the Agentic AI Foundation in October 2026) is read by GitHub Copilot (agent mode in VS Code,
the CLI, the cloud agent) and by Claude Code from `.claude/skills/<name>/SKILL.md` in the repository.

## Approaches

- **`init` writes the skill into the repository** (chosen). One file, written once, committed by the person with
  `.spec/`. Copilot and Claude Code both read `.claude/skills/`; no install step.
- **Ship the skill with the package.** Not possible as such: no editor installs a skill from a Python package. A
  Claude Code plugin, a VS Code extension or `gh skill` would each be a distribution of its own to keep.
- **No skill.** The README and the MCP server's instructions only; an assistant without the server knows nothing.

## Decisions

- The owner's: `init` writes it. Asked in a dialog with "Not now" recommended for writing outside `.spec/`; the owner
  chose "Yes, init writes it".
- Mine, as calls: the path is `.claude/skills/adk-spec/SKILL.md`, the folder named as the skill, as the standard asks;
  it is written only where none is there, and never over one, since it is the person's after `init`; `init --refresh`
  writes it where missing, for a workspace made before this change; one line says it was written. Its text says what
  the MCP server's instructions say: the commands an assistant may run, that `propose`, `plan`, `check` and `verify`
  call a model and cost time, that approving, archiving and every `--override` stay the person's, and how to
  implement from a change's folder and tick tasks. The cleanup review found the two texts had drifted: the skill now
  also leaves `--with` to the person, as the server does, and one test holds both to the same rules.
- Left for later, from the cleanup review: `init --refresh` refuses `--no-explore`, so a workspace made before the
  skill gets it only with a new reading. Letting `--refresh --no-explore` write what is missing and read nothing is a
  few lines, but changes what that pair of options means, for the few workspaces made before this change.

## Non-goals

No new command. No skill for `.github/skills/` or `.agents/skills/` as well: Copilot reads `.claude/skills/`, and
Claude Code reads only that one. No update of a skill already written: a later adk-spec's text reaches a repository
only where the person deletes theirs and runs `init --refresh`.
