"""Statements about a repository's code: kept only where the quote is in the file named, and written as
`context.md`, the file a plan is drafted from."""

from __future__ import annotations

from adk_spec.domain.context_md import (
    PROFILE_HEADING,
    PROFILE_SECTIONS,
    SECTIONS,
    drafted_rules,
    render_context,
    unknown_count,
)
from adk_spec.domain.convert import to_statements
from adk_spec.domain.drafts import SurveyDraft
from adk_spec.domain.model import Statement

SESSION = "import time\n\n\ndef start_session(user):\n    return Session(user, started=time.time())\n"
TEXTS = {"src/auth/session.py": SESSION, "src/app.py": "def login(user):\n    return password(user)\n"}


def survey(*statements: dict) -> SurveyDraft:
    return SurveyDraft.model_validate(
        {"statements": list(statements), "more_files": [], "more_folders": [], "more_searches": []}
    )


def stated(**changed: str) -> dict:
    held = {"kind": "exists", "file": "src/auth/session.py", "quote": "def start_session(user):"}
    return {**held, "note": "Sessions are started in one place.", **changed}


def test_a_statement_is_kept_where_its_quote_is_in_the_file_it_names() -> None:
    kept, dropped = to_statements(survey(stated()), TEXTS)
    assert dropped == 0 and kept == [
        Statement(
            kind="exists",
            path="src/auth/session.py",
            line=4,
            quote="def start_session(user):",
            note="Sessions are started in one place.",
        )
    ]


def test_a_statement_with_a_quote_that_is_nowhere_or_in_another_file_is_left_out() -> None:
    """A file's text may tell a model what to write. What it writes is kept only where it quotes a real line of
    the file it names: a statement cannot be dictated into the context."""
    invented = stated(quote="def start_session(user, remember_me):", note="Sessions can be remembered.")
    elsewhere = stated(file="src/app.py")
    unread = stated(file="src/billing.py", quote="def charge(amount):")
    short = stated(quote="def")
    kept, dropped = to_statements(survey(invented, elsewhere, unread, short, stated(kind="touches")), TEXTS)
    assert dropped == 4 and [one.kind for one in kept] == ["touches"]


def test_a_statements_words_are_plain_text_and_its_quote_one_line() -> None:
    escape, bell = chr(27), chr(7)
    over_lines = "def start_session(user):\n    return Session(user, started=time.time())"
    (one,), _dropped = to_statements(survey(stated(quote=over_lines, note=f"Started{escape}[2J here{bell}.")), TEXTS)
    assert one.note == "Started [2J here ." and "\n" not in one.quote
    assert one.quote == "def start_session(user): return Session(user, started=time.time())" and one.line == 4


def test_context_md_has_a_section_a_kind_and_says_what_was_read_and_left_out() -> None:
    kept, _dropped = to_statements(
        survey(
            stated(),
            stated(kind="touches", file="src/app.py", quote="return password(user)", note="Sign-in is decided here."),
            stated(kind="risk", quote="started=time.time()", note="Session age is wall-clock time."),
        ),
        TEXTS,
    )
    text = render_context(
        "Context: passkeys",
        at="2026-11-22T10:00:00+00:00",
        commit="1a2b3c4d5e6f7a8b9c0d",
        statements=kept,
        read=("src/auth/session.py (whole)", "src/app.py (lines 1 to 2 of 40)"),
        left_out=("config/prod.yaml: git lists no such file",),
        dropped=2,
    )
    assert text.startswith("# Context: passkeys\n\nRead from the repository at commit 1a2b3c4d5e6f on 2026-11-22.\n")
    headings = [line for line in text.split("\n") if line.startswith("## ")]
    assert headings == [
        "## What exists",
        "## Where the change plugs in",
        "## Risks and what is unclear",
        "## What was read",
    ]
    assert "- `src/app.py:2` Sign-in is decided here.\n  > return password(user)\n" in text
    assert "- src/app.py (lines 1 to 2 of 40)\n" in text
    assert "Left out: 2 statements whose quote was not in the file named." in text
    assert "Not read: config/prod.yaml: git lists no such file." in text
    assert [kind for kind, _heading in SECTIONS] == ["exists", "touches", "convention", "risk"]


def test_a_partial_reading_says_so_at_its_top() -> None:
    text = render_context(
        "Context: passkeys",
        at="2026-11-22T10:00:00+00:00",
        commit=None,
        statements=[],
        read=(),
        partial="the token ceiling was spent",
    )
    assert "Read from the repository on 2026-11-22.\n\nThis reading is partial: the token ceiling was spent.\n" in text
    assert "## What was read\n\n- nothing\n" in text


def test_a_reading_across_repositories_names_each_commit() -> None:
    text = render_context(
        "Context: passkeys",
        at="2026-11-22T10:00:00+00:00",
        commit="1a2b3c4d5e6f7a8b9c0d",
        statements=[],
        read=(),
        others={"api": "9f8e7d6c5b4a3f2e1d0c", "web": None},
    )
    assert text.startswith(
        "# Context: passkeys\n\nRead on 2026-11-22: this repository at commit 1a2b3c4d5e6f, api at commit 9f8e7d6c5b4a,"
        " web.\n"
    )


def test_what_is_still_unknown_has_its_section_and_the_disputed_are_counted() -> None:
    held = Statement(
        kind="touches", path="api/src/routes.py", line=2, quote="return x()", note="Here.", within="def a():"
    )
    text = render_context(
        "Context: passkeys",
        at="2026-11-22T10:00:00+00:00",
        commit=None,
        statements=[held],
        read=("api/src/routes.py (whole)",),
        dropped=2,
        disputed=1,
        unknown=[("Does the mobile app call it too?", "a repository not named here"), ("Who owns sessions?", "")],
    )
    assert "- `api/src/routes.py:2` Here.\n  in: def a():\n  > return x()\n" in text
    assert (
        "## What is still unknown\n\n- Does the mobile app call it too? Look in: a repository not named here.\n"
        "- Who owns sessions?\n\n## What was read"
    ) in text
    assert "Left out: 2 statements whose quote was not in the file named; 1 the review disputed." in text
    assert unknown_count(text) == 2 and unknown_count("# Context: x\n") == 0


# Phase 8: the profile of a repository, and the rules drafted from it.


def test_a_profile_has_its_own_heading() -> None:
    text = render_context(PROFILE_HEADING, at="2026-11-22T10:00:00+00:00", commit=None, statements=[], read=())
    assert text.startswith("# This repository\n\nRead from the repository on 2026-11-22.\n")


def test_drafted_rules_are_the_conventions_each_with_its_evidence() -> None:
    tests = Statement(
        kind="convention", path="tests/test_app.py", line=1, quote="def test_login():", note="Each module has a test."
    )
    app = Statement(kind="exists", path="src/app.py", line=1, quote="def login(user):", note="Sign-in is here.")
    text = drafted_rules([tests, app])
    assert text.startswith("## Drafted from the code\n\n") and "adk-spec init" in text
    assert "keep, edit or delete" in text and "Sign-in is here." not in text
    assert "- Each module has a test. (`tests/test_app.py:1`: `def test_login():`)\n" in text


def test_no_convention_drafts_no_rule() -> None:
    held = Statement(kind="risk", path="src/app.py", line=1, quote="def login(user):", note="Unclear.")
    assert drafted_rules([]) == "" and drafted_rules([held]) == ""


def test_a_drafted_rule_holds_its_quote_whole_whatever_backticks_it_holds() -> None:
    held = Statement(kind="convention", path="a.py", line=3, quote="use `foo", note="Errors are AppError.")
    assert "- Errors are AppError. (`a.py:3`: `` use `foo ``)\n" in drafted_rules([held])


def test_a_profile_says_where_things_live_and_not_where_a_change_plugs_in() -> None:
    held = Statement(kind="touches", path="src/app.py", line=1, quote="def login(user):", note="Sign-in lives here.")
    text = render_context(
        PROFILE_HEADING,
        at="2026-11-22T10:00:00+00:00",
        commit=None,
        statements=[held],
        read=(),
        sections=PROFILE_SECTIONS,
    )
    assert "## Where things live\n" in text and "Where the change plugs in" not in text
