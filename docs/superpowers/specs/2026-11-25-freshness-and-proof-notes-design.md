# Freshness and proof notes: the phase after phase 16

Designed on 25 November 2026, from an outside product-discovery report of twelve options, each checked against the
code, the roadmap's decisions and the tools it cites by four independent verifiers. The owner chose, as recommended,
the three parts that survived as worth building now, as one small phase: the profile checked against the code
(option 6, reduced), the proofs a verification's work removed (option 1, its reverse half), and the `[P]` mark held
to its rule (option 5, reduced). The rest of the report was skipped or left to be measured first; the reasons are in
the roadmap.

## Intent

adk-spec keeps statements about the code that code can check and does not: `profile.md`, which every drafting stage
reads, quotes lines that a later edit may have removed; and the tasks stage marks a task `[P]`, "it touches other
files than its neighbours", without code reading its files. This phase checks both with code, and says what it
finds in one line, where the person is looking. (A third, the proofs a verification's work removed, was taken out:
Goal 2.)

## Goals

1. **The profile checked against the code.** `status`, and `propose` before it spends anything, say in one line
   how many of the profile's quotes are no longer in the code, and that `init --refresh` reads it again.
2. **The proofs the work removed** (built, then taken out on 25 November 2026). `verify` was to say in one `note`
   line which living requirements, untouched by the change, lost every line that proved them in files the work
   changed. Three code reviews in turn found it missed or misnamed requirements: by path (code moved before the
   work, a repository's folder spelled two ways), and by text (a two-line quote changed in one line, a line another
   repository removed). Exact attribution needs each proof read at the base commit; `status` and `validate` already
   flag every requirement whose evidence is gone. The owner may take it up again (the roadmap).
3. **`[P]` as the planner is told it.** A drafted task keeps `[P]` only where it names its files and none of them
   is a file of the task before or after it.

## Non-goals

- No model call, no new command, flag, or `change.json` field, no new file.
- No change to `validate`: a stale profile is no reason to stop a merge, and the proofs a change removed are
  already its `spec.evidence-gone` notes there.
- No check of `context.md`: it lives for one change, and only `plan` reads it again.
- Nothing dispatches on `[P]`: the skill and the server still tell an assistant to work through `tasks.md` in order.

## Anti-goals

- A line that cries wolf: a quote that moved to another file holds, as evidence's does; a quote of an installed
  library (`python:`, `node:`) is not looked for; a profile that does not read says nothing.
- A note that blocks: the profile's line changes no exit code or step.

## Decisions (the owner's)

- The three parts, in this phase, as recommended (25 November 2026). The report's other options: skipped, or
  measured first on a go-ahead (the constitution in `verify`, check lenses, the tier raised after the reading,
  evidence given to the reading, bugfix guidance).

## The report's other options, and why not now

- **Specs drafted from existing code** (2): deferred by the owner in phase 8; evidence is kept only from lines a
  verification's diff adds, and a baseline has none.
- **MCP elicitation, resources, prompts, `.agents/skills/`** (4): against recorded decisions (tools ask no question;
  Claude Code reads `.claude/skills/` alone, and Copilot that too); the tools already send `structuredContent`.
- **Execution waves, cross-change file collisions** (5, the rest): waves need task dependencies, set aside; the
  files are the model's guess, and the requirement overlap already shows.
- **Lesson capture at `approve`** (6b): an interactive prompt and a diff on screen in a command that asks nothing.
- **A request read from stdin, a size check before the reading** (7): optional, kept for later.
- **`status --runs`, `smoke --replay`** (8): the tokens line exists; a recording keeps no files to replay against.
- **Per-task packets** (9): a new parser for `context.md` for an unmeasured saving.
- **`--dry-run`, `--max-calls`** (11a): the token ceiling already holds every call, before it is made.
- **A "no test file changed" line** (10b): optional; which files are tests is a guess from their paths.
- **`--bugfix`, a repro-test proof** (12): a new flag; a diff cannot show a test failed before the fix.

## Calls made in the design (each the builder's, to check while reading)

- **One test of a quote, shared.** Whether a quote holds is `workspace/evidence.py`'s rule, in its file or moved to
  another of its repository: the profile's check calls the same function, split out of `holds` so that a profile
  statement needs no `Proof`.
- **The profile read leniently.** An entry is a `` - `path:line` `` line and the `  > ` line under it, as
  `render_context` writes them; anything else in the file, a person's edit, is passed over. A path with a library's
  scheme is not looked for; the line number is not used, as a moved quote holds.
- **Where the profile line shows.** `status` (text only, as the suspect lines are) and the start of `propose`, the
  one command that sends the profile to a model. Not `plan`: it reads `context.md`, which `propose` wrote.
- **A quote that cannot be looked for is not gone.** Not in its file, and git refusing the search for it elsewhere,
  outside a repository say, it is unknown: counted neither gone nor checked, as evidence's `None` is.
- **`[P]`'s neighbours.** The tasks before and after it in its group, whatever their own mark; two files overlap
  where they are one path, or one is under the other as a folder. So a colliding pair loses the mark on both: two
  agents never run on one file. A path is read as `remaining.md` reads a task's file (backticks, `./`, a trailing
  `/` and backslashes taken off), from one function both use.
- **A dropped `[P]` is not said.** The tasks file is the model's draft, held to its own rule by code, as `convert`
  holds the rest of it.

## Tests

- A profile whose quotes all hold says nothing; one quote gone says "1 of N"; a moved quote holds; a library path is
  not counted; a profile that will not read, or is not there, says nothing; lines a person wrote off the format are
  passed over; outside a git repository a quote not in its file is not counted; `propose` says it before its first
  call.
- A drafted `[P]` task sharing a file with its neighbour loses the mark; one sharing a folder does; one naming no
  file does; one apart from both neighbours keeps it.
