---
applyTo: "tests/**"
---

# Writing adk-spec's tests

- A test name is a sentence of the behaviour it pins: `test_a_lock_an_older_adk_spec_wrote_is_left_alone`. Its
  docstring says why the behaviour matters; a fix found by a review says so ("Found by review: ...").
- Never name a helper `test*`: pytest would collect it.
- No test calls a real model or the network. The `fake_provider` fixture (`tests/conftest.py`) answers each stage:
  `answers_when(text, payload)` and `answers_each_time(text, payloads)` match on text in the stage's instruction,
  usually its opening line, and `raises_when` makes a stage fail. A rule no request matched fails the test;
  `answers_if_asked` sets a default for a stage the test may not reach. `on_the_fake(monkeypatch)` puts a model-calling
  command on the fake model. An autouse fixture, `_nothing_from_the_shell`, clears every `SPEC_*` variable and the
  providers' keys, and points the Copilot token folder at an empty one, so no test reads the developer's login.
- The fake model exists only inside the pytest process. A test that runs adk-spec in a subprocess gets no fake model:
  run only offline commands there (`status`, `validate`, `--help`), or build a model without calling it, as
  `tests/test_models.py` does with `SPEC_MODEL='gemini-test'`.
- `seeded(tmp_path)` makes a workspace with a living spec and one open change, `passkeys`; use it rather than building
  `.spec/` by hand.
- Test the behaviour through the public seam (the command, the tool call, the stage's run) rather than a private
  helper, where that is not much harder.
- A test that depends on the system says so with `pytest.mark.skipif(os.name == "nt", reason=...)`, and the reason is
  a sentence. Windows paths, line endings and process stopping differ: CI runs the suite on Windows too.
