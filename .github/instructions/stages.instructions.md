---
applyTo: "adk_spec/orchestration/**"
---

# Stages, gates and the model arms

- Each drafting stage is one schema-bound `LlmAgent` built by `stage()` in `stages/__init__.py`, with an instruction
  built by `instruction(opening, guide, *sections)`: the opening line, `## What to write`, the guide, each section,
  then `RETRY` (what the last gate found) just before `ENDING`. Keep the retry findings last but the ending, so a retry
  leaves the start of the prompt as it was for a provider to reuse.
- The tests' fake model picks a stage's answer by text in its instruction, usually the opening line. Rewording an
  opening breaks the tests that match on it: change them together. `uv run python scripts/dump_instructions.py` prints
  every instruction as a model is sent it.
- A stage's answer is read back with `read_back(state, key, schema)`; the gate in `gate.py` checks it in code, and
  its findings go back to the stage, at most three tries. Every gate sentence is `coded(code, sentence)`.
- What a stage is told goes through `workspace/context.py`, each input capped, and is scrubbed of secrets. The
  `Scrub` plugin on every app fails closed.
- `models.py` builds both arms: Copilot through LiteLLM, Gemini through ADK's registry, each under a deadline. Call
  `_litellm()` before LiteLLM is imported, as `catalog.py` does: it takes up the system's certificates first, and
  LiteLLM keeps the certificate context it makes on import. Import LiteLLM inside functions, never at module top.
- Nothing here may run a real model in a test. Do not run `propose`, `plan`, `check`, `verify`, `smoke` or
  `scripts.measure` to try a change: each sends real requests on the owner's account.
