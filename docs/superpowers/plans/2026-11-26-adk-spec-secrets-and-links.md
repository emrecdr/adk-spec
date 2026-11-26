# Secrets and links Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** close the audit's three P0 gaps: credential lines the scrub misses, a key held in a string, links under
`.spec/`.

**Architecture:** two shapes changed and one added in `domain/secrets.py`; `holds_a_key` widened there; one walk of
`.spec` in `workspace/paths.py`, called by `Workspace.find`.

**Tech Stack:** Python 3.14, `re`, `os.walk`, pytest.

**Spec:** `docs/superpowers/specs/2026-11-26-secrets-and-links-design.md`

## Global Constraints

- No model call, command, flag or `change.json` field.
- Ruff complexity 10, lines 120; the four gates and `pyrefly --python-platform windows` green.
- A test that makes a link skips where none can be made (`pytest.skip("no symbolic link can be made here")`).
- Every shape bounded: no run a scan repeats over a long line without a cap.

## Review Focus

1. A long line of options or of `#` (40,000 characters): the scrub stays under a second.
2. Code that names a header in a string, then a long path or identifier on the next line: read, not withheld.
3. A `.spec` with a link deep in a change's `reports/`: refused at open, not after a model call.
4. `init` in a folder whose `.spec` is a dangling link: refused, nothing written through it.
5. A value that is a placeholder after an option, `--token $TOKEN` or `--password <pass>`: left alone.

---

### Task 1: credential lines (S2)

**Files:** Modify `adk_spec/domain/secrets.py` (`_GENERIC`); Test `tests/test_secrets.py`.

- [ ] Write `test_a_credential_line_with_a_comment_or_a_list_mark_is_hidden` (parametrized: `DB_PASSWORD=<v> # prod`,
  `  - POSTGRES_PASSWORD=<v>`, `password: <v>  # rotate`, `set API_TOKEN=<v>`, `+  - SECRET_KEY=<v>`) and
  `test_a_secret_option_of_a_command_is_hidden` (`mysql --password=<v> -h db`, `docker login --token <v>`), and
  `test_an_option_or_a_line_holding_no_value_is_kept` (`--token $TOKEN`, `--password <pass>`, `--max-tokens 4096`,
  `token = get_token(x)  # why`). Run: FAIL on the hidden ones.
- [ ] The unquoted rule takes `(?:-[^\S\n]+)?` after the indent, `set` beside `export|env|arg`, and
  `(?:[^\S\n]+#[^\n]*+)?` before `\s*$`; a new `generic_secret` shape for options. Run: PASS; whole file green.
- [ ] Measure the scrub before and after over the installed packages and this repository; read every new line.

### Task 2: a key held in a string (S1)

**Files:** Modify `adk_spec/domain/secrets.py` (`holds_a_key`); Test `tests/test_secrets.py`.

- [ ] Write `test_a_key_held_in_a_string_is_withheld` (concatenated literals, triple-quoted, a YAML value with `\n`, a
  diff part of the concatenated form) and `test_code_naming_a_header_then_a_long_path_is_read`. Run: FAIL.
- [ ] `holds_a_key` also matches `_KEY_HEADER[^\n]{0,40}?(?:\n[^\n]{0,40}?)?[A-Za-z0-9+/]{40,}`. Run: PASS; suite green.

### Task 3: no link under `.spec/` (S3)

**Files:** Modify `adk_spec/workspace/paths.py` (`refuse_links`), `workspace/layout.py` (`find`, `init`); Test
`tests/test_paths_files.py`, and the three tests that pin a link (`test_lessons.py`, `test_summary.py`,
`test_review.py`).

- [ ] Write `test_a_linked_file_under_spec_is_refused_before_it_is_read` (a linked `profile.md`: `status` exits 2,
  names it), `test_a_linked_runs_folder_is_refused_and_its_target_untouched`, `test_a_linked_spec_is_refused`,
  `test_init_refuses_a_spec_that_is_a_dangling_link`. Run: FAIL.
- [ ] `refuse_links(top: Path) -> None` walks `top` and raises `PathError` at the first link or junction;
  `Workspace.find` calls it; `Workspace.init` refuses `home.is_symlink()`. Pin the three tests to the refusal.
  Run: PASS; suite green.

### Task 4: docs

- [ ] README (what a link under `.spec/` does), the roadmap's row and phase note, CLAUDE.md and
  `.github/copilot-instructions.md` where the rule is named. Gate; commit.
