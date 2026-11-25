# Freshness and proof notes: the phase after phase 16

Designed on 25 November 2026, from an outside product-discovery report of twelve options, each checked against the
code, the roadmap's decisions and the tools it cites by four independent verifiers. The owner chose, as recommended,
the three parts that survived as worth building now, as one small phase: the profile checked against the code
(option 6, reduced), the proofs a verification's work removed (option 1, its reverse half), and the `[P]` mark held
to its rule (option 5, reduced). The rest of the report was skipped or left to be measured first; the reasons are in
the roadmap.

## Intent

adk-spec keeps three statements about the code that code can check and does not: `profile.md`, which every drafting
stage reads, quotes lines that a later edit may have removed; a living requirement's evidence can be removed by a
change that never names it, and `verify` judges that change without saying so; and the tasks stage marks a task
`[P]`, "it touches other files than its neighbours", without code reading its files. This phase checks each with
code, and says what it finds in one line, where the person is looking.

## Goals

1. **The profile checked against the code.** `status`, and `propose` before it spends anything, say in one line
   how many of the profile's quotes are no longer in the code, and that `init --refresh` reads it again.
2. **The proofs the work removed.** `verify` says in one `note` line which living requirements, untouched by the
   change, lost every line that proved them in files the work changed.
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
- A note that blocks: neither line changes an exit code or a step.

## Decisions (the owner's)

- The three parts, in this phase, as recommended (25 November 2026). The report's other options: skipped, or
  measured first on a go-ahead (the constitution in `verify`, check lenses, the tier raised after the reading,
  evidence given to the reading, bugfix guidance).

## Calls made in the design (each the builder's, to check while reading)

- **One test of a quote, shared.** Whether a quote holds is `workspace/evidence.py`'s rule, in its file or moved to
  another of its repository: the profile's check calls the same function, split out of `holds` so that a profile
  statement needs no `Proof`.
- **The profile read leniently.** An entry is a `` - `path:line` `` line and the `  > ` line under it, as
  `render_context` writes them; anything else in the file, a person's edit, is passed over. A path with a library's
  scheme is not looked for; the line number is not used, as a moved quote holds.
- **Where the profile line shows.** `status` (text only, as the suspect lines are) and the start of `propose`, the
  one command that sends the profile to a model. Not `plan`: it reads `context.md`, which `propose` wrote.
- **What the `verify` note names.** A living requirement the change neither adds, modifies nor removes, all of whose
  evidence is gone, with an evidence file the work's diff changed. Another repository's file is matched by the name
  the change gives it. At most three IDs, then a count, as the unmet step does.
- **Only what the diff touched is looked at.** The living evidence files are read, and a requirement is checked
  only where one of its evidence files is among the diff's paths; then every line of it is, as gone means all of
  them. No whole-repository scan on each `verify` (a refinement from the report's author, 25 November 2026).
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
- `verify` names a requirement whose only evidence file the work deleted a line of; not one the change modifies;
  not one whose evidence holds; not one whose evidence file the work did not touch; three IDs then a count.
- A drafted `[P]` task sharing a file with its neighbour loses the mark; one sharing a folder does; one naming no
  file does; one apart from both neighbours keeps it.
