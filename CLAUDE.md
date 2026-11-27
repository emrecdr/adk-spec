# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`adk-spec`: spec-driven development on Google ADK, a hybrid of OpenSpec and GitHub Spec Kit. Models draft specs and
judge them; Python owns the files, the requirement IDs, the gates, the approvals and the merge into one living spec
per capability. It writes specs and plans and judges the work; it never edits application code. Python 3.14, uv,
macOS and Windows, two model arms: GitHub Copilot (through LiteLLM) and Gemini.

## Commands

```
uv sync --locked                     # install
uv run ruff check .                  # the gate, before every commit, all four
uv run ruff format --check .
uv run pyrefly check
uv run pytest -q
uv run pytest tests/test_revise.py -q -k "keeps_its_tier"    # one file, one test
uv run adk-spec --help               # the command; `python -m adk_spec` runs it too
uv run python scripts/dump_instructions.py                   # every stage's instruction, as a model is sent it
```

**No live model call without the owner's explicit go-ahead, in so many words.** A Copilot token may be cached on the
machine, so these send real requests: `propose`, `plan`, `check` (without `--no-model`), `verify`, `approve` on a
standard or strict change whose check is missing or stale, `init` (without `--no-explore`), `smoke`, `models`,
`login`, `adk-spec-mcp` with a tool that runs one of these, and `python -m scripts.measure`. `--help`, `status`,
`validate`, `new`, `rebase`, `archive` and the test suite call none. The tests' fake model exists only inside pytest; a
command run from a shell has no offline model.

Pins: uv resolves with `exclude-newer = "P3D"` (a three-day cooldown on every release). `litellm` is held at 1.106.2
because `google-adk` 2.15.0 caps it; `login.py` also uses LiteLLM's private Copilot names. `codegraph` (the code graph,
shared with adk-review) is a uv git source pinned by commit: a bump is a reviewed change of the rev, decided with
adk-review's session.

## Architecture

Four layers, each importing only itself and the ones before it: `domain` → `workspace` → `orchestration` →
`interfaces`. `tests/test_layering.py` enforces it and more: each layer's `__init__.py` docstring says what it may
import; `domain` does no I/O; `workspace` imports no network module; only `workspace/process.py` starts a program;
`interfaces/cli.py` imports no engine module at its top, so offline commands start without ADK; nothing builds at
import except `adk_spec/agent.py`, the shape `adk web` loads.

- **domain**: pure. Pydantic models (`model.py`), the Markdown grammars each rendered and parsed back (`*_md.py`; a
  draft that does not read back as written is refused), validation, the change's life (`lifecycle.py`), secret
  scrubbing (`secrets.py`), conversion of model drafts (`drafts.py` → `convert.py`).
- **workspace**: the `.spec/` tree (`layout.py`), atomic writes (`files.py`), the writer lock (`lock.py`), git and the
  set of repositories a change spans (`git.py`, `source.py`), the project's installed libraries a reading may open
  offline as `python:`/`node:` paths (`installed.py`), the Agent Skill `init` writes into the repository (`skill.py`; a
  refresh replaces one whose text is in `SHIPPED`), the MCP entry it adds to the root `.mcp.json` (`mcp_setup.py`), the
  code graph beside the reading, a hint and leads a stage confirms, never the source of truth (`graph.py`), config, what
  stages are given (`context.py`), running the project's tests (`tests.py`, `process.py`).
- **orchestration**: ADK `Workflow` graphs (`graph.py`), one schema-bound `LlmAgent` per stage (`stages/`), the gate
  after each stage (`gate.py`), the code reading (`explore.py`), plugins every app carries (`plugins.py`: schema
  mismatch, token ledger, scrub), the two provider arms (`models.py`, `settings.py`).
- **interfaces**: `cli.py` (argparse, the commands and their printing), `login.py` (Copilot device flow),
  `mcp_server.py` (`adk-spec-mcp`: six commands as MCP tools, each running `python -P -m adk_spec` in its own process;
  no tool approves, archives, overrides or names another repository, which stay the person's; the `verify` tool runs
  only a committed test command, from the approval's base, as `SPEC_TOOL_CALL` tells the command).

Rules that span files and are easy to break:

- **A model's words count only where code finds them.** A statement, a check finding and a verify verdict each quote
  text, and are kept only where `domain/text.py`'s `quoted_at` finds the quote in the file or diff it names.
- **Each stage answers in a schema and passes a gate in code**, at most three tries; the gate's findings go back to
  the stage. Every gate sentence is `coded(code, sentence)` (`domain/lessons_md.py`): drafting gates' send-backs
  that a retry fixed become lines of `.spec/lessons.md`.
- **What each tier demands is one table**, `DEMANDS` in `lifecycle.py` (questions, check, verification, design, the
  stop before the plan, approvers, warnings, override). Read it rather than testing `tier == ...`.
- **An approval is the fingerprints of the change's files** (`lifecycle.approval_files`); any edit voids it, ticking
  a task box does not. `change.json` also records what adk-spec drafted, so `approve` can name a draft a person
  edited. An older adk-spec refuses a `change.json` with a field it does not know.
- **Secrets never reach a model or a recording**: `secrets.scrub`/`scrub_lines` on everything sent, the `Scrub`
  plugin on every app (fail closed), and files or test output holding a private key withheld whole. A link under
  `.spec/` is refused once, where `Workspace.find` opens the tree (`paths.refuse_links`), not at each read.
- **`propose` reads before it drafts**: triage alone, then the reading (`explore.py`) aimed by the request, then the
  brief and deltas from its `context.md` and the profile; the plan reuses that `context.md`. A brief's open points
  name what they wait on (`depends_on`), and a round asks only those answerable now.
- **What a stage is told goes through `workspace/context.py`**, each input capped; stage instructions are built in
  `stages/__init__.py` (`instruction()`, shared sections, the retry findings just before the ending).

`.spec/` in a repository using adk-spec: `config.toml`, `constitution.md`, `profile.md` (written by `init`),
`lessons.md`, `changelog.md` (an entry per archive), `specs/<capability>/spec.md` (living specs) and `evidence.md`
beside it (the lines `verify` proved each requirement with, one entry a line, folded in at archive), `changes/<id>/`
(`brief.md`, `specs/<capability>/spec.md` deltas, `design.md`, `tasks.md`, `context.md`, `evidence.md`, `reports/`
with `review.md`, `verify.md`, `remaining.md`, `summary.md`, `change.json`), `runs/` (recordings, git-ignored). None
of the evidence, changelog or report files enters an approval's fingerprints.

## Working conventions

- **Golden rule, the owner's:** few commands and simple one-pass flows, little detail on screen. Do not add a
  subcommand; make an existing command do more.
- Tests: the `fake_provider` fixture (`tests/conftest.py`) answers each stage by the opening of its instruction
  (`answers_when`, `answers_each_time`; `answers_if_asked` for a stage a test may not reach), and fails a test whose
  rule no request matched; `seeded(tmp_path)` makes a workspace with a living spec and one change. Test
  names are sentences of the behaviour; do not name a helper `test*`. Ruff keeps complexity at 10 and lines at 120.
- `.github/copilot-instructions.md` gives GitHub Copilot the same guidance as this file, with folder rules in
  `.github/instructions/`, and `.github/workflows/copilot-setup-steps.yml` readies Copilot's cloud agent: change them
  together with this file.
- Docs: designs in `docs/superpowers/specs/`, plans in `docs/superpowers/plans/`, the roadmap and every phase's state
  in `docs/superpowers/plans/README.md`, live measurements in `docs/measurements/`. A phase is designed with the
  owner's decisions recorded, built test first, cleaned up and code-reviewed, then merged locally.
- `docs/reports/` and `docs/research_notes/` hold the research the project rests on. The owner's numbered files
  (`docs/reports/01-…` to `03-…`, `docs/research_notes/Spec driven framework on Google ADK/01-…` to `06-…`) are
  theirs: do not edit them.
