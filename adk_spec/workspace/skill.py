"""The Agent Skill `init` writes into the repository: how a coding assistant uses adk-spec.

The owner's choice, 23 November 2026, after the third audit: a skill, in the open Agent Skills form (agentskills.io),
is read by GitHub Copilot and by Claude Code from `.claude/skills/`, so an assistant knows how to use adk-spec with
nothing set up, where the MCP server needs an editor's configuration. It is written once and is the person's after
that: never written over, and committed with the repository as `.spec/` is.
"""

from __future__ import annotations

from pathlib import Path

from .files import write_text
from .paths import inside

#: Where the skill stands, from the repository's root: the folder's name is the skill's, as the standard asks.
SKILL_PARTS = (".claude", "skills", "adk-spec", "SKILL.md")

SKILL_TEXT = """\
---
name: adk-spec
description: Plan, check and verify changes to this repository with adk-spec, spec-driven development whose files \
live in .spec/. Use when the person asks to propose, specify or plan a change, to implement an approved change from \
.spec/changes/, to verify work against its requirements, or what to do next with a change.
---

# adk-spec

This repository uses adk-spec: a change is planned as files in `.spec/changes/<id>/` before code is written, and the
finished work is judged against them. adk-spec never edits code: you implement.

## Commands you may run

Run them in the repository. Where the shell does not find `adk-spec`, ask the person how it is installed: often
`uv run --project <path to adk-spec> adk-spec`.

- `adk-spec status`: each open change and its next step. Run it first.
- `adk-spec propose --no-input "<request>"`: drafts a change. It asks no question and prints each point left open
  with a suggested answer: put them to the person, then revise the change with their answers,
  `adk-spec propose --no-input --id <id> "<the answers>"`.
- `adk-spec plan <id>`: drafts the tasks again, after the brief or the specs changed.
- `adk-spec check <id>`: checks the change's files against each other.
- `adk-spec verify <id>`: runs the project's tests and judges the work against each requirement.
- `adk-spec validate`: checks the structure of the specs.

`propose`, `plan`, `check` and `verify` call a model, cost tokens and take minutes, `propose` the most: run each with
your longest timeout or in the background, wait for it to end, and run it once for a request, never to poll.

## What stays the person's

Never run `adk-spec approve`, `adk-spec archive`, `adk-spec init`, any command with `--override`, or one that names
another repository with `--with`. Approving, archiving and setting a finding aside record the person's own decision,
and another repository's code would be sent to a model: when a change needs one of them, tell the person the command
to run. A strict change's plan waits for the person to read its brief and specs: run `plan` for it once they say so.

## Implementing an approved change

1. Read `brief.md`, the specs under `specs/`, `context.md` and `design.md`, where there is one, in
   `.spec/changes/<id>/`.
2. Work through `tasks.md` in order, test first.
3. Tick each task's box, `- [ ]` to `- [x]`, once it is done. Ticking keeps the approval; any other edit of the
   change's files voids it, so change no other file in `.spec/`.
4. Run `adk-spec status` and do the step it names: `adk-spec verify <id>` where the change owes a verification, and
   work on what it finds `unmet` or `unclear`.
"""


def write_skill(root: Path) -> Path | None:
    """The skill written into the repository at `root`, where it has none: the path written, or nothing where one is
    there already, which is the person's."""
    path = inside(root, *SKILL_PARTS)
    if path.exists():
        return None
    write_text(path, SKILL_TEXT)
    return path
