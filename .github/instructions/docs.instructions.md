---
applyTo: "docs/**"
---

# adk-spec's docs

- The owner's numbered files are theirs and are not edited: `docs/reports/01-…` to `03-…` and
  `docs/research_notes/Spec driven framework on Google ADK/01-…` to `06-…`. The rest of `docs/reports/` and
  `docs/research_notes/` is research the project rests on; treat its claims as claims to check against the code.
- Where things go: designs in `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`, with the owner's decisions
  recorded; plans in `docs/superpowers/plans/`; the roadmap and every phase's state in
  `docs/superpowers/plans/README.md`; live measurements in `docs/measurements/`, listed in its README.
- `docs/full-usage-guide.md` describes the commands as the code has them. A change to a command, a flag or a file
  under `.spec/` updates it, and the README where the README shows it.
- A measurement records what was run, on which model, the calls and tokens it took, and what it showed. A claim about
  a live model is made only from a measurement.
- Write plainly: short sentences, the words a person would use, no more detail than the reader needs.
