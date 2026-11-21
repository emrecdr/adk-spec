"""The labelled set and its measurement: each case is a well-formed change with one fault planted, and the scoring
counts a fault as caught only by a finding on its file that names it."""

from __future__ import annotations

import pytest
from conftest import on_the_fake, run

from scripts import cases, measure
from scripts.cases import CASES, Expected
from scripts.measure import Seen, scored


@pytest.fixture(autouse=True)
def _fake_arm(monkeypatch) -> None:
    on_the_fake(monkeypatch)


def case(name: str):
    return next(one for one in CASES if one.name == name)


def test_the_set_holds_six_cases_one_of_them_clean_and_one_for_verify() -> None:
    assert [one.name for one in CASES] == [
        "contradiction",
        "ambiguity",
        "no-task",
        "constitution",
        "clean",
        "half-done",
    ]
    assert [one.name for one in CASES if one.clean] == ["clean"] and case("clean").expect == ()
    assert [one.command for one in CASES if one.command != "check"] == ["verify"]


def test_a_planted_fault_is_caught_by_a_finding_on_its_file_that_names_it() -> None:
    planted = case("contradiction")
    right = Seen("check.contradiction", "brief.md", "No change to session length. The delta ends sessions early.", True)
    assert scored(planted, [right]) == measure.Score(caught=1, missed=0, false_blocking=0)
    wrong_file = Seen("check.contradiction", "tasks.md", "session", True)
    wrong_kind = Seen("check.duplication", "brief.md", "session", False)
    silent = Seen("check.contradiction", "brief.md", "The title is long.", False)
    assert scored(planted, [wrong_file, wrong_kind, silent]) == measure.Score(caught=0, missed=1, false_blocking=1)


def test_a_blocking_finding_on_a_clean_case_is_counted_as_false() -> None:
    clean = case("clean")
    assert scored(clean, [Seen("check.gap", "brief.md", "x", True), Seen("check.gap", "brief.md", "y", False)]) == (
        measure.Score(caught=0, missed=0, false_blocking=1)
    )


def test_an_expectation_matches_by_prefix_any_of_its_files_and_any_of_its_words() -> None:
    wanted = Expected("verdict.un", ("REQ-AUTH-002",))
    assert wanted.met_by(Seen("verdict.unclear", "REQ-AUTH-002", "", False))
    assert wanted.met_by(Seen("verdict.unmet", "REQ-AUTH-002", "", False))
    assert not wanted.met_by(Seen("verdict.met", "REQ-AUTH-002", "", False))
    worded = Expected("check.ambiguity", ("specs/auth/spec.md",), ("quickly", "fast"))
    assert worded.met_by(Seen("check.ambiguity", "specs/auth/spec.md", "How FAST is fast?", False))


@pytest.mark.parametrize("name", [one.name for one in CASES])
def test_every_case_builds_a_workspace_that_reads(tmp_path, name) -> None:
    """The labelled set is itself well formed: a case that did not validate would measure its own mistake."""
    change = case(name).build(tmp_path)
    assert run(tmp_path, "validate") in (0, 1), "never a usage error"
    assert run(tmp_path, "status") == 0 and change == cases.CHANGE


def test_the_case_code_decides_is_found_with_no_model(tmp_path, fake_provider) -> None:
    row = measure.measured(case("no-task"), runs=2, folder=tmp_path)
    assert (row.caught, row.runs, row.tokens) == ([2], 2, 0) and fake_provider.requests == []


def verdicts_of_the_half_done_case() -> dict:
    """What a model that reads the half-done diff rightly would answer: the passkey met by its line, the lock not."""
    met = {"id": "REQ-AUTH-003", "verdict": "met", "reason": "Sign-in tries the passkey first."}
    met["evidence"] = [{"path": "src/auth.py", "quote": cases.HALF_DONE_LINE}]
    unmet = {"id": "REQ-AUTH-002", "verdict": "unmet", "evidence": [], "reason": "The lock still falls at five."}
    return {"verdicts": [met, unmet]}


def test_the_measurement_runs_whole_on_the_fake(tmp_path, capsys, fake_provider) -> None:
    fake_provider.answers_when("You judge whether a diff", verdicts_of_the_half_done_case())
    out = tmp_path / "measured.md"
    assert measure.main(["--runs", "2", "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    rows = [line for line in text.split("\n") if line.startswith("| `")]
    assert len(rows) == 6 and "fake on gemini" in text and "2 runs a case" in text
    assert "| `no-task` | check | 2/2 |" in text and "| `half-done` | verify | 2/2, 2/2 |" in text
    assert "| `clean` | check | nothing planted | 0 |" in text
    assert "about 10 model calls" in capsys.readouterr().out, "it says what it is about to spend before it starts"
    assert len(fake_provider.requests) == 10


def test_one_case_can_be_measured_alone(tmp_path, fake_provider) -> None:
    assert measure.main(["--runs", "1", "--case", "clean", "--out", str(tmp_path / "one.md")]) == 0
    assert len(fake_provider.requests) == 1
    assert measure.main(["--case", "no-such-case"]) == 2
