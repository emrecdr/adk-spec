"""The Agent Skill `init` writes into the repository: how a coding assistant uses adk-spec.

The owner's choice, 23 November 2026, after the third audit: a skill, in the open Agent Skills form (agentskills.io),
is read by GitHub Copilot and by Claude Code from `.claude/skills/`, so an assistant knows how to use adk-spec with
nothing set up, where the MCP server needs an editor's configuration. It is committed with the repository as `.spec/`
is. A refresh gives it the text adk-spec has now where it holds one adk-spec wrote, known by its hash; one a person
edited is theirs, and kept (the audit of 25 November, C3: written once, an install never had a better text).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from .files import read_text, write_text
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

## What the person asks, and what to run

- "what is next?" or "where are we?": run `adk-spec status` and say the step it names.
- A feature, a fix or a change of behaviour: `adk-spec propose --no-input "<request>"`, then put the points it left
  open to the person.
- "implement <id>": follow "Implementing an approved change" below; a change not yet approved waits for the person to
  run `adk-spec approve <id>`.
- "is it done?" or "check the work": `adk-spec verify <id>`.

At each of them, stop where the person decides: an open point, a strict change's reading, an approval, an archive.

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
4. Run `adk-spec status` and do the step it names: `adk-spec verify <id>` where the change owes a verification.
   Where it leaves requirements unmet, work from `reports/remaining.md` in the change's folder, then verify again.
   Put `reports/summary.md` in the pull request.
"""


#: The hash of each skill text adk-spec has written, line ends as LF: a skill holding one is adk-spec's, and a
#: refresh gives it the text adk-spec has now. A test holds the list to the text: change it, and add its hash here.
SHIPPED = frozenset(
    {
        "47e9424dde775d1682a9dbb08b956f3f933c792782f0caada80e61998adde8c9",  # 18f9839
        "ed51f2d572f68659c5618cc99be09ad981ef2c0863dca489a948e22ec9d278f0",  # 83bd317
        "b581cfcb44924462d53add2a3e76ada3efaa4db63aae9dcbf8bba4a6d7ffc33d",  # a22a99c
        "abf6a8828005ac90fc5f93e16e5ac91e5d1163a6708b8de1dee2ade883c33014",  # phase 23
    }
)


def write_skill(root: Path) -> tuple[str, Path] | None:
    """The skill written into the repository at `root`: `wrote` where it had none, `replaced` where it held a text
    adk-spec wrote before, `kept` where a person edited it, which is theirs; nothing where it holds the text now."""
    path = inside(root, *SKILL_PARTS)
    if not path.exists():
        write_text(path, SKILL_TEXT)
        return "wrote", path
    held = read_text(path)
    if held == SKILL_TEXT:
        return None
    if hashlib.sha256(held.encode()).hexdigest() not in SHIPPED:
        return "kept", path
    write_text(path, SKILL_TEXT)
    return "replaced", path
