# Context kept and said: phase 18

Designed on 25 November 2026, from the owner's question whether context is lost between the layers and between
Python and the models. Two read-only researchers mapped every stage's inputs, caps and losses, and the code reading's
aim and limits (findings cited to file and line in the session). The owner chose, as recommended, a first step that
calls no model: keep what is lost in silence, and say the reading's cuts. A second step, aiming the reading with triage's
capabilities, a reading of the repository's guidance files, and the constitution for the deltas stage, changes what
models are told and waits for a live measurement on the owner's go-ahead.

## Intent

Python decides what is read and what is kept, and every model claim stands only where code finds its quote. But some
context is dropped in silence: the person's answers live only in the run, the reading cuts statements, unknowns and
requests without saying so, a folded file tree hides the repository's top files, and the end of a long test output is
given to `verify` with no mark of the cut. This phase keeps the answers and says each cut, with no model call.

## Goals

1. **The person's answers kept.** `context.md` holds each question `propose` asked and its answer, near its top, so
   the stages after the brief (deltas, design, tasks) read the person's own words, not only the brief's.
2. **Every cut of the reading said.** Statements past the 40 kept and unknowns past 8 are counted under what was
   left out; the searches and folder listings made are said under what was read. (Requests left when the budget ran
   out were counted, then taken out: two reviews found the count wrong, a request read later or asked twice; an exact
   one needs each request followed across rounds. The roadmap keeps it.)
3. **What matters first in `context.md`.** The unknowns and what was left out stand above the statements, so the cut
   a stage is given at 20,000 characters takes the statements' tail first.
4. **The top files named.** A folded tree lists the files at the repository's top by name, so a stage sees
   `README.md`, `pyproject.toml` or `CLAUDE.md` there.
5. **A cut test output marked.** `verify` is told where the output of a test run was cut.

## Non-goals

- No model call, command, flag or `change.json` field; nothing a stage is told changes but the inputs above.
- The step that changes what models are told (aiming the reading, guidance files, the constitution for deltas):
  measured first.
- Answers of a run with `--no-explore`, or of a revision: no `context.md` is written then, and writing one for the
  answers alone would keep `plan` from reading the code. Said in the docs.

## Calls made in the design (the builder's)

- **Where the answers go.** A `## The person's answers` section after the file's first lines, one `- <question> ->
  <answer>` line each, as the brief stage is given them; written when the change's `context.md` is.
- **Unknowns of two reviews.** The last review's stand, as it read what the first asked for; those past 8 are
  counted. Adding the first's was built and taken out: the second review is not shown them, so it could not withdraw
  one it had answered (code review). Showing it them is a change to what a model is told: step 2.
- **The top files.** Up to 30 by name on one line after the header, then a count of the rest.
- **The test output's mark.** One line before the kept end, saying its start is not shown (no count: the byte
  window a run's output is held in drops a start of unknown length too).

## Tests

One per goal: answers in `context.md` after a propose that asked; each cut said (statements past the budget, unknowns
past theirs, a search and a folder in what was
read); the unknowns above the statements in the file; a folded tree naming the top files; a cut test output marked.
