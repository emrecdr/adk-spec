"""The next work: what a verification found unmet, written where the coding assistant looks, and the next step that
names it."""

from __future__ import annotations

import json

import pytest
from conftest import on_the_fake, run
from samples import TASKS
from test_lifecycle import approved, phrase
from test_verify import REPORT, VERIFY, approved_in_a_repository, implemented, verdicts

from adk_spec.domain.lifecycle import verified
from adk_spec.domain.remaining import remaining, render_remaining
from adk_spec.domain.tasks_md import parse_tasks
from adk_spec.domain.verify import Verdict

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
    state = verified(approved(), {f"REQ-A-00{n}": "unmet" for n in range(1, 6)}, base="c0", diff="sha256:d", at="t")
    said = phrase(state, [], [])
    assert said.startswith("REQ-A-001, REQ-A-002, REQ-A-003 and 2 more unmet: work from reports/remaining.md")
    assert said.endswith(f"then run `adk-spec verify {state.id}`")


def test_failed_tests_come_before_unmet_requirements() -> None:
    state = verified(approved(), {"REQ-A-001": "unmet"}, base="c0", diff="sha256:d", at="t", tests={".": "failed"})
    assert phrase(state, [], []).startswith("the tests failed")
