"""What a command says while it works and when it ends: which stage it is on, on a terminal alone, and what to read
first. Waiting in silence and not knowing where to look are two of the things people call heavy in tools like this."""

from __future__ import annotations

import re

import pytest
from conftest import BRIEF_OWING_A_DESIGN, on_the_fake, run, seeded

from adk_spec.interfaces import cli

REQUEST = "Let users sign in with a passkey."
BRIEF, DELTAS = "You write the brief of a change", "You write the requirement deltas"


@pytest.fixture(autouse=True)
def _fake_arm(monkeypatch) -> None:
    on_the_fake(monkeypatch)


@pytest.mark.usefixtures("fake_provider")
def test_nothing_is_said_where_the_error_stream_is_no_terminal(tmp_path, capsys) -> None:
    seeded(tmp_path)
    assert run(tmp_path, "propose", REQUEST, "--tier", "lean", "--id", "quiet") == 0
    assert "working" not in capsys.readouterr().err, "a pipe, a script and a test read what they read before"


def test_a_terminal_is_told_each_stage_as_it_starts_and_a_second_try_is_marked(
    tmp_path, monkeypatch, capsys, fake_provider
) -> None:
    seeded(tmp_path)
    monkeypatch.setattr(cli, "_on_a_terminal", lambda: True)
    fake_provider.answers_each_time(DELTAS, iter(["not json", None]))
    assert run(tmp_path, "propose", REQUEST, "--tier", "lean", "--id", "told") == 0
    said = capsys.readouterr()
    lines = [line for line in said.err.splitlines() if line.startswith("working")]
    # The audit of 25 November (U1): what a call does, in plain words, and the time since the command began.
    assert all(re.search(r"  \d+:\d\d$", line) for line in lines), lines
    assert [re.sub(r"  \d+:\d\d$", "", line) for line in lines] == [
        "working   writing the brief",
        "working   writing the requirements",
        "working   writing the requirements, again",
        "working   writing the tasks",
    ]
    assert "working" not in said.out, "what a script reads holds no progress"


def test_propose_names_what_to_read_first_with_its_length(tmp_path, capsys, fake_provider) -> None:
    """Review matters most early and short, on the intent and the design: a person is told where to start, and how
    long it is."""
    seeded(tmp_path)
    assert run(tmp_path, "propose", REQUEST, "--tier", "lean", "--id", "short") == 0
    out = capsys.readouterr().out
    # The owner's choice after phase 15's live runs: a brief that assumed where it might have asked says so.
    assert re.search(r"^read      brief\.md \(\d+ lines, 1 assumption\) first$", out, re.MULTILINE)
    assert out.index("read      ") < out.index("next      "), "what to read, then what to run"
    fake_provider.answers_when(BRIEF, BRIEF_OWING_A_DESIGN)
    assert run(tmp_path, "propose", REQUEST, "--tier", "lean", "--id", "designed") == 0
    out = capsys.readouterr().out
    said = r"^read      brief\.md \(\d+ lines, 1 assumption\) and design\.md \(\d+ lines\) first$"
    assert re.search(said, out, re.MULTILINE)
