# Plans and roadmap: where the project stands

Updated on 22 November 2026.

A **phase** is one plan in this folder. It is built test first, then cleaned up (`/simplify`), reviewed
(`/code-review`), committed and merged to `main`.

A detailed plan is written for one phase at a time, just before it is built: each phase so far has changed the
next one. A phase that is not yet planned has an entry in the roadmap below, and gets its own design and plan when
its turn comes.

## Done and in progress

| # | Phase | Plan file | State |
|---|---|---|---|
| 1 | Foundation: the `.spec/` tree, parsers, validator, approval, archive | `2026-11-21-adk-spec-foundation.md` | Done |
| 2 | Model stages: `propose` and `plan` | `2026-11-22-adk-spec-model-stages.md` | Done, confirmed live on Copilot |
| 3 | `check` and `verify`, recordings, the measurement script | `2026-11-21-adk-spec-check-and-verify.md` | Done, measured live twice. Two steps are the owner's: the Gemini arm, and a run on Windows |
| 4 | A brief's open points asked without a second model call | `2026-11-21-adk-spec-questions-in-code.md` | Tasks 1 to 3 done and merged. Task 4, the live proof, waits for the owner's go-ahead |
| 5 | Brownfield, part 1: context for one feature | not written yet | **In design.** Design: `../specs/2026-11-22-brownfield-feature-context-design.md`, waiting for the owner's approval. The plan is written once it is approved |

## The plan being followed now

Phase 5 has a design and no plan yet. Until it has one, the last plan worked from is
`2026-11-21-adk-spec-questions-in-code.md`.

## Roadmap: the phases to come

The order is a recommendation. The owner chose phases 5 and 6 and their order on 22 November 2026; the rest follow
the research report (`reports/Spec driven framework on Google ADK.md`, its migration table) and plan 3's "What this
plan leaves".

### Phase 5. Brownfield, part 1: context for one feature

- **Goal:** a design and a task list for a new feature rest on what the repository's code is, not on file names.
- **Builds:** `adk-spec explore <id>`, which reads the code that matters for one change and writes `context.md`,
  every statement with a quoted line that code checked; `plan` reading it; reading limited to files git tracks,
  with a person's own exclusions; known secret shapes scrubbed from every model request of every command.
- **Depends on:** nothing unbuilt.
- **Size:** about seven tasks. The last holds the live steps.
- **Open:** the owner's approval of the design.

### Phase 6. Brownfield, part 2: a baseline of the repository

- **Goal:** adk-spec knows a repository before the first change: its stack, its structure, its conventions, and
  which folders belong to which capability.
- **Builds:** a one-time survey that writes a repository profile under `.spec/`; a capability-to-folder map; a
  constitution drafted from what is already true of the code, for the person to accept; `explore` choosing its
  first files from the map.
- **Depends on:** phase 5's reading, grounding and scrubbing.
- **Size:** medium to large.
- **To decide then:** whether `propose` explores before it writes the brief, which phase 5's measurement informs;
  and whether living specs are drafted from existing code, which is the riskiest piece and stays out until asked
  for.

### Phase 7. Tests as evidence for `verify`

- **Goal:** a verdict rests on the project's own tests as well as on the diff.
- **Builds:** running a test command the person configures, mapping its results to requirement IDs, and showing
  them to the model that judges.
- **Depends on:** nothing unbuilt.
- **Size:** large. It is the first phase in which adk-spec runs a command of the project's, so it is
  security-sensitive, most of all on Windows.

### Phase 8. Triage by rules

- **Goal:** most requests are sized (lean, standard, none) with no model call.
- **Builds:** rules on measurable inputs, with the model asked only where they do not decide.
- **Size:** small.

### Phase 9. The contradiction pass of `check` in code

- **Goal:** what code can decide about two files that disagree is decided by code.
- **Depends on:** more measurement. The two so far show this pass is the least steady: 2 of 3, then 1 of 3.
- **Size:** medium.

### Phase 10. A lessons file

- **Goal:** a workspace keeps what a gate sent back and what a person corrected, and later drafts read it.
- **Size:** medium.

### Phase 11. The `strict` tier

- **Goal:** the third level of ceremony, which is read as `standard` today.
- **Size:** medium.

## The owner's, outside any phase

- A smoke run on the Gemini arm. It needs a `GOOGLE_API_KEY`.
- The gate on a Windows machine. The CI workflow has a Windows job, and the repository has no remote.
- Every live model call: each needs a go-ahead in so many words.
