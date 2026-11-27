"""Phase 17: the profile every drafting stage reads, checked against the code it quotes, by code alone."""

from __future__ import annotations

import os

import pytest
from conftest import on_the_fake, repository, run, seeded

from adk_spec.domain.context_md import quoted_statements, render_context
from adk_spec.domain.model import Statement
from adk_spec.domain.secrets import scrub_lines
from adk_spec.workspace.context import PROFILE_MAX_CHARS
from adk_spec.workspace.evidence import profile_gone, quote_holds
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
    # Outside a repository git lists nothing, so nothing is looked for: each is unknown (an outside audit of 171f1c4).
    assert profile_gone(ws) == (0, 0)


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


def test_a_quote_the_reading_made_plain_still_holds(tmp_path) -> None:
    """Found by phase 17's fourth review: the reading stores a quote with each unprintable character as a space, a
    soft hyphen say, and the raw file never matched it."""
    profile = PROFILE.replace("return password_check(user)", "label = Ta belle_einstellung")
    files = {**FILES, "src/app.py": "label = Ta­belle_einstellung\n"}
    ws = profiled(tmp_path, files=files, profile=profile)
    assert profile_gone(ws) == (0, 2)


def test_a_profile_past_the_stages_cap_is_checked_whole(tmp_path) -> None:
    """Found by phase 17's fourth review: the profile was read cut at the cap a stage is given, and a quote the cut
    shortened read as gone."""
    head = "# Profile\n\n## Conventions\n\n"
    statement = "- `src/app.py:2` Sign-in goes through the password check.\n"
    profile = head + "x" * PROFILE_MAX_CHARS + "\n\n" + statement + "  > return password_check(user)\n"
    ws = profiled(tmp_path, profile=profile)
    assert profile_gone(ws) == (0, 1)


def test_a_nul_and_a_twice_quoted_line_count_as_nothing_more(tmp_path, capsys) -> None:
    """Found by phase 17's fourth review: a NUL in a quote stopped `status` with a traceback; one line quoted by two
    statements counted twice; one quote was "quotes"."""
    twice = "- `src/old.py:1` The session helper.\n  > def start_session(user):\n"
    ws = profiled(
        tmp_path, profile="# Profile\n\n## Conventions\n\n" + twice + twice.replace("session helper", "helper")
    )
    assert quote_holds(tmp_path, ".", "src/app.py", "zzzzzzzz\x00yyyy", ()) is False, "no NUL reaches git"
    write_text(tmp_path / "src/old.py", "def begin(user):\n")
    assert profile_gone(ws) == (1, 1)
    capsys.readouterr()
    assert run(tmp_path, "status") == 0
    assert "profile: 1 of 1 quote no longer in the code" in capsys.readouterr().out


def test_a_quote_a_secret_was_scrubbed_from_holds_while_its_line_stands(tmp_path) -> None:
    """Found by phase 17's reviews: a reading quotes scrubbed text, whole or cut through a secret's stand-in, and such a
    quote read as gone, or was guessed unknown by its shape. It is looked for in the file as a reading is shown it."""
    key = "AKIA" + "IOSFODNN7EXAMPLE"
    shown = scrub_lines(f'KEY = "{key}"')[0]
    quotes = (shown, shown[: shown.index("[REDA") + 5], shown[shown.index("ACTED") :])
    entries = "".join(f"- `src/conf.py:1` Note {n}.\n  > {quote}\n" for n, quote in enumerate(quotes))
    ws = profiled(tmp_path, files={**FILES, "src/conf.py": f'KEY = "{key}"\n'}, profile="# Profile\n\n" + entries)
    assert profile_gone(ws) == (0, 3)
    write_text(tmp_path / "src/conf.py", "KEY = None\n")
    assert profile_gone(ws) == (3, 3), "the line taken out, each quote of it is gone"


def test_a_quote_too_short_to_look_for_is_unknown(tmp_path) -> None:
    """Found by phase 18's code review: a quote too short to find anywhere read as gone."""
    profiled(tmp_path)
    assert quote_holds(tmp_path, ".", "src/app.py", "x = 1", ()) is None


def test_a_file_shared_by_many_quotes_is_read_once(tmp_path, monkeypatch) -> None:
    """The audit of 25 November (H3): each quote read its file whole again."""
    from adk_spec.workspace import evidence

    repository(tmp_path, {"src/a.py": "def start_session(user):\n    return user\n"})
    reads: list[str] = []
    real = evidence.read_text
    monkeypatch.setattr(evidence, "read_text", lambda path: reads.append(path.name) or real(path))
    assert quote_holds(tmp_path, ".", "src/a.py", "def start_session(user):", ())
    assert quote_holds(tmp_path, ".", "src/a.py", "    return user", ())
    assert reads.count("a.py") == 1


def test_a_quote_in_a_file_past_what_a_reading_reads_is_unknown(tmp_path, monkeypatch) -> None:
    """The audit of 25 November (H3): a file of any size was read whole for a quote; a reading reads none so large."""
    from adk_spec.workspace import evidence

    monkeypatch.setattr(evidence, "FILE_MAX_BYTES", 10)
    repository(tmp_path, {"big.txt": "x" * 100})
    assert quote_holds(tmp_path, ".", "big.txt", "xxxxxxxxxxxx", ()) is None


def test_a_quote_moved_into_a_file_past_the_cap_is_unknown_not_gone(tmp_path, monkeypatch) -> None:
    """Found by the code review of phase 24: the search of other files read a file past the cap as not holding it."""
    from adk_spec.workspace import evidence

    monkeypatch.setattr(evidence, "FILE_MAX_BYTES", 60)
    repository(tmp_path, {"src/a.py": "x = 1\n", "gen/big.py": "def start_session(user):\n" + "#" * 80 + "\n"})
    assert quote_holds(tmp_path, ".", "src/a.py", "def start_session(user):", ()) is None


def test_a_quote_is_looked_for_only_in_a_file_git_lists(tmp_path) -> None:
    """Found by an outside audit of 171f1c4, and reproduced: an evidence line could learn whether a string is in
    `.git/config`, which holds a CI runner's token, or in an ignored `.env`, from whether `validate` noted it gone."""
    from conftest import _git

    repository(tmp_path, {"src/a.py": "x = 1\n", ".gitignore": ".env\n"})
    (tmp_path / ".env").write_text("SECRET_TOKEN=abcd1234efgh\n", encoding="utf-8")
    _git(tmp_path, "config", "http.extraheader", "AUTHORIZATION: basic c2VjcmV0dG9rZW4=")
    for path, guess in ((".env", "SECRET_TOKEN=abcd1234"), (".git/config", "AUTHORIZATION: basic c2Vj")):
        assert quote_holds(tmp_path, ".", path, guess, ()) is None, path


def test_a_quote_over_a_secret_is_never_matched_against_the_secret(tmp_path) -> None:
    """Found by an outside audit of 171f1c4: matched against the raw text first, a guess at a tracked file's
    password held where a wrong one did not."""
    repository(tmp_path, {"src/settings.py": 'PASSWORD = "hunter2pass9"\n'})
    right = quote_holds(tmp_path, ".", "src/settings.py", 'PASSWORD = "hunter2pass9"', ())
    wrong = quote_holds(tmp_path, ".", "src/settings.py", 'PASSWORD = "zzzzzzzz99"', ())
    assert right is wrong is False


@pytest.mark.skipif(os.name == "nt", reason="a link needs a privilege on Windows that a test run does not hold")
def test_a_quote_in_a_file_reached_through_a_link_is_unknown(tmp_path) -> None:
    from conftest import _git

    repository(tmp_path, {"src/a.py": "x = 1\n", ".gitignore": ".env\n"})
    (tmp_path / ".env").write_text("SECRET_TOKEN=abcd1234efgh\n", encoding="utf-8")
    (tmp_path / "src/env").symlink_to(tmp_path / ".env")
    _git(tmp_path, "add", "src/env")
    assert quote_holds(tmp_path, ".", "src/env", "SECRET_TOKEN=abcd1234", ()) is None


def test_another_repositorys_quote_honours_its_own_exclusions(tmp_path) -> None:
    """Found by an outside audit of 171f1c4: another repository's evidence was looked for with no exclusions."""
    seeded(tmp_path / "app")
    repository(
        tmp_path / "api",
        {
            ".spec/config.toml": '[project]\ndefault_tier = "lean"\n\n[repository]\nexclude = ["secrets/**"]\n',
            "secrets/key.txt": "the token value here\n",
        },
    )
    assert quote_holds(tmp_path / "app", "../api", "secrets/key.txt", "the token value here", ()) is None
