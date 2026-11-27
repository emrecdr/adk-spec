# Small hardening: phase 24, and the audit's P2 triaged

Designed on 27 November 2026 from the audit of 25 November (`docs/reports/2026-11-25-codebase-audit.md`), its P2. The
owner asked for the P2 items. Each was checked again in the code; this phase builds the hardening worth its cost, and
the triage below says what comes next and what is left, and why.

## Goals

1. **S7: the README's CI example as safe as this repository's own.** Actions pinned by commit, `permissions:
   contents: read`, `persist-credentials: false`, as `.github/workflows/ci.yml` does.
2. **S8: `login` loads LiteLLM in production mode.** The two settings `_litellm()` sets before LiteLLM's import, so it
   reads no `.env` and fetches no price list, are one function both call.
3. **S9: a job-summary cell holds no Markdown of its own.** A folder name or a finding's text from a pull request
   renders as text, not as a link or an image.
4. **H2: a diff past what is read is refused before it is built.** Files git neither tracks nor ignores, past four
   times what a stage is given (800,000 bytes), are refused by their size, before each is diffed and held whole.
5. **H3: an evidence check reads each file once.** A file's text, and its scrubbed text, are kept by its path and
   stamp for the command; a file past the reading's own cap (2,000,000 bytes) is not read, its quote unknown.

## The rest of P2

| Item | Call | Why |
|---|---|---|
| U9, U10, U11, U13 | Next: a phase of plain lines | Printed lines; one phase, one review |
| A4, A5, A6, A8 | Next: a phase of small refactors | No behaviour; cheap |
| C6 | Next, with the plain lines | A suspect requirement's next step names `propose` |
| C4 | Later | Structured MCP results: a new output contract to design |
| S5 | Later | `context.md` as material: changes a file format and the skill |
| H4 | Left | Fixed model deadlines: measure first, which needs live calls |
| H5 | Left | A lock after a reboot: no boot time on every system without a dependency; the refusal names the file |
| S6 | Left | Provider keys in test runs: the person's own test runs hold them too, and dropping them breaks a project that uses the same provider |
| A3 | Left | Splitting `cli.py`: decided before (roadmap) |
| A7 | Left | Provenance comments: a style for new code, no sweep |
| C5 | Waits | Live calls: the owner's go-ahead |
| C7 | Waits | MCP elicitation: no client support confirmed |

## Calls made in the design (the builder's)

- **H3 keeps no grep cap.** Caching the files read removes most of the repeated work; a cap would need a budget
  threaded through the checks for a scale not yet seen.
- **H2's refusal** is a `GitError`, which `status` already reads as work that cannot be compared, and `verify` says.
