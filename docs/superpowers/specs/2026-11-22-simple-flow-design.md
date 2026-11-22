# The simple flow: four everyday commands

Design for the next phase of adk-spec. Written on 22 November 2026. Status: waiting for the owner's approval.

## Intent, and why

The owner's golden rule (22 November 2026): "i do not wanna deal with too many sub commands, i do not wanna
overwhelm users with too much details, our proceesses, flows should be simple. consider openspec & spec dev kit".
And, on how far to go: "it shoudn't have to be the simplest one but must be easy to understand, shouldn't be one
of the complex ones".

Today one standard change takes six commands (`propose`, `plan`, `check`, `approve`, `verify`, `archive`) out of
fourteen subcommands. Two of the six exist only because the tool does its work in separate steps: a person decides
nothing between `propose` and `plan`, and runs `check` only because `approve` asks for it.

## The rule

**A command exists where a person decides something. The tool's own work happens inside it.**

## The flow

| Command | The question it answers | What happens inside |
|---|---|---|
| `adk-spec propose "..."` | What do we want to build? | Sizes the request, asks its questions, writes the brief, the specs, the design where one is owed, and the tasks |
| `adk-spec approve <id>` | Do I agree with this plan? | Records what the change is written against, runs the check where none is current, stops on anything blocking, then records the approval |
| `adk-spec verify <id>` | Is it built? | Judges the work against each requirement. Run as often as wanted while implementing |
| `adk-spec archive <id>` | Make it the record? | Folds the change into the living specs |

Once for a repository: `adk-spec init`. At any time: `adk-spec status`, which says what to do next.

A lean change needs three of the four: it owes no verification, as today.

## What the research found

Four sets of notes are in `research_notes/Simple command flows in spec tools/`.

| Finding | Where it comes from | What it decides here |
|---|---|---|
| OpenSpec cut its default from 10 commands to 4 because "new users feel overwhelmed". Its everyday flow is propose, apply, archive | `openspec_command_flow.md` | A small everyday set is the proven shape |
| OpenSpec's `propose` writes every planning file in one pass, asks only what would change scope, and stops for one review | `openspec_command_flow.md` | `propose` runs through to the tasks |
| Kiro added a one-pass mode in May 2026: the step-by-step approvals "can feel like more process than the problem requires". BMAD collapsed to one build command | `simple_versus_heavy_flows.md` | The same |
| Spec Kit grew from 3 commands to 10 and merged nothing. Its own newsletters name "review overload, ceremony for small tasks, and verbose markdown output" as the most-cited concerns | `speckit_command_flow.md` | Do not grow; keep what is generated short |
| What users call heavy is, in order: how much they must read, fixed ceremony for small changes, repeated approvals, waiting, and not knowing what to run next. The number of commands is almost never named | `simple_versus_heavy_flows.md` | Fewer commands is right and is not enough: also short files, one approval, progress while waiting, and a `next` line every time |
| People approve 93 to 97 percent of prompts without real review | `simple_versus_heavy_flows.md` | One approval that means something, and no second one |
| Review matters most early and short, on intent and design. No source singles out the task list | `simple_versus_heavy_flows.md` | `propose` ends by naming what to read first |
| A separate step that only advises gets skipped: OpenSpec's `verify` cannot block its archive, and its users forget to archive | `openspec_command_flow.md` | `verify` stays a gate, as it is, and `status` keeps a verified change in view |
| In our code all the merges are possible with no new stored state. A check run inside `propose` would be wasted, since any edit voids it. An archive that verifies would rewrite the specs in the step that first shows the verdicts | `adk_spec_current_flow.md` | The check goes inside `approve`. `verify` and `archive` stay apart |

## Approaches considered

| Approach | Commands for a standard change | Why it was or was not chosen |
|---|---|---|
| Keep six | 6 | A person runs two commands that decide nothing. It is the side of the range Spec Kit's users complain about |
| **Four, one a decision** (chosen) | 4 | Each command is a question a person can name. Every merge is safe in the code |
| Three: `archive` verifies first | 3 | The fewest, and harder to follow: the specs are rewritten in the same step that first shows the verdicts, and `verify` can no longer be repeated cheaply while implementing. The owner asked for easy to understand, not for the fewest |

## What changes

- **`propose`** goes on, once the specs pass their gate, to the design where one is owed and to the tasks, in the
  same command, under one token ceiling. If that second part fails, the change stands as a draft and the command
  says that `adk-spec plan <id>` finishes it. A point the person left open does not stop it: the point is listed
  under what needs them, and holds the approval, as today.
- **`approve`** records the base of each requirement the change touches where none is recorded, so `rebase` is
  needed only after a living spec has moved. On a standard change it runs the check where none is current. Anything
  blocking stops it, with the findings shown. `--override` works only on a check a person has already been shown,
  never on one made in the same run.
- **`verify` and `archive`** do what they do today. Each ends on a `next` line, as `approve` and `archive` do not
  yet.
- **The help** shows the everyday commands first. `plan`, `check`, `rebase`, `validate` and `new` stand under a
  second heading, "to redo one step", and `smoke`, `models` and `login` under a third, "setup".
- **What a command prints** is three things: what it wrote, what needs the person, and the next command. `propose`
  also names what to read first, the brief and the design, with their lengths.
- **While a command runs** it says which stage it is on, one line a stage, so a minute of work is not a minute of
  silence.

## What does not change

- Every command that exists keeps working, with its flags. A person who likes the six steps can keep them.
- No rule of the lifecycle changes: a standard change is still checked before it is approved and verified before
  it is archived. Only who types the command changes.
- The files of a change, their grammar and the state file.

## What the flow already covers, with no new command

The most-voted requests in both parent projects are for changing a spec after the fact and for a fix loop. Here:

- **Changing a change:** edit its files. The approval is void, and `approve` checks again.
- **Redrafting after an edit of the brief:** `adk-spec plan <id> --replace`.
- **A fix loop:** implement, `verify`, implement, `verify`.

## Risks

- **About forty assertions pin the present steps:** some thirty on a `next` phrase, some twelve on a refusal
  between two steps. They are rewritten deliberately, one by one.
- **`approve` now needs a model** on a standard change whose check is not current. Where no provider is set up, it
  says so, and `check --no-model` remains.
- **The check is the least steady stage measured.** Putting it inside `approve` hides no finding: what blocks still
  stops the approval, and the report is written as today.

## Decided by the builder, for the owner to check

1. An open point a person left unanswered does not stop `propose` from writing the plan.
2. No flag is added to stop `propose` early. `--no-input` stays.
3. Progress lines go to the error stream, so a command's output stays what a script can read.
4. No length limit is put on what a stage writes in this phase. The lengths are shown and measured first.

## How it is proven

- Offline: the suite, on the fake model, with a standard and a lean change taken through the new flow from request
  to archive, and each old command still passing alone.
- Live, on the owner's go-ahead: one standard change through the four commands, with its tokens, its seconds and
  the number of lines a person has to read.

## What follows from it

Brownfield reading (the next phase) goes inside `propose`, before the brief, with no command of its own. The
repository baseline (the phase after) goes inside `init`. OpenSpec's `propose` has read the relevant code before
drafting since its version 1.12.0; neither parent project builds a baseline, and a code-first one is an open
request in OpenSpec's tracker.
