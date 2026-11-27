# adk-spec

adk-spec turns a request such as "let users sign in with a passkey" into a written, reviewed plan before any code
is written, and afterwards checks the finished code against that plan. It is spec-driven development, run on Google
ADK with GitHub Copilot's or Gemini's models: models draft the specs and judge the work; plain Python owns the files,
the requirement IDs, the checks, the approvals and the record.

**Contents:** [What it is for](#what-it-is-for) · [How it works](#how-it-works) ·
[Where things live](#two-folders-where-adk-spec-lives-and-where-you-run-it) · [Install](#install-once) ·
[Choose a model](#choose-a-model-once) · [Start in a repository](#start-in-a-repository-once-per-repository) ·
[Your first change](#your-first-change-step-by-step) · [Use cases](#use-cases) ·
[When something goes wrong](#when-something-goes-wrong) · [Commands](#command-reference) ·
[Settings](#settings-reference) · [What each command does, in depth](#what-each-command-does-in-depth) ·
[Developing adk-spec](#developing-adk-spec)

## What it is for

A coding assistant writes code straight from a chat message. What was meant is lost in the chat, nothing records
what was agreed, and nothing checks the result against it. adk-spec puts a short written plan between the request
and the code, and keeps it:

- **Before the code:** it reads the code that matters for your request, asks you only what the code cannot answer,
  and writes the change as files you can read and edit: why and what (`brief.md`), the requirements with their
  scenarios (`specs/`), what the code already is (`context.md`), a design where one is owed (`design.md`) and the
  tasks (`tasks.md`).
- **The decision:** you read the files, edit them, and approve them. A check runs first and stops on contradictions
  or gaps between the files.
- **After the code:** it runs your tests, reads the diff, and gives each requirement a verdict, keeping a `met` only
  where it can point at the lines that show it.
- **The record:** a finished change is folded into one living spec per capability (`.spec/specs/auth/spec.md`), so
  the next change starts from what the system really does.

adk-spec writes specs and plans and judges the work. **It never edits your code**: you implement the tasks, by hand or
with the coding assistant you already use (GitHub Copilot, Claude Code, Cursor and others). Your project can be in
any language; adk-spec reads it through git.

## How it works

One change takes four commands, one for each decision that is yours. Everything the tool can do by itself happens
inside them.

```text
 you: "Let users sign in with a passkey."
        │
        ▼
 adk-spec propose "…"      sizes the request, reads the code, asks what the code cannot answer,
        │                  writes brief.md, specs/, context.md, design.md (where owed), tasks.md
        ▼
 you read and edit the files in .spec/changes/<id>/
        │
        ▼
 adk-spec approve <id>     checks the files against each other, then records your approval
        │
        ▼
 you (or your coding assistant) implement tasks.md, ticking each box
        │
        ▼
 adk-spec verify <id>      runs your tests, judges the diff against each requirement
        │
        ▼
 adk-spec archive <id>     folds the change into the living specs in .spec/specs/
```

| Command | The question it answers | What happens inside |
|---|---|---|
| `propose` | What do we want to build? | Sizes the request, reads the code that matters for it, asks you only what the code cannot answer, writes the brief and the specs, the design where one is owed, and the tasks |
| `approve` | Do I agree with this plan? | Records what the change is written against, checks the files against each other, stops on anything blocking, then records your approval |
| `verify` | Is it built? | Runs your tests and judges what changed in the repository against each requirement. Run it as often as you like |
| `archive` | Make it the record? | Folds the change into the living specs, all of it or none |

Not every change needs all four. `propose` sizes each request into a **tier**, or you name one with `--tier`:

| Tier | For | Commands | What it owes |
|---|---|---|---|
| none | a typo, a comment, a cosmetic edit | `propose` only, which says no spec is owed and writes nothing | nothing |
| `lean` | a small, contained change or bug fix | `propose`, `approve`, `archive` | no check, no verification |
| `standard` | an ordinary feature (the default) | `propose`, `approve`, `verify`, `archive` | a check before approval, a verification before archive |
| `strict` | many capabilities, a high risk of regression, an audit trail | `propose`, `plan`, `approve` twice, `verify`, `archive` | always a design; you read the brief before the plan; two different approvers; a warning blocks as an error does |

At any time, `adk-spec status` says what to do next, and every command that moves a change ends on a `next` line
that says the same.

## Two folders: where adk-spec lives, and where you run it

adk-spec is installed once, in a folder of its own. You run it **inside the repository you are working on**, your
project, never inside adk-spec's own folder:

```text
~/tools/adk_spec/          adk-spec itself: installed once; holds .env, your model settings
~/code/shop/               your project's git repository: run every adk-spec command here
├── .spec/                 written by adk-spec; commit it with your code
│   ├── config.toml        this repository's settings for adk-spec
│   ├── constitution.md    the rules every change follows
│   ├── profile.md         what the code is, as init read it
│   ├── lessons.md         corrections every draft follows
│   ├── specs/             the living specs: one folder per capability
│   └── changes/           one folder per change: brief.md, specs/, context.md, design.md, tasks.md, reports/
├── .claude/skills/adk-spec/SKILL.md   written by init: how your coding assistant uses adk-spec; commit it too
├── src/
└── tests/
```

- `adk-spec init` makes `.spec/` in the folder you run it in: run it at the root of your project's repository.
- Every other command finds `.spec/` in the folder you are in or any folder above it, so you can run it from
  anywhere inside the repository. `--root <folder>` points it at another repository without moving there.
- Commit `.spec/` with your code: the specs and the changes are shared through git like any other file. What must
  not be shared ignores itself: `.spec/runs/` (recordings of what was sent to the model) and the lock files.

## Install (once)

You need [uv](https://docs.astral.sh/uv/) and git. uv fetches Python 3.14 for adk-spec by itself; your project
needs no Python. macOS and Windows are supported.

```shell
git clone <adk-spec repository URL> ~/tools/adk_spec
cd ~/tools/adk_spec
uv sync --locked
cp .env.example .env        # your model settings: see "Choose a model"
```

Then give yourself an `adk-spec` command that works in any folder. Either one of these:

- **A shell alias** (runs the exact versions adk-spec was tested with):

  ```shell
  # macOS and Linux: add to ~/.zshrc or ~/.bashrc
  alias adk-spec='uv run --project ~/tools/adk_spec adk-spec'
  ```

  ```powershell
  # Windows PowerShell: add to your $PROFILE
  function adk-spec { uv run --project "$HOME\tools\adk_spec" adk-spec @args }
  ```

  `uv run --project` runs adk-spec from its own folder's environment while you stay in your project's folder.

- **An installed tool**, which also puts `adk-spec-mcp` on your PATH for the editor setup below:

  ```shell
  uv tool install --editable ~/tools/adk_spec
  ```

  It still reads `~/tools/adk_spec/.env`. It resolves its own versions rather than the lock file: ADK, LiteLLM and
  MCP are pinned and match, other libraries may be a patch newer.

Check it: `adk-spec --help` lists every command. A `git pull` in `~/tools/adk_spec`, then `uv sync --locked`,
updates it.

## Choose a model (once)

adk-spec calls models through one of two arms, chosen in `~/tools/adk_spec/.env`. That file is read from adk-spec's
own folder only, never from your project, and a variable set in your shell wins over it.

**GitHub Copilot** (the default arm): no key. Log in once with GitHub's device flow, then pick a model.

```shell
adk-spec login              # opens GitHub's device flow; the token is cached on this machine
adk-spec models             # lists the models your Copilot plan serves (calls no model)
```

```ini
# ~/tools/adk_spec/.env
SPEC_PROVIDER=copilot
SPEC_MODEL=                 # blank: gpt-4.1; or a name `adk-spec models` lists
```

**Gemini**: an AI Studio key, or Vertex AI with a project.

```ini
# ~/tools/adk_spec/.env
SPEC_PROVIDER=gemini
SPEC_MODEL=                 # blank: gemini-3.8-flash
GOOGLE_API_KEY=<your key>
```

Then check it:

```shell
adk-spec smoke --check      # says whether the arm is ready; sends nothing
adk-spec smoke              # one small model call, to prove the provider answers
```

Two more settings, both optional: `SPEC_FALLBACK_MODEL` names a second model tried when the first answers 429, 5xx
or times out, and `SPEC_<STAGE>_MODEL` gives one stage its own model, for example a stronger one for
`SPEC_VERIFY_MODEL` or a cheaper one for `SPEC_TRIAGE_MODEL`, named as `adk-spec models` lists them. The stages are
`triage`, `scout`, `survey`, `review`, `brief`, `deltas`, `design`, `tasks`, `check` and `verify`.

## Start in a repository (once per repository)

```shell
cd ~/code/shop              # the root of your project's git repository
adk-spec init
```

```text
made      .spec
wrote     .claude/skills/adk-spec/SKILL.md
reading   the code, to describe this repository: up to 7 model calls. --no-explore skips it
explored  42 files: 18 statements kept
wrote     .spec/profile.md
tests     none named: set [verify] test in .spec/config.toml
next      keep what is true in constitution.md, then run `adk-spec propose "<what you want>"`
```

`init` reads your code once and writes `.spec/profile.md`: the stack, the commands, where things live, the
conventions and the risks, each statement quoting the code it rests on. Every later change starts its reading from
it. Rules already true of the code are drafted into `.spec/constitution.md`, each marked with its evidence. It
also writes `.claude/skills/adk-spec/SKILL.md`, an [Agent Skill](https://agentskills.io) that GitHub Copilot and
Claude Code read from the repository: it tells your coding assistant how to use adk-spec, with nothing to set up
(see [below](#from-vs-code-with-copilot-or-claude-code)). It is yours: edit it as you like; `init` never writes over
one that is there.

Then:

1. **Read `.spec/constitution.md`**: keep the rules that are true and wanted, edit or delete the rest. Every stage
   of every change reads it, so keep it short (under 16,000 characters).
2. **Name your test command** in `.spec/config.toml`, so that `verify` runs it (see [Settings](#settings-reference)):
   until one is named, `verify` runs none and says so.
3. **Commit** `.spec/` and the skill: `git add .spec .claude/skills/adk-spec && git commit -m "Add adk-spec"`.
   Where `.gitignore` leaves out `.claude/`, add the skill with `git add -f .claude/skills/adk-spec`.

`init --no-explore` makes the tree with no model call; `init --refresh` reads the code again later and rewrites the
profile, and writes the skill into a repository that has none, as one set up before adk-spec wrote it. That reading
calls a model: `init --refresh --no-explore` adds the skill alone, with no model call. adk-spec reads the skill as
none of your code, as it reads `.spec/`.

## Your first change, step by step

A standard feature, from request to record. The output below is what adk-spec prints; your files, counts and token
numbers will be your own.

### 1. Propose

```shell
adk-spec propose "Let users sign in with a passkey."
```

adk-spec sizes the request and says the tier it chose (a wrong one is stopped here with Ctrl-C and named with
`--tier`), reads the code that matters for it, and asks what only you can decide, at most three questions a round,
each with a suggested answer:

```text
sized     standard: a new way to sign in, within one capability
explored  6 files: 9 statements kept
1 point is open. Type an answer and press Enter; = takes the suggestion, and yes one that says yes; an empty line leaves it open in brief.md.
1. Which browsers are in scope?
   suggested: Evergreen browsers only
answer> =
wrote     .spec/changes/sign-in-with-a-passkey, a standard draft
          .spec/changes/sign-in-with-a-passkey/brief.md
          .spec/changes/sign-in-with-a-passkey/specs/auth/spec.md
          .spec/changes/sign-in-with-a-passkey/context.md
          .spec/changes/sign-in-with-a-passkey/tasks.md
tokens    23,149 in 9 calls
read      brief.md (25 lines, 1 assumption) first
review    .spec/changes/sign-in-with-a-passkey/reports/review.md: 1 added
next      run `adk-spec approve sign-in-with-a-passkey`
```

While a model works, a terminal is told what it does and how long the command has run, `working   reading the code
0:47`; a pipe or a script is not.

Answering a question: type your answer, `=` (or `yes` where the suggestion is a yes) to take the suggestion, or an
empty line to leave the point open. A point left open stays in `brief.md` as `[NEEDS CLARIFICATION: …]`, and the
tasks wait until you settle it there and run `adk-spec plan <id>`.

The change's name comes from the brief's title; `--id passkeys` names it yourself. `--no-input` asks nothing and
prints each open point with its suggestion instead.

### 2. Read and edit

The files in `.spec/changes/sign-in-with-a-passkey/` are yours: edit any of them. `propose` names what to read first
and how many assumptions the brief made where it might have asked you; check those before approving.

`brief.md`, why and what:

```markdown
# Sign in with a passkey

## Why
Passwords are the top source of account takeovers.

## What changes
Users can register a passkey and sign in with it.

## Non-goals
No change to session length.

## Capabilities
- auth

## Assumptions
Browsers in scope support WebAuthn.
```

`specs/auth/spec.md`, the requirements this change adds, modifies or removes in the `auth` capability, each with a
stable ID and scenarios a test could show false:

```markdown
# Delta: auth

## ADDED Requirements

### REQ-AUTH-004: Sign in with a passkey

The system SHALL let a user sign in with a passkey.

#### Scenario: Registered passkey

- WHEN the user presents a registered passkey
- THEN the system starts a session
```

`context.md` is what the reading found: what exists, where the change plugs in, conventions, risks and what is still
unknown, each statement quoting a file and line. It also keeps your answers to the questions `propose` asked, and says
what the reading left out. `tasks.md` is the work, test first, each task naming the
requirements it serves, its files and how to check it:

```markdown
- [ ] T001 [REQ-AUTH-004] Write the failing passkey sign-in test
  - files: tests/test_passkey.py
  - verify: uv run pytest tests/test_passkey.py
```

Changed your mind about what is wanted? Edit the brief or the specs and run `adk-spec plan <id>` to draft the tasks
again, or ask for the change in words: `adk-spec propose "also allow backup codes" --id sign-in-with-a-passkey`.

### 3. Approve

```shell
adk-spec approve sign-in-with-a-passkey
```

```text
checked   .spec/changes/sign-in-with-a-passkey/reports/check.md: 1 finding, 0 blocking
tokens    1,393 in 1 call
approved `sign-in-with-a-passkey` by ana: 3 files recorded
next      implement tasks.md, then run `adk-spec verify sign-in-with-a-passkey`
```

The check runs first: code checks the structure and that every requirement has a task, a model looks for what takes
a reading, such as two files that contradict each other. A blocking finding stops the approval: fix it and approve
again, or approve with `--override "<your reason>"`, which is recorded. The approval records a fingerprint of each
file: any later edit voids it, ticking a task box does not.

Before approving, read `reports/review.md`, which every command that leaves a draft for you to read writes again
(its `review` line names it): each requirement the change adds, whole; each it removes, with the reason and as the
living spec holds it; and each it
modifies, as a diff against the living spec. It also names any other open change that modifies or removes the same
requirement, as `approve` does in a `note` line: whichever of the two is archived second is stopped, to be reworked
onto the first. Where `archive` stops on a living spec that moved, it writes the view again to show what. A spec you
edit by hand is in the view once a command writes it again: `adk-spec check <id> --no-model` does, and calls no model.

### 4. Implement

Work through `tasks.md` yourself or with your coding assistant, ticking each box (`- [x]`) as it is done. A task
marked `[P]` touches other files than the tasks beside it: adk-spec drops the mark from a drafted task where its
files say otherwise, or it names none. For example, to GitHub Copilot or Claude Code:

> Implement `.spec/changes/sign-in-with-a-passkey/tasks.md` task by task, test first. Read `brief.md`, the specs and
> `context.md` in that folder first. Tick each task's box when it is done. Do not edit any other file in `.spec/`.

### 5. Verify

```shell
adk-spec verify sign-in-with-a-passkey
```

```text
testing   uv run pytest -q
tests     passed in 4.2 s
met       REQ-AUTH-004  Sign in with a passkey
verified  yes: 1 of 1 met, tests passed
wrote     .spec/changes/sign-in-with-a-passkey/reports/verify.md
          .spec/changes/sign-in-with-a-passkey/reports/summary.md
tokens    3,866 in 1 call
next      run `adk-spec archive sign-in-with-a-passkey`
```

Each requirement gets `met`, `unmet` or `unclear`. A `met` stands only where the model quoted lines that really are
in the diff; anything else is `unclear`, so missing or invented evidence never reads as a pass. A failing test run
keeps the change from being verified. Run `verify` as often as you like while you work; `--override "<your reason>"`
verifies a change you judge done although a requirement is not shown met.

Where a requirement is not shown met, `verify` also writes `reports/remaining.md`, and the `next` line names the
requirements and the file. For each requirement it lists, first, what code found: a task ticked although its
requirement is unmet, and the files a task named that the work never touched. Then it gives the model's reason,
marked as words that code has not checked. Point your coding assistant at it, then verify again. The file is removed
once every requirement is met.

Each run also writes `reports/summary.md`, Markdown to paste into the pull request: why the change is made, the
requirements it adds, modifies and removes, each verdict, the tests, and who approved.

### 6. Archive

```shell
adk-spec archive sign-in-with-a-passkey
```

```text
archived `sign-in-with-a-passkey`: folded into auth
```

`.spec/specs/auth/spec.md` now holds `REQ-AUTH-004`. Commit the change with the code it describes.

`archive` also keeps the lines `verify` proved each requirement with, in `.spec/specs/auth/evidence.md`, one line
each. Later, `validate` and `status` look for those lines in the code. A requirement none of whose lines is found,
in its file or anywhere else in the repository, is noted as suspect: a refactor may have broken it. This is a note
only, and it never fails CI. To clear it, verify a change that keeps the requirement, or delete its lines in a
reviewed commit. A line from another repository is checked only where that repository is there. A line is looked
for only in files git tracks, with each repository's own exclusions, and in their text as a model is shown it, its
secrets hidden: never in `.git/`, an untracked file, or a secret's own value. A new file counts once you `git add` it.

It also puts an entry first in `.spec/changelog.md`: the change and the day, then each requirement it added,
modified and removed. Anything you write below the heading is kept as it is. A changelog with a code fence never
closed is left as it is, and `archive` says the change's entry was not added: close the fence.

## Use cases

### A small bug fix (`lean`)

```shell
adk-spec propose "Fix: a password with a trailing space is refused" --tier lean --id trailing-space
adk-spec approve trailing-space
# fix the bug and add its test, ticking the tasks
adk-spec archive trailing-space
```

```text
approved `trailing-space` by ana: 3 files recorded
next      implement tasks.md, then run `adk-spec archive trailing-space`
…
archived `trailing-space`: folded into auth
```

A lean change owes no check and no verification. Without `--tier`, `propose` sizes the request itself and may call
a fix that touches security, money or data `strict`.

### A typo or a cosmetic edit (no spec)

```shell
adk-spec propose "Fix the typo in the login docstring"
```

```text
no spec is owed: A typo in a comment changes no behaviour.
tokens    1,180 in 1 call
```

Nothing is written. Make the edit as usual.

### A risky change (`strict`, two approvers)

```shell
adk-spec propose "Store passwords with Argon2 instead of SHA-256" --tier strict --id argon2
```

```text
explored  8 files: 11 statements kept
wrote     .spec/changes/argon2, a strict draft
          .spec/changes/argon2/brief.md
          .spec/changes/argon2/specs/auth/spec.md
          .spec/changes/argon2/context.md
tokens    18,240 in 7 calls
plan      waits: the change is read before it is planned
review    .spec/changes/argon2/reports/review.md: 2 added
next      read brief.md and the specs, then run `adk-spec plan argon2 --no-explore`
```

A strict change stops after the brief and the specs, so that the design and the tasks are drafted from what you
agreed. Then:

```shell
adk-spec plan argon2                # always writes design.md, then tasks.md
adk-spec approve argon2 --by ana
adk-spec approve argon2 --by ben    # a second, different name; an edit in between voids the first
# implement
adk-spec verify argon2
adk-spec archive argon2
```

On a strict change a warning of the check blocks as an error does, and there is no `--override` for it.

### Changing your mind mid-flight

Ask for the change in words, naming the open change with `--id`:

```shell
adk-spec propose "Also allow backup codes" --id sign-in-with-a-passkey
```

```text
revising  sign-in-with-a-passkey, a standard draft: its files kept where the request does not reach
revised   added REQ-AUTH-005; changed nothing; dropped nothing
```

It keeps the tier, `context.md` and every edit the request does not reach; a requirement that keeps its name keeps
its ID. The tasks are drafted again unless one is ticked. A revised change is a draft again, to be approved again.
Or, on a draft, edit the files yourself and run `adk-spec plan <id>` (add `--replace` to redraft a task list that has
a ticked box); `plan` drafts no task for an approved change, whose new tasks you write in `tasks.md` or revise with
`propose --id`. A verified or archived change is not revised: propose a new one.

### A feature across repositories

When one feature changes an API and the web app that calls it, name the other repositories with the change, from the
repository that holds `.spec/`:

```shell
cd ~/code/shop-api
adk-spec propose "Let users sign in with a passkey." --with ../shop-web --with mobile=../shop-mobile
```

The reading covers them all, `approve` records where the work begins in each, and `verify` runs each repository's
own test command and judges the work in all of them. `--with PATH` names a repository after its folder,
`--with NAME=PATH` names it yourself. Forgot one? On a draft, `adk-spec plan <id> --with ../other` adds it.

### From VS Code with Copilot, or Claude Code

**With nothing to set up**, the skill `init` wrote tells your assistant how to use adk-spec: Copilot (agent mode in
VS Code, the CLI and the cloud agent) and Claude Code read `.claude/skills/adk-spec/SKILL.md` and run `adk-spec` in
the terminal. Ask in the chat, as below; the assistant runs `status`, `propose --no-input`, `plan`, `check`, `verify`
and `validate`, implements the tasks and ticks them, and leaves `approve`, `archive`, every `--override` and every
`--with` to you. Google Antigravity reads skills from `.agents/skills/` alone: where you use it, copy the skill there,
`mkdir -p .agents/skills && cp -R .claude/skills/adk-spec .agents/skills/`. Only there: Copilot reads both folders and
lists a skill found in each twice.
The assistant's terminal must find `adk-spec`: a shell alias is not seen by every assistant's terminal, so install it
as a tool (`uv tool install --editable ~/tools/adk_spec`), or say in the chat how to run it.

**With the MCP server**, `adk-spec-mcp` serves `propose`, `plan`, `check`, `verify`, `status` and `validate` as tools to your coding assistant,
so you can ask for a change in the chat and have the assistant implement it. Approving and archiving stay yours, in a
terminal. The `verify` tool runs only a test command committed in `.spec/config.toml`, and diffs from the approval's
base: an assistant that edits the test command cannot have it run, and `--base` stays a terminal's. The command still
runs your project's own test files, which the assistant may have written: that is what verifying the work means. Run
for a tool, they are not given your provider's key (`GOOGLE_API_KEY`, `GEMINI_API_KEY`).

VS Code, in your project's `.vscode/mcp.json`:

```json
{
  "servers": {
    "adk-spec": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--project", "/path/to/adk_spec", "adk-spec-mcp", "--root", "${workspaceFolder}"]
    }
  }
}
```

Claude Code, from your project's folder:

```shell
claude mcp add adk-spec -- uv run --project /path/to/adk_spec adk-spec-mcp --root "$PWD"
```

(With the installed tool: `"command": "adk-spec-mcp", "args": ["--root", "${workspaceFolder}"]`, and
`claude mcp add adk-spec -- adk-spec-mcp --root "$PWD"`.)

Then, in the chat:

1. "Use adk-spec to propose: let users sign in with a passkey." The tool asks no question: open points come back in
   its output for the assistant to put to you, and it revises the change with your answers.
2. Read the files, then in a terminal: `adk-spec approve <id>`.
3. "Implement `.spec/changes/<id>/tasks.md`, ticking each box, then run adk-spec verify on it."
4. In a terminal: `adk-spec archive <id>`.

A `propose` that reads the code takes minutes. A change that spans other repositories is started in a terminal with
`--with`; the tools then keep them.

### Writing a change by hand

```shell
adk-spec new drop-remember-me --tier lean
```

This makes `.spec/changes/drop-remember-me/` with its state file and no model call. Write `brief.md`, `tasks.md`
and one `specs/<capability>/spec.md` per capability, with whole requirement blocks under `## ADDED Requirements`,
`## MODIFIED Requirements` and `## REMOVED Requirements`, then `adk-spec validate drop-remember-me`, `approve` and
`archive` as above.

### Keeping the specs sound in CI

`adk-spec validate` checks the structure of the living specs and of every open change, calls no model, and exits 1
on an error (`--strict`: on a warning too). In a CI job where adk-spec is installed:

```shell
adk-spec validate --strict
```

It also reads whether an approved change still stands as approved, and a verified one as verified. A change edited
after its approval is a warning, `change.approval-void`, and so is a verified change whose work changed since,
`change.work-drifted`, where its tier owes a verification, so `--strict` fails on both. A change that a revision or
`rebase` sent back to a draft reads as a draft, which the gate does not hold. Work that cannot be compared, in a clone without the history, is a note. In GitHub
Actions, `validate` also writes each finding as an annotation on its line, and a summary on the run's page. A
workflow that checks out the pull request's own commit, with its history:

```yaml
on: pull_request
permissions:
  contents: read  # the gate reads; it writes nothing
jobs:
  specs:
    runs-on: ubuntu-latest
    steps:
      # Pinned by commit, the only reference an action cannot move; the tag it was is beside it.
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          ref: ${{ github.event.pull_request.head.sha }}  # the merge with the target would read as drifted work
          fetch-depth: 0  # the history, to compare the work with what was verified
          persist-credentials: false  # no token is left for the steps after
      - uses: astral-sh/setup-uv@68559e99cc807c1eb7e9238fd43a15bba460eec2 # v10.3.3
      - run: uv tool install <where your team keeps adk-spec>  # it is not on PyPI
      - run: adk-spec validate --strict
```

Archive each change before its pull request merges, as above, and the gate reads only what is still open.

### Where am I?

```shell
adk-spec status
```

```text
Waiting on you
  sign-in-with-a-passkey  standard  approved  implement tasks.md, then run `adk-spec verify sign-in-with-a-passkey`
  argon2                  strict    draft     run `adk-spec approve argon2`

Ready to run
  trailing-space          lean      draft     run `adk-spec plan trailing-space`
```

`--all` lists archived changes too; `--json` prints the list for a script. Where quotes of `.spec/profile.md` are no
longer in the code, `status` says how many on one line, and so does `propose` before it spends anything: run
`adk-spec init --refresh` to read the code again.

## When something goes wrong

| What you see | What to do |
|---|---|
| `no .spec folder at or above …` | You are outside the repository, or it has no `.spec/` yet: `cd` into it, or run `adk-spec init` at its root |
| `… is held by another adk-spec run` | Another command is writing in this repository: wait for it. If none is running, remove the file it names |
| `the brief and the specs are written, and the plan is not: … Run adk-spec plan <id>` | The plan failed after the change was written: run that command to finish it |
| `no change was written: …` | A stage failed before anything was written: read the reason, then run `propose` again |
| `` `<id>` is not approved: the findings above block it`` | Read `reports/check.md`, fix the files, approve again; or `--override "<why>"` (not for a strict change's warnings) |
| `unmet` or `unclear` in `verify` | Implement what is missing, or point the work at the requirement, and verify again |
| `the tests failed` | Fix them and verify again; `verify --override "<why>"` verifies anyway, recorded |
| `archive` stops: the living spec changed under the change | Read the current requirement, update the delta, then `adk-spec rebase <id>` and approve again |
| `CEILING: … token ceiling … is spent` | Raise `[limits] max_tokens` in `.spec/config.toml` |
| `… changed since the approval: run adk-spec approve <id> again` | A file changed after approval: read the change and approve again |

Exit codes: `0` done, `1` a step was refused or found what stops it (a check, a validation, a verification),
`2` a usage or configuration error, before anything is spent, `3` a model or provider failure, `130` interrupted.

## Command reference

Every command runs in the repository it is started in (or `--root <folder>`, given before the command:
`adk-spec --root ../api status`).

| Command | Options | Calls a model |
|---|---|---|
| `init` | `--no-explore` read no code · `--refresh` read the code again, rewrite the profile | yes, unless `--no-explore` |
| `propose "<request>"` | `--id ID` name the change, or revise the open change `ID` · `--tier lean\|standard\|strict` · `--no-input` ask nothing · `--no-explore` read no code · `--with PATH` or `--with NAME=PATH` another repository (repeatable) | yes |
| `approve <id>` | `--by NAME` who approves (default: this account) · `--strict` refuse on a warning too · `--override REASON` approve despite a blocking finding | for a standard or strict change whose check is missing or stale |
| `verify <id>` | `--base REF` the commit the work started from, or `NAME=REF` for another repository · `--override REASON` verify although a requirement is not shown met | yes |
| `archive <id>` | | no |
| `status` | `--all` archived changes too · `--json` | no |
| `plan <id>` | `--replace` redraft although a task is ticked, or a design you edited · `--no-explore` · `--with PATH` | yes |
| `check <id>` | `--no-model` the checks code makes, alone | unless `--no-model` |
| `rebase <id>` | | no |
| `validate [id]` | `--strict` fail on a warning too · `--json` | no |
| `new <id>` | `--tier lean\|standard\|strict` (default: the config's) | no |
| `login` | `--force` log in again | no (GitHub's device flow) |
| `models` | `--json` | no (reads the provider's list) |
| `smoke` | `--check` say whether the arm is ready, send nothing · `--model MODEL` · `--request TEXT` · `--json` | yes, unless `--check` |

`plan`, `check`, `rebase`, `validate` and `new` redo one step by itself; a standard change rarely needs them, and a
strict one, or one with a point left open, is planned with `plan` once you have read it.

## Settings reference

`.spec/config.toml`, in your project, committed. A key adk-spec does not know is refused by name.

```toml
[project]
default_tier = "standard"        # the tier `adk-spec new` gives without --tier; `propose` sizes each request itself

[limits]
max_tokens = 80000               # what one command may spend; unset: no ceiling
keep_runs = 20                   # how many recordings .spec/runs/ keeps

[repository]
exclude = ["vendor/**", "**/*.pem", "config/production.yaml"]   # never read, listed or sent

[verify]
test = ["uv", "run", "pytest", "-q"]   # your test command, as a list of words; run with no shell
timeout = 900                    # seconds; 900 where it is not set
```

`~/tools/adk_spec/.env`, adk-spec's own, never committed: `SPEC_PROVIDER` (`copilot` or `gemini`), `SPEC_MODEL`,
`SPEC_FALLBACK_MODEL`, `SPEC_<STAGE>_MODEL`, and for Gemini `GOOGLE_API_KEY` (or `GOOGLE_GENAI_USE_ENTERPRISE=TRUE`
with `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION`). `.env.example` lists them all.

## What each command does, in depth

- **`propose`** drafts a change from a request. A model writes each part; a gate after each stage checks it and
  asks again at most twice. On the standard tier it puts each point the brief leaves open to you as a question, at
  most three a round and three rounds, each with a suggested answer: a line answers, `=` takes the suggestion, `yes`
  takes a suggestion that is itself a yes and is otherwise your answer, and an empty line leaves the point open, in
  which case approval waits until you settle it in the brief.
  A question that only makes sense once another is answered waits for a later round, and the brief never asks what
  the code or the profile already show: facts are adk-spec's to find, decisions are yours.
  `--no-input` asks nothing, and `--id` names the change. Where you leave a question unanswered, `propose` writes
  the brief and the specs and drafts no plan on a guess: settle the point in the brief, then `adk-spec plan <id>`.
  The same command finishes a plan that did not end well.

  In a git repository `propose` reads the code before it drafts the brief, once: the brief, the specs, the design
  and the tasks are all drafted from what it found, which it writes to `context.md` in the change's folder. See
  "Working in an existing repository" below. `--no-explore` skips it.

  Where `--id` names a change that is open, `propose` revises it by the request, keeping the change's tier and
  everything the request does not reach, your edits included. It says which requirements it added, changed and
  dropped; a requirement that keeps its name keeps its ID. The tasks are drafted again unless one is ticked, and
  `context.md` is kept. A revised change is a draft again, to be approved again. A verified or archived change is
  not revised: propose a new one.

- **`approve`** records who approved, when, and the fingerprint of each file. A later edit voids it; ticking a
  task does not. The name is a recorded claim, not an authentication. On a standard or strict change it first makes
  the check, where none is current: code checks structure and that every requirement has a task, and a model looks for
  what takes a reading, such as two files that contradict each other. Each finding must quote the text it is about,
  and one whose quote is not in the file it names is left out. A blocking finding stops the approval: fix it and
  approve again, or approve with `--override "<your reason>"`, which is recorded. An override answers only a finding
  you were already shown, never one of the same run. Where no model is set up, `adk-spec check <id> --no-model`
  checks by code alone; it never clears what a model's check found blocking, which a model checks again. Where no
  model can make that check again, on a standard change, `--override "<your reason>"` sets the finding aside.

  Where you edited a file adk-spec drafted, `approve` names it once, so that you can write what you corrected in
  `.spec/lessons.md`.

- **`.spec/lessons.md`** is what every draft in the workspace follows: each stage that writes a brief, a delta, a
  design or tasks reads it, within 6,000 characters. Write a correction there in one line, under "From people", and
  edit or delete any line. adk-spec adds a line under "Sent back by a gate" each time a gate sent a draft back and
  the next try put it right, by the stage and the fault, and counts it when it comes back. No model writes it. It
  is shared through git, as the constitution is.

- **`verify`** reads what changed in the repository since the change was approved, as one diff: tracked files, and
  files git does not track yet and does not ignore. A model gives each requirement a verdict, `met`, `unmet` or
  `unclear`, and quotes the lines that show it. Code keeps a `met` only where a quoted line is really in the diff.
  Anything else is `unclear`, so a missing or an invented piece of evidence never reads as a pass. A change is
  verified where every requirement is shown met, or where you say so with `--override "<your reason>"`. `verify`
  needs a git repository and reads it only; `--base <ref>` names another commit to start from.

  Where you name your test command in `.spec/config.toml`, `verify` runs it first, says so, and shows the model and
  the report its result and the end of its output, scrubbed of secret shapes. A run that fails, cannot start or runs
  past its time keeps the change from being verified, whatever the verdicts; `--override` still verifies it, with
  your reason. Only the command you wrote is run, as the list of words you wrote, with no shell to read it; another
  repository of the change runs the command in its own `.spec/config.toml`, where it has one. The tests are not
  given the variables adk-spec's own `.env` set, your provider's key among them.
  A run is judged by its own exit, and whatever it started, a server say, is stopped when it ends, as on Ctrl-C.
  A `verify` stopped from outside, by a closed terminal, a `kill` or a cancelled tool call, stops its tests too.
  Output that names a private key is shown in no part. On Windows a batch file (`npm.cmd`) is refused, since
  cmd.exe reads its words again: name the program it runs. The work is judged as it stands after the tests.

- **`archive`** folds the change's deltas into the living specs. A standard change is archived only once verified.
  If the living spec changed under a requirement the delta touches, the archive stops and writes nothing: read the
  current requirement, update the delta, then run `adk-spec rebase <id>` and approve again.

- **`status`** lists each open change and what to do next with it, in groups: `Waiting on you`, `Ready to run`,
  and with `--all` `Done`. A change whose `change.json` does not read is listed with the reason, and stops no other.

- **`init`** makes `.spec/` with a config, a constitution and the folders for specs and changes. In an existing
  repository it then reads the code, saying first what that costs (up to seven model calls; `--no-explore` skips
  it), and writes `.spec/profile.md`: what is here, how this repository does things, risks and what is unknown,
  each statement with a quote. Rules already true of the code are drafted into the new constitution, each with its
  evidence, for you to keep, edit or delete. Every change's reading starts from the profile. `init --refresh` reads
  the code again and rewrites the profile; it drafts rules only while the constitution is still the template.
  Without a model set up, `init` makes the tree and says how to read the code later. It also writes the Agent Skill
  `.claude/skills/adk-spec/SKILL.md` where the repository has none. `init --refresh` gives it adk-spec's text now
  where it holds a text adk-spec wrote, and keeps one you edited, saying so.

- **`plan`** drafts a change's tasks again, and its design where one is owed, after you edited the brief or the
  specs. Where a task is already ticked it replaces nothing unless you add `--replace`, and it keeps a design you
  wrote or edited, planning from it, unless you add `--replace`. It reads the code first where the change has no
  `context.md`; `--no-explore` skips that.
- **`check`** makes the check `approve` makes, and writes `reports/check.md`, without approving.
- **`rebase`** records anew what a change's deltas are written against, after a living spec moved under them.
- **`validate`** checks the structure of the living specs and of every open change. `--strict` fails on a warning.

### Working in an existing repository

Before `propose` drafts a brief, it reads the code that matters for the request, so that the brief, the specs, the
design and the tasks rest on what is there and not on file names. `plan` reads it for a change that has no
`context.md` yet.

- **How it reads.** A model names what it wants to see: files, folders to list, words to search for. Code reads
  them, and only where git lists the path: nothing git ignores, nothing outside the repository, never a symbolic
  link. A second model call states what the text shows. It may ask to see more, three rounds at most.
- **Installed libraries, offline.** The reading may also open the project's installed libraries, at the versions it
  runs: the repository's Python environment (`.venv` or `venv`) and its `node_modules`. A model is told each
  library's name and version, and names a file as `python:httpx/_client.py` or `node:react/index.js`, only where the
  change depends on how the library behaves. A library is read by the same rules, found in its environment's own
  records, never searched, and nothing leaves your machine but what the model is shown, as with code. A path your
  `exclude` names is left out of them too, and a package that cannot be opened is named, not read. pnpm's linked
  packages are not read.
- **A model checks the reading.** A third call reviews what was kept, statement by statement, and reads no file.
  It leaves out a statement its quote does not bear out, names what is still unknown, and may send the reading one
  round further.
- **What you get.** `context.md` in the change's folder: your answers to the questions asked, what is still
  unknown and what the reading left out first, then four sections: what exists, where the change plugs in,
  conventions to follow, risks; and last what was read, the searches made and folders listed among it. Every
  statement names a file and a line, the line that opens the block it stands in, and quotes the code; a statement
  whose quote is not in that file is left out and counted, as are statements and unknowns past what a reading
  keeps. A run with `--no-explore`, or a reading that keeps nothing, writes no `context.md`, and so keeps no
  answers; nor does a `context.md` you delete to read the code again. The design and the tasks are drafted from
  it, and do not plan on an unknown as if it were known.
- **It is yours.** Edit `context.md` as you would any file of the change. One that is there is kept and read as it
  stands; delete it and the next `adk-spec plan <id>` reads the code again. It is no part of an approval.
- **What it costs.** Up to seven model calls: one to choose, four to state, two to review. Measured live on a
  repository of 268 files it took some 30,000 tokens; far less in a small repository. It is the largest part of
  `propose`. Under `[limits] max_tokens` it spends at most half of what is left, and the rest is kept for the
  brief, the specs and the plan; the `tokens` line shows what it spent.
- **It never stops a plan.** A reading that fails or finds nothing says so in one line, and the plan is drafted
  without it.

To keep paths out of every command, name them in `.spec/config.toml`, read as `.gitignore` reads them. A pattern
with no slash, or a slash at its end alone, such as `*.pem`, `secrets` or `secrets/`, names a file or a folder at
any depth. One with a slash before its end, such as `vendor/**` or `config/secrets`, is a path from the folder that
holds `.spec/`, and so is one that opens with a slash, such as `/build`, which keeps out the top folder alone. A
folder is kept out with all it holds. Letters match in either case. Folders are parted by `/`, never `\`, and a
glob character is matched as itself in brackets: `logs/run[[]1[]].txt`. An excluded path is never read, never listed
among the repository's files, and never part of the diff `verify` sends, so work done only there is no evidence for
`verify`. A `context.md` written before a path was excluded still holds what it quoted from it: delete the file to
read again.

A file that holds a private key is treated as an excluded path is, with nothing to set up: it is never read, and
`verify` leaves its changes out and says so. A key held in a string, as a test holds one, counts too.

A link anywhere under `.spec/` is refused when a command opens the workspace, before it reads or spends anything:
it could lead a read or a removal out of the repository. Replace it with a real file or folder.

### A feature across repositories, in depth

- `--with PATH` names a repository after its folder; `--with NAME=PATH` names it yourself. A path is read from the
  folder you run the command in, as your shell reads it, and recorded in the change; the next change names its own,
  or none. A path that is no repository is refused before anything is spent.
- Every command that reads another repository names it: `with      api from ../api`. A change's file is one a
  teammate may commit, and nothing is read on the strength of it unsaid.
- Name a repository by its own folder. One inside another adk-spec project is refused, so that project's
  exclusions hold, and so is this repository by another spelling. On a shared machine, a repository another account
  owns is not opened.
- The reading covers them all, by the same rules: each one's own git list, its own exclusions where it is an
  adk-spec project too, no file that holds a key. A statement names `api/src/routes.py` for a file of `api`, and
  `context.md` says at what commit each repository was read.
- A repository that is not on this machine is said in one line, and the plan goes on without it.
- `approve` records where the work begins in each, and `verify` judges the work in all of them. Name a repository's
  starting point by hand with `verify <id> --base api=<commit>`, for one named after the change was approved.

### What a command costs, and what it sends

`propose`, `verify`, `plan` and `check` call a model, and `approve` does where a standard or strict change's check is
not current. `[limits] max_tokens` in `.spec/config.toml` caps what one command may spend: once that much is spent no
further call is sent, so a command overshoots by its last call at most, and `propose` asks no question whose answer
it could not use. A ceiling below twice what the reading costs reads less: some 80,000 tokens leaves a `propose` on
a repository of a few hundred files room for all of it.

On a terminal a command says which stage it is on while it works. Every command that calls a model keeps what it
sent and what came back under `.spec/runs/`, which ignores itself for git: one file a model pass, so a `propose`
leaves up to three, its own, its reading of the code and its plan's. The newest 20 are kept, and
`[limits] keep_runs` changes that.

What a model is sent is what the command reads: your request, your specs and the change's files, the names of the
repository's files, the parts of your code the reading asked for, and for `verify` the diff of your working tree.
No key or token of the provider is ever part of it.

Every request is scrubbed of known secret shapes before it is sent or recorded: vendors' keys and tokens, private
key blocks, passwords in URLs, and values a name says are secret. If the scrub fails, nothing is sent. It knows
shapes, not secrets, so it is a net and no guarantee: keep secrets in files git ignores, and name anything else
that must not leave under `[repository] exclude`.

### Watching a run in ADK's own interface

`adk_spec/agent.py` is the shape ADK's interface loads. From inside a repository that holds `.spec/`, run
`uv run --project <this checkout> adk web --no_use_local_storage <this checkout>` and choose `adk_spec`. One message
you type is one request: it is drafted as `propose --no-input` drafts it, stage by stage in the event view, and the
chat ends on the drafts. Nothing is written to `.spec/` and no question is asked. Without `--no_use_local_storage`,
ADK keeps each session, the code a reading showed included, in a `.adk` folder of the checkout. The commands are
the product; this is for watching.

### Notes for each system

- Windows: set `PYTHONUTF8=1` in the user environment. LiteLLM may otherwise read its own files as cp1252.
- Windows on ARM64: set `UV_PYTHON_ARCH=x86_64`. LiteLLM ships no wheel for native ARM64.
- macOS: install the Xcode Command Line Tools while `google-adk` is 2.14.1. `watchdog` 6.0.0 builds from source on
  Python 3.14.
- Behind a company proxy that re-signs HTTPS, adk-spec trusts the operating system's certificate store.

## Developing adk-spec

Everything above is for using adk-spec in your project. This part is for working on adk-spec itself, in its own
folder.

```shell
uv sync --locked
```

The gate, before every commit, one command a line:

```shell
uv run ruff check .
uv run ruff format --check .
uv run pyrefly check
uv run pytest -q
```

The tests run on a fake model and call none. `uv run python -m scripts.measure` builds seven small changes, runs
`check`, `verify` or `plan` on each a few times on the arm your environment names, and reports how often each
planted fault was caught, and whether the reading of the code named the place a change plugs in. It calls a model:
about eight calls a run of the set, and it says the number before the first. `docs/measurements/README.md` says what
each case plants. `uv run python scripts/dump_instructions.py` prints every stage's instruction, to compare before
and after a change to one.

- `docs/full-usage-guide.md`: how adk-spec compares with other spec kits, and the whole lifecycle in one picture.
- `docs/reports/Spec driven framework on Google ADK.md`: the research this project rests on; `docs/research_notes/`
  holds the notes behind it, and `docs/reports/` the owner's own reports.
- `docs/superpowers/plans/`: the implementation plans, and in its `README.md` the roadmap.
- `CLAUDE.md` and `.github/copilot-instructions.md`: the architecture and the rules, for an assistant working here.
