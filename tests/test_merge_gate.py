"""The merge gate: `validate` reads whether each change's approval and verification still cover what is merged, and
speaks GitHub's annotations where it runs in GitHub Actions."""

from __future__ import annotations

import json

import pytest
from conftest import on_the_fake, run, seeded, state_of
from test_strict import planned
from test_verify import approved_in_a_repository, implemented

from adk_spec.domain.ci_md import ROWS, annotation_lines, step_summary
from adk_spec.domain.model import Finding
from adk_spec.workspace.files import read_text, write_text

BRIEF = ".spec/changes/passkeys/brief.md"


@pytest.fixture(autouse=True)
def _fake_arm(monkeypatch) -> None:
    on_the_fake(monkeypatch)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)


def validated(root, capsys, *flags: str) -> tuple[int, str]:
    capsys.readouterr()
    code = run(root, "validate", *flags)
    return code, capsys.readouterr().out


def voided(root) -> None:
    """The seeded change approved, then its brief edited."""
    seeded(root)
    assert run(root, "approve", "passkeys", "--by", "reviewer") == 0
    write_text(root / BRIEF, read_text(root / BRIEF) + "\nAn edit after the approval.\n")


def test_a_voided_approval_is_a_warning_that_fails_strict(tmp_path, capsys) -> None:
    seeded(tmp_path)
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer") == 0
    assert validated(tmp_path, capsys, "--strict")[0] == 0
    write_text(tmp_path / BRIEF, read_text(tmp_path / BRIEF) + "\nAn edit after the approval.\n")
    code, out = validated(tmp_path, capsys)
    (void,) = [line for line in out.splitlines() if "change.approval-void" in line]
    assert code == 0 and void.startswith("WARNING") and BRIEF in void and "approve passkeys" in void
    assert validated(tmp_path, capsys, "--strict")[0] == 1


def test_a_voided_strict_approval_can_still_be_approved_again(tmp_path, fake_provider) -> None:
    planned(tmp_path, fake_provider)
    assert run(tmp_path, "approve", "ledger", "--by", "ana") == 0
    assert run(tmp_path, "approve", "ledger", "--by", "ben") == 0
    brief = tmp_path / ".spec/changes/ledger/brief.md"
    write_text(brief, read_text(brief) + "\nAn edit after the approval.\n")
    assert run(tmp_path, "approve", "ledger", "--by", "ana") == 0, "the gate's warning is no blocker of approve"


def test_drifted_work_is_a_warning(tmp_path, capsys) -> None:
    approved_in_a_repository(tmp_path)
    implemented(tmp_path)
    assert run(tmp_path, "verify", "passkeys") == 0
    assert "change.work-drifted" not in validated(tmp_path, capsys)[1]
    write_text(tmp_path / "src/auth.py", read_text(tmp_path / "src/auth.py") + "\n# a later edit\n")
    (drift,) = [line for line in validated(tmp_path, capsys)[1].splitlines() if "change.work-drifted" in line]
    assert drift.startswith("WARNING") and "verify passkeys" in drift


def test_work_that_cannot_be_compared_is_a_note_and_archive_still_refuses(tmp_path, capsys) -> None:
    approved_in_a_repository(tmp_path)
    implemented(tmp_path)
    assert run(tmp_path, "verify", "passkeys") == 0
    held = state_of(tmp_path)
    held["verification"]["base"] = "0" * 40  # a commit this clone does not hold, as a shallow one does not
    write_text(tmp_path / ".spec/changes/passkeys/change.json", json.dumps(held, indent=2))
    (unknown,) = [line for line in validated(tmp_path, capsys)[1].splitlines() if "change.drift-unknown" in line]
    assert unknown.startswith("INFO")
    assert run(tmp_path, "archive", "passkeys") == 1


def test_github_actions_gets_annotations_and_a_summary(tmp_path, capsys, monkeypatch) -> None:
    voided(tmp_path)
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    code, out = validated(tmp_path, capsys)
    assert code == 0 and f"::warning file={BRIEF},title=change.approval-void::" in out
    assert "| WARNING | change.approval-void |" in read_text(summary)


def test_annotations_escape_what_github_reads_as_syntax() -> None:
    held = Finding(severity="ERROR", code="x.y", message="50% done\nnext", path="a,b:c.md", line=3)
    assert annotation_lines([held]) == ["::error file=a%2Cb%3Ac.md,line=3,title=x.y::50%25 done%0Anext"]
    assert annotation_lines([held.model_copy(update={"path": None})]) == []


def test_the_summary_is_capped() -> None:
    many = [Finding(severity="INFO", code="x", message=f"m {n} | piped", path="p.md") for n in range(ROWS + 10)]
    text = step_summary(many, failed=False)
    assert ROWS == 50 and text.count("| INFO | x |") == 50 and "and 10 more" in text and "m 0 \\| piped" in text


def test_no_summary_file_still_annotates(tmp_path, capsys, monkeypatch) -> None:
    voided(tmp_path)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    code, out = validated(tmp_path, capsys)
    assert code == 0 and "::warning " in out
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "missing" / "summary.md"))
    code, out = validated(tmp_path, capsys)
    assert code == 0 and "::warning " in out and not (tmp_path / "missing").exists()


def test_nothing_github_is_said_outside_github_actions(tmp_path, capsys) -> None:
    voided(tmp_path)
    assert "::" not in validated(tmp_path, capsys)[1]


def test_json_output_is_unchanged_by_github_actions(tmp_path, capsys, monkeypatch) -> None:
    voided(tmp_path)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    found = json.loads(validated(tmp_path, capsys, "--json")[1])["findings"]
    assert "change.approval-void" in {held["code"] for held in found}
