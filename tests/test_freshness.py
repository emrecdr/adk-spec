"""Phase 17: the profile every drafting stage reads, checked against the code it quotes, by code alone."""

from __future__ import annotations

import pytest
from conftest import on_the_fake, repository, run, seeded

from adk_spec.domain.context_md import quoted_statements, render_context
from adk_spec.domain.model import Statement
from adk_spec.workspace.evidence import profile_gone
from adk_spec.workspace.files import write_text

#: A profile as `init` writes one, with a line a person added, and a statement on an installed library's file.
PROFILE = """\
# Profile

Read on 2026-11-20 of commit abc.

## Conventions

- `src/app.py:2` Sign-in goes through the password check.
  > return password_check(user)
- `src/old.py:1` The session helper.
  in: def start_session(user):
  > def start_session(user):
- `python:httpx/_client.py:10` The HTTP client.
  > class Client(BaseClient):

A note of the person's own, and `src/app.py:9` mentioned in prose.
- A bullet of theirs.
"""
FILES = {
    "src/app.py": "def login(user):\n    return password_check(user)\n",
    "src/old.py": "def start_session(user):\n    return {}\n",
}
LINE = "profile: "
STATEMENT = Statement(
    kind="convention",
    path="src/old.py",
    line=1,
    quote="def start_session(user):",
    note="The session helper.",
    within="def start_session(user):",
)


@pytest.fixture(autouse=True)
def _fake_arm(monkeypatch) -> None:
    on_the_fake(monkeypatch)


def profiled(root, files=FILES, profile=PROFILE):
    """A workspace in a repository of `files`, with `profile` as its `.spec/profile.md`."""
    ws = seeded(root)
    repository(root, files)
    write_text(root / ".spec/profile.md", profile)
    return ws


def test_the_profile_is_read_as_its_statements_and_their_quotes() -> None:
    written = render_context("Profile", at="2026-11-20", commit="abc", statements=[STATEMENT], read=[])
    assert quoted_statements(written) == [("src/old.py", "def start_session(user):")], "as the writer writes it"
    assert quoted_statements(PROFILE) == [
        ("src/app.py", "return password_check(user)"),
        ("src/old.py", "def start_session(user):"),
        ("python:httpx/_client.py", "class Client(BaseClient):"),
    ]


def test_a_quote_gone_from_the_code_is_counted_and_the_refresh_named(tmp_path, capsys) -> None:
    ws = profiled(tmp_path)
    capsys.readouterr()
    assert run(tmp_path, "status") == 0
    assert LINE not in capsys.readouterr().out, "a profile whose quotes all hold says nothing"
    write_text(tmp_path / "src/old.py", "def begin(user):\n    return {}\n")
    assert profile_gone(ws) == (1, 2), "the library's statement is not looked for"
    capsys.readouterr()
    assert run(tmp_path, "status") == 0
    (said,) = [line for line in capsys.readouterr().out.splitlines() if line.startswith(LINE)]
    assert "1 of 2 quotes no longer in the code" in said and "init --refresh" in said


def test_a_quote_moved_to_another_file_holds(tmp_path) -> None:
    ws = profiled(tmp_path, files={**FILES, "src/old.py": "x = 1\n", "src/session.py": "def start_session(user):\n"})
    assert profile_gone(ws) == (0, 2)


def test_no_profile_one_that_does_not_read_or_nothing_to_look_for_says_nothing(tmp_path) -> None:
    ws = seeded(tmp_path)
    assert profile_gone(ws) == (0, 0)
    (tmp_path / ".spec/profile.md").write_bytes(b"\xff\xfe not text")
    assert profile_gone(ws) == (0, 0)
    write_text(tmp_path / ".spec/profile.md", "# Profile\n\nNothing found yet.\n")
    assert profile_gone(ws) == (0, 0)


def test_outside_a_repository_a_quote_not_in_its_file_is_not_counted(tmp_path) -> None:
    ws = seeded(tmp_path)
    for path, text in FILES.items():
        write_text(tmp_path / path, text)
    write_text(tmp_path / "src/old.py", "def begin(user):\n")
    write_text(tmp_path / ".spec/profile.md", PROFILE)
    assert profile_gone(ws) == (0, 1), "git cannot look elsewhere: the gone one is unknown, not gone"


def test_a_profile_statement_is_never_looked_for_outside_the_repository(tmp_path) -> None:
    outside = tmp_path / "outside.py"
    write_text(outside, "secret = 1\n")
    profile = "# Profile\n\n## Conventions\n\n- `../outside.py:1` Out.\n  > secret = 1\n"
    ws = profiled(tmp_path / "repo", profile=profile)
    assert profile_gone(ws) == (0, 0)


@pytest.mark.usefixtures("fake_provider")
def test_propose_says_it_before_its_first_call(tmp_path, capsys) -> None:
    profiled(tmp_path)
    write_text(tmp_path / "src/old.py", "def begin(user):\n    return {}\n")
    capsys.readouterr()
    run(tmp_path, "propose", "Add passkeys", "--no-input", "--no-explore")
    assert capsys.readouterr().out.splitlines()[0].startswith(LINE), "said before anything is spent"


def test_a_quote_a_secret_was_scrubbed_from_is_not_counted(tmp_path) -> None:
    """Found by phase 17's code review: the reading quotes scrubbed text, so a quote holding a stand-in for a secret
    is never in the code, and was counted gone on every `status`, through any refresh."""
    profile = PROFILE.replace("return password_check(user)", 'URL = "postgres://app:[REDACTED:password]@db/app"')
    ws = profiled(tmp_path, profile=profile)
    assert profile_gone(ws) == (0, 1)


def test_a_statement_is_read_to_its_own_code_span_and_with_no_note() -> None:
    """Found by phase 17's code review: a note mentioning `b.py:10` took the path to the note's span, and a statement
    whose note was empty, its space stripped, or followed by a tab, was passed over."""
    text = "- `src/a.py:3` Calls `b.py:10` here.\n  > def call_b():\n- `src/c.py:4`\n  > def c_alone():\n"
    text += "- `src/d.py:5`\ta tab after the span.\n  > def d_tabbed():\n"
    assert quoted_statements(text) == [
        ("src/a.py", "def call_b():"),
        ("src/c.py", "def c_alone():"),
        ("src/d.py", "def d_tabbed():"),
    ]
