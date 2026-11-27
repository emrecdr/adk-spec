# Copilot instructions for adk-spec

These instructions carry the same guidance as `CLAUDE.md` at the repository root; change the two together. Rules for
particular folders are in `.github/instructions/`.

## What this is

`adk-spec`: spec-driven development on Google ADK, a hybrid of OpenSpec and GitHub Spec Kit. Models draft specs and
judge them; Python owns the files, the requirement IDs, the gates, the approvals and the merge into one living spec
per capability. It writes specs and plans and judges the work; it never edits application code. Python 3.14, uv,
macOS and Windows, two model arms: GitHub Copilot (through LiteLLM) and Gemini.

## Hard limits

- **Never run a command that calls a model.** A Copilot token may be cached on the owner's machine, so these send real
  requests on the owner's account: `adk-spec propose`, `plan`, `check` (without `--no-model`), `verify`, `approve` on
  a standard or strict change whose check is missing or stale, `init` (without `--no-explore`), `smoke`, `models`,
  `login`, `adk-spec-mcp` with a tool that runs one of these, and `python -m scripts.measure`. Only the owner starts
  them. `--help`, `status`, `validate`, `new`, `rebase`, `archive` and the test suite call none. The tests' fake model
  exists only inside pytest; a command run from a shell has no offline model.
- **Never read or print a secret**: no `.env` file, nothing under `~/.config/litellm`, no key or token in a log, a
  test or a commit.
- **The owner's numbered research files are theirs**: `docs/reports/01-…` to `03-…` and
  `docs/research_notes/Spec driven framework on Google ADK/01-…` to `06-…`. Do not edit them.
- **Golden rule, the owner's:** few commands and simple one-pass flows, little detail on screen. Do not add a
  subcommand; make an existing command do more.

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

CI runs the four gate commands on Windows, Ubuntu and macOS with `PYTHONUTF8=1`. Ruff keeps complexity at 10 and lines
at 120. Pins: uv resolves with `exclude-newer = "P3D"` (a three-day cooldown on every release). `litellm` is held at
1.106.2 because `google-adk` 2.15.0 caps it; `login.py` also uses LiteLLM's private Copilot names. Do not raise either
pin.

## Architecture

Four layers, each importing only itself and the ones before it: `domain` → `workspace` → `orchestration` →
`interfaces`. `tests/test_layering.py` enforces it and more: each layer's `__init__.py` docstring says what it may
import; `domain` does no I/O; `workspace` imports no network module; only `workspace/process.py` imports
`subprocess` and starts a program; `interfaces/cli.py` imports no engine module at its top, so offline commands start
without ADK; nothing builds at import except `adk_spec/agent.py`, the shape `adk web` loads.

- **domain**: pure. Pydantic models (`model.py`), the Markdown grammars each rendered and parsed back (`*_md.py`; a
  draft that does not read back as written is refused), validation, the change's life (`lifecycle.py`), secret
  scrubbing (`secrets.py`), conversion of model drafts (`drafts.py` → `convert.py`).
- **workspace**: the `.spec/` tree (`layout.py`), atomic writes (`files.py`), the writer lock (`lock.py`), git and the
  set of repositories a change spans (`git.py`, `source.py`), the project's installed libraries a reading may open
  offline as `python:`/`node:` paths (`installed.py`), the Agent Skill `init` writes into the repository (`skill.py`; a
  refresh replaces one whose text is in `SHIPPED`), the MCP entry it adds to the root `.mcp.json` (`mcp_setup.py`),
  config, what stages are given (`context.py`), running the project's tests and other programs (`tests.py`,
  `process.py`).
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

- Build test first: write the test, watch it fail, then make it pass, and run the whole gate before a commit.
- Before building, read the code, the plan and the sources it rests on, and confirm each assumption. Leave out a big
  or risky change that buys little, and say so.
- Code, docstrings and messages are plain sentences of what a thing is or does. Error messages say what is wrong and
  what to do next.
- Docs: designs in `docs/superpowers/specs/`, plans in `docs/superpowers/plans/`, the roadmap and every phase's state
  in `docs/superpowers/plans/README.md`, live measurements in `docs/measurements/`. A phase is designed with the
  owner's decisions recorded, built test first, cleaned up and code-reviewed, then merged.

## Reviewing a change

Check, beyond correctness:

- The layering rules above, and that a program is started only through `workspace/process.py`.
- Tier behaviour read from `DEMANDS`, not from a test of the tier's name.
- A model's quoted text checked with `quoted_at` before it is kept; everything sent to a model scrubbed.
- A new gate sentence written as `coded(code, sentence)`.
- A test for each behaviour, named as a sentence of it, and no test that would call a real model.
- No new subcommand, and no more detail printed than the person needs.
