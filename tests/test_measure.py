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


def test_the_set_holds_seven_cases_one_clean_one_for_verify_and_one_for_the_reading() -> None:
    assert [one.name for one in CASES] == [
        "contradiction",
        "ambiguity",
        "no-task",
        "constitution",
        "clean",
        "half-done",
        "integration",
    ]
    assert [one.name for one in CASES if one.clean] == ["clean"] and case("clean").expect == ()
    assert [one.command for one in CASES if one.command != "check"] == ["verify", "plan"]


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
    assert len(rows) == 7 and "fake on gemini" in text and "2 runs a case" in text
    assert "| `no-task` | check | 2/2 |" in text and "| `half-done` | verify | 2/2, 2/2 |" in text
    assert "| `clean` | check | nothing planted | 0 |" in text
    assert "about 16 model calls" in capsys.readouterr().out, "it says what it is about to spend before it starts"
    assert len(fake_provider.requests) == 16, "five cases of one call, and a plan: its scout, its survey, its tasks"


def test_one_case_can_be_measured_alone(tmp_path, fake_provider) -> None:
    assert measure.main(["--runs", "1", "--case", "clean", "--out", str(tmp_path / "one.md")]) == 0
    assert len(fake_provider.requests) == 1
    assert measure.main(["--case", "no-such-case"]) == 2


def test_a_run_that_fails_its_gate_is_counted_and_does_not_end_the_measurement(tmp_path, fake_provider) -> None:
    """Found by the code review: a failed run's last answer is no JSON, and reading it ended the whole measurement
    with a traceback, the runs already paid for lost."""
    fake_provider.answers_when("You review the files of a change", "not json")
    row = measure.measured(case("clean"), runs=1, folder=tmp_path)
    assert (row.failed, row.false_blocking, row.left_out) == (1, 0, []) and len(fake_provider.requests) == 3


def test_what_was_found_beyond_what_was_planted_is_kept_in_its_own_words(tmp_path, fake_provider) -> None:
    """Found by the first live measurement: three blocking findings matched nothing planted, and the report held
    their number alone, the runs being thrown away. A person is to read each one: it is a false finding, or a
    fault nobody planted."""
    stray = {"kind": "gap", "severity": "critical", "file": "brief.md", "message": "Which browsers is not said."}
    stray["quote"] = "Browsers in scope support WebAuthn."
    fake_provider.answers_when("You review the files of a change", {"findings": [stray]})
    clean = measure.measured(case("clean"), runs=1, folder=tmp_path / "clean")
    assert clean.false_blocking == 1
    assert clean.strays == [
        "run 1: `check.gap` brief.md: Browsers in scope support WebAuthn. Which browsers is not said."
    ]
    missed = measure.measured(case("ambiguity"), runs=1, folder=tmp_path / "ambiguity")
    assert missed.caught == [0] and len(missed.missed) == 1 and "check.gap on brief.md" in missed.missed[0]
    page = measure.rendered([clean, missed], model="a model", commit=None, at="t")
    assert "## Blocking on nothing planted" in page and "- `clean`, run 1: `check.gap` brief.md" in page
    assert "## Missed" in page and "- `ambiguity`, run 1: wanted check.ambiguity" in page


def test_the_clean_case_promises_nothing_its_delta_does_not_deliver() -> None:
    """Found by the second live measurement: the brief every case shares said users can register a passkey, and no
    requirement covered registering. The model named that gap, rightly, in the clean case too, and where it named
    it, it often left the planted fault unsaid."""
    promised = cases.BRIEF.what_changes.lower()
    assert "register" not in promised and "sign in with a passkey" in promised
    assert cases.PASSKEY.statement == "The system SHALL let a user sign in with a passkey."


def test_a_finding_left_out_for_its_quote_is_kept_in_its_own_words_too(tmp_path, fake_provider) -> None:
    """Found by the second live measurement: two findings were left out for quoting text that is not in the file.
    Whether one of them was the planted fault, quoted a word off, nobody can say: only their number was kept."""
    invented = {"kind": "ambiguity", "severity": "critical", "file": "specs/auth/spec.md", "message": "How fast?"}
    invented["quote"] = "The system SHALL respond very quickly indeed"
    fake_provider.answers_when("You review the files of a change", {"findings": [invented]})
    row = measure.measured(case("ambiguity"), runs=1, folder=tmp_path)
    assert row.left_out == [
        "run 1: `check.ambiguity` specs/auth/spec.md: quoted `The system SHALL respond very quickly indeed`: How fast?"
    ]
    page = measure.rendered([row], model="a model", commit=None, at="t")
    assert "## Left out, no such quote" in page and "- `ambiguity`, run 1: `check.ambiguity`" in page


def test_a_left_out_findings_file_name_cannot_break_the_page(tmp_path, fake_provider) -> None:
    """Found by the code review: a left-out finding's path is the model's own `file`, never printed before, and it
    reached the page as it came."""
    invented = {"kind": "gap", "severity": "warning", "message": "m", "quote": "nowhere to be found at all"}
    invented["file"] = "specs/auth/spec.md\n## Missed"
    fake_provider.answers_when("You review the files of a change", {"findings": [invented]})
    row = measure.measured(case("clean"), runs=1, folder=tmp_path)
    assert row.left_out == ["run 1: `check.gap` specs/auth/spec.md ## Missed: quoted `nowhere to be found at all`: m"]


def test_the_integration_case_is_caught_where_a_statement_names_the_planted_file(tmp_path, fake_provider) -> None:
    """Brownfield, part 1: a small repository with one place where sign-in starts a session, and an old file of a
    similar name that nothing uses. The reading is caught out where it names only the old one."""
    scout = {"files": ["src/auth/password.py", "src/legacy/auth_session_old.py"], "folders": [], "searches": []}
    fake_provider.answers_when("You choose what to read", {**scout, "reason": "Where sign-in starts a session."})
    planted = {"kind": "touches", "file": "src/auth/password.py", "quote": "return start_session(user)"}
    decoy = {"kind": "exists", "file": "src/legacy/auth_session_old.py", "quote": "def start_session_v1(user):"}
    more = {"more_files": [], "more_folders": [], "more_searches": []}
    survey = "You read parts of a repository's code"
    fake_provider.answers_when(
        survey, {"statements": [{**planted, "note": "A passkey sign-in ends here too."}], **more}
    )
    found = measure.measured(case("integration"), runs=1, folder=tmp_path / "found")
    assert (found.caught, found.failed) == ([1], 0) and found.tokens == 360, "the scout, the survey and the tasks"
    fake_provider.clear()
    fake_provider.answers_when("You choose what to read", {**scout, "reason": "Where sign-in starts a session."})
    fake_provider.answers_when(survey, {"statements": [{**decoy, "note": "Sessions start here."}], **more})
    missed = measure.measured(case("integration"), runs=1, folder=tmp_path / "missed")
    assert missed.caught == [0] and "context.exists on src/legacy/auth_session_old.py" in missed.missed[0]


def test_a_model_no_plan_stage_can_run_is_said_before_anything_is_spent(monkeypatch, capsys, fake_provider) -> None:
    monkeypatch.setenv("SPEC_SCOUT_MODEL", "gpt-4.1")  # ADK would send it to another provider's class
    assert measure.main(["--runs", "1", "--case", "integration"]) == 2
    assert "SPEC_SCOUT_MODEL" in capsys.readouterr().err and fake_provider.requests == []
