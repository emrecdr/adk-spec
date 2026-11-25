"""The next work: what a verification found unmet, written where the coding assistant looks, and the next step that
names it."""

from __future__ import annotations

import json

import pytest
from conftest import on_the_fake, run
from samples import TASKS
from test_lifecycle import approved, phrase
from test_verify import REPORT, VERIFY, approved_in_a_repository, implemented, verdicts

from adk_spec.domain.drafts import VerdictsDraft
from adk_spec.domain.lifecycle import verified
from adk_spec.domain.remaining import remaining, render_remaining
from adk_spec.domain.tasks_md import parse_tasks
from adk_spec.domain.verify import NO_VERDICT, UNGROUNDED, Verdict, grounded

LEFT = ".spec/changes/passkeys/reports/remaining.md"
GROUPS = parse_tasks(TASKS)  # T002, ticked, serves 004, 002 and 001 and names two files under src/auth/
SAID = [
    Verdict("REQ-AUTH-002", "unmet", (), "Still five."),
    Verdict("REQ-AUTH-004", "met", (("src/auth.py", "return passkey(user)"),), "Sign-in goes through the passkey."),
]
UNMET = verdicts(**{"002": {"verdict": "unmet", "evidence": [], "reason": "Still five."}})


@pytest.fixture(autouse=True)
def _fake_arm(monkeypatch) -> None:
    on_the_fake(monkeypatch)


def test_a_ticked_task_whose_requirement_is_unmet_comes_first() -> None:
    text = render_remaining("passkeys", remaining(SAID, GROUPS, frozenset({"src/auth.py"})))
    assert "REQ-AUTH-002" in text and "REQ-AUTH-004" not in text
    assert "Ticked, yet unmet: T002" in text and text.index("T002") < text.index("Still five.")


def test_a_file_a_task_named_that_the_diff_never_touched_is_listed() -> None:
    (left,) = remaining(SAID, GROUPS, frozenset({"src/auth/passkey.py"}))
    assert left.untouched == ("src/auth/lockout.py",) and left.ticked == ("T002",) and left.open == ()


def test_the_models_reason_is_labelled_as_its_own_words() -> None:
    text = render_remaining("passkeys", remaining(SAID, GROUPS, frozenset()))
    assert "The model's reason, which code has not checked: Still five." in text


def test_verify_writes_the_remaining_work_and_names_it(tmp_path, capsys, fake_provider) -> None:
    approved_in_a_repository(tmp_path)
    implemented(tmp_path)
    fake_provider.answers_when(VERIFY, UNMET)
    capsys.readouterr()
    assert run(tmp_path, "verify", "passkeys") == 1
    assert "Still five." in (tmp_path / LEFT).read_text(encoding="utf-8")
    (wrote,) = [line for line in capsys.readouterr().out.splitlines() if line.startswith("wrote ")]
    assert REPORT in wrote and LEFT in wrote


def test_the_remaining_work_is_removed_once_everything_is_met(tmp_path, fake_provider) -> None:
    approved_in_a_repository(tmp_path)
    implemented(tmp_path)
    fake_provider.answers_each_time(VERIFY, iter([UNMET, None]))  # unmet, then every one met
    assert run(tmp_path, "verify", "passkeys") == 1
    assert (tmp_path / LEFT).is_file()
    assert run(tmp_path, "verify", "passkeys") == 0
    assert not (tmp_path / LEFT).exists()


def test_the_next_step_names_the_unmet_requirements(tmp_path, capsys, fake_provider) -> None:
    approved_in_a_repository(tmp_path)
    implemented(tmp_path)
    fake_provider.answers_when(VERIFY, UNMET)
    assert run(tmp_path, "verify", "passkeys") == 1
    capsys.readouterr()
    assert run(tmp_path, "status", "--json") == 0
    (row,) = json.loads(capsys.readouterr().out)["changes"]
    assert row["next"] == "REQ-AUTH-002 unmet: work from reports/remaining.md, then run `adk-spec verify passkeys`"


def test_the_next_step_names_three_unmet_requirements_and_counts_the_rest() -> None:
    left = {f"REQ-A-00{n}": "unmet" for n in range(1, 6)}
    state = verified(approved("standard"), left, base="c0", diff="sha256:d", at="t")
    said = phrase(state, [], [])
    assert said.startswith("REQ-A-001, REQ-A-002, REQ-A-003 and 2 more unmet: work from reports/remaining.md")
    assert said.endswith(f"then run `adk-spec verify {state.id}`")


def test_failed_tests_come_before_unmet_requirements() -> None:
    state = verified(approved(), {"REQ-A-001": "unmet"}, base="c0", diff="sha256:d", at="t", tests={".": "failed"})
    assert phrase(state, [], []).startswith("the tests failed")


def test_a_report_that_will_not_be_removed_loses_no_verification(tmp_path, monkeypatch, fake_provider) -> None:
    """Found by the code review: on Windows a held file refused to be removed, after the verification was paid for and
    before it was recorded."""
    from pathlib import Path

    approved_in_a_repository(tmp_path)
    implemented(tmp_path)
    fake_provider.answers_each_time(VERIFY, iter([UNMET, None]))
    assert run(tmp_path, "verify", "passkeys") == 1
    removing = Path.unlink

    def held(path, missing_ok=False):
        if path.name == "remaining.md":
            raise PermissionError(32, "The process cannot access the file")
        removing(path, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", held)
    assert run(tmp_path, "verify", "passkeys") == 0
    assert json.loads((tmp_path / ".spec/changes/passkeys/change.json").read_text())["status"] == "verified"


def test_a_lean_change_with_an_unmet_requirement_is_pointed_to_its_archive() -> None:
    """Found by the code review: a lean change owes no verification, and was sent to verify again."""
    state = verified(approved(), {"REQ-A-001": "unmet"}, base="c0", diff="sha256:d", at="t")
    assert phrase(state, [], []).endswith(f"then run `adk-spec archive {state.id}`")


def test_task_paths_are_read_as_paths() -> None:
    """Found by the code review: a task's `./` path, a backticked one or a folder read as untouched by the work."""
    named = "./src/auth/passkey.py, `src`, src\\auth\\passkey.py"  # a backslash, as on Windows, too
    groups = parse_tasks(TASKS.replace("src/auth/passkey.py, src/auth/lockout.py", named))
    (left,) = remaining(SAID, groups, frozenset({"src/auth/passkey.py"}))
    assert left.untouched == ()


def test_a_change_verified_by_override_is_not_sent_to_a_remaining_list() -> None:
    """Found by the code review: verified over its verdicts, then approved again, a change was sent to the remaining
    list its verification removed."""
    state = verified(approved("standard"), {"REQ-A-001": "unmet"}, base="c0", diff="sha256:d", at="t", override="ok")
    assert "remaining.md" not in phrase(state.model_copy(update={"status": "approved"}), [], [])


def test_the_remaining_list_names_the_step_the_tier_owes() -> None:
    text = render_remaining("passkeys", remaining(SAID, GROUPS, frozenset()), last="archive")
    assert "then run `adk-spec archive passkeys`" in text


def test_a_change_approved_again_after_an_edit_is_not_sent_to_the_old_remaining_list(
    tmp_path, capsys, fake_provider
) -> None:
    """Found by the code review: revised and approved again, a change was still sent to the unmet requirements of the
    verification its earlier files had."""
    approved_in_a_repository(tmp_path)
    implemented(tmp_path)
    fake_provider.answers_when(VERIFY, UNMET)
    assert run(tmp_path, "verify", "passkeys") == 1
    brief = tmp_path / ".spec/changes/passkeys/brief.md"
    brief.write_text(brief.read_text(encoding="utf-8") + "\nRevised after the verification.\n", encoding="utf-8")
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer") == 0
    assert not (tmp_path / LEFT).exists(), "the list of what was left goes with the verification it came from"
    assert not (tmp_path / ".spec/changes/passkeys/reports/summary.md").exists(), "and so does its summary"
    capsys.readouterr()
    assert run(tmp_path, "status", "--json") == 0
    (row,) = json.loads(capsys.readouterr().out)["changes"]
    assert "remaining.md" not in row["next"]


def test_a_summary_that_cannot_be_written_leaves_the_evidence_of_the_verification(tmp_path, monkeypatch) -> None:
    """Found by the code review: a summary refused after the verification was recorded left the change's evidence of
    an earlier one, and the archive then took the living evidence out with nothing put in."""
    from adk_spec.workspace.layout import Workspace

    approved_in_a_repository(tmp_path)
    implemented(tmp_path)
    writing = Workspace.write_report

    def held(self, change_id, name, text):
        if name == "summary.md":
            raise OSError(13, "Permission denied")
        return writing(self, change_id, name, text)

    monkeypatch.setattr(Workspace, "write_report", held)
    assert run(tmp_path, "verify", "passkeys") == 0
    at = json.loads((tmp_path / ".spec/changes/passkeys/change.json").read_text())["verification"]["at"]
    assert f" | {at} | " in (tmp_path / ".spec/changes/passkeys/evidence.md").read_text(encoding="utf-8")


def test_code_found_reasons_are_said_as_codes() -> None:
    """Found by the code review: a reason code wrote itself, that no quoted line is in the diff, was labelled as the
    model's words, which code had not checked. Both are as `grounded` writes them."""
    draft = VerdictsDraft.model_validate(
        {"verdicts": [{"id": "REQ-AUTH-002", "verdict": "met", "evidence": [], "reason": "three now."}]}
    )
    said = grounded(draft, "", added=frozenset({"REQ-AUTH-002", "REQ-AUTH-004"}), removed=frozenset())
    text = render_remaining("passkeys", remaining(said, GROUPS, frozenset()))
    assert f"What code found: {UNGROUNDED}. The model's reason: three now." in text
    assert f"What code found: {NO_VERDICT}" in text


def test_a_reason_of_the_models_own_is_never_said_as_codes() -> None:
    """Found by the code review: a model's reason opening as code's did was said as what code found."""
    said = [Verdict("REQ-AUTH-002", "unmet", (), "no quoted line is in the diff for the retry path")]
    text = render_remaining("passkeys", remaining(said, GROUPS, frozenset()))
    assert "The model's reason, which code has not checked: no quoted line is in the diff for the retry path" in text
    # Found by the closing code review: nor one whose words are code's own, word for word.
    said = [
        Verdict("REQ-AUTH-002", "unmet", (), f"{UNGROUNDED}. The retry path is missing"),
        Verdict("REQ-AUTH-004", "unclear", (), NO_VERDICT),
    ]
    assert "What code found" not in render_remaining("passkeys", remaining(said, GROUPS, frozenset()))
