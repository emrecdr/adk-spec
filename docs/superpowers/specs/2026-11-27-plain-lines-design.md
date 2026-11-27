# Plain lines: phase 26

Designed on 27 November 2026 from the audit of 25 November (`docs/reports/2026-11-25-codebase-audit.md`: U9, U10,
U13 and C6) and the outside audit of `171f1c4` (H7-PERF). The owner said "finish those next remaining work, without
going into loop", then "do simplify once, code-review once, only after you finish all remaining tasks": phase 26 and
phase 27 are built first, then reviewed once together. Each item was checked again in the code before this design.

## Goals

1. **U9: one read line.** After a plan, `read      brief.md (25 lines, 1 assumption), then reports/review.md (1
   added)`, in place of a `read … first` line and a `review` line. The `plan` a stop names drops `--no-explore` where
   the change's `context.md` makes `plan` skip the reading anyway.
2. **U10: one label column.** `approved  x by ana: 3 files recorded`; `archived  x: folded into auth`, then `next
   commit .spec/ with the code`; `new` says `made      …` and ends on the `next` line `status` gives; `validate`
   counts its notes where it prints some: `0 errors, 0 warnings, 2 notes`.
3. **U13: task progress and a brief to fill.** `status` shows the tasks ticked of a change past its draft, `3/7`, in a
   column only where a row has one. `new` writes `brief.md` with its sections in order, each part to write a
   `[NEEDS CLARIFICATION: …]` that `validate` reports.
4. **C6: a suspect requirement names its next step.** Its note says to run `adk-spec propose "keep REQ-X: its
   evidence is gone"` and verify that change, or to delete its lines once that is reviewed.
5. **H7: the cap before the reading.** `propose` checks the living specs triage named against what a stage is given
   before the code reading spends, and stops as the deltas stage would.

## Left out

- **U11, bare commands on the terminal.** It touches 40 source lines, 73 test assertions and the README's examples.
  The hazard is a paste that includes the backticks, which a person rarely selects. The backticks also mark where a
  command ends inside a sentence, and the reader of the MCP tools' output takes them as code.
- **A `tasks.md` skeleton.** The grammar names its shape on any error, and a placeholder task would need
  requirement IDs that do not exist yet; `plan` drafts the list.

## Calls made in the design (the builder's)

- **The tasks column** counts a list that reads; a list off its grammar shows none, as `validate` says why.
- **H7 uses triage's capabilities**, which the brief starts from. A brief that names fewer could have fit where this
  check stops it: rare, as the brief is given triage's list to start from.
- **The brief skeleton** is rendered by `render_brief`, so it reads back as written.
