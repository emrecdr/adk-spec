# Plans: where the project stands

One row a phase. A phase is one plan in this folder: it is built test first, then cleaned up (`/simplify`), reviewed
(`/code-review`), committed and merged to `main`. Updated on 22 November 2026.

| # | Phase | Plan file | State |
|---|---|---|---|
| 1 | Foundation: the `.spec/` tree, parsers, validator, approval, archive | `2026-11-21-adk-spec-foundation.md` | Done |
| 2 | Model stages: `propose` and `plan` | `2026-11-22-adk-spec-model-stages.md` | Done, confirmed live on Copilot |
| 3 | `check` and `verify`, recordings, the measurement script | `2026-11-21-adk-spec-check-and-verify.md` | Done, measured live twice. Two steps are the owner's: the Gemini arm, and a run on Windows |
| 4 | A brief's open points asked without a second model call | `2026-11-21-adk-spec-questions-in-code.md` | Tasks 1 to 3 done and merged. Task 4, the live proof, waits for the owner's go-ahead |
| 5 | Brownfield, part 1: context for one feature, read from the repository's code | not written yet | In design. The design will be `../specs/2026-11-22-brownfield-feature-context-design.md`; the plan follows its approval |
| 6 | Brownfield, part 2: a one-time baseline of the repository, and which folders belong to which capability | not written yet | Not started |

## The plan being followed now

Phase 5 is next and has no plan file yet. Until it has one, the last plan worked from is
`2026-11-21-adk-spec-questions-in-code.md`.

## Named for later, not planned

In the order of the research report (`reports/Spec driven framework on Google ADK.md`, its migration table) and of
plan 3's "What this plan leaves":

- Tests as evidence for `verify`: run the project's own tests and map results to requirements before a model judges.
- Triage by rules, with a model asked only where the rules do not decide.
- The contradiction pass of `check` moved to code, where a measurement shows it can be.
- A lessons file a workspace keeps between runs.
- The `strict` tier, which is read as `standard` today.

## The owner's, outside any phase

- A smoke run on the Gemini arm. It needs a `GOOGLE_API_KEY`.
- The gate on a Windows machine. The CI workflow has a Windows job, and the repository has no remote.
- Every live model call: each needs a go-ahead in so many words.
