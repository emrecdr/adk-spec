"""The approver's view: what a change does to each requirement it touches, and which other open change touches the
same one."""

from __future__ import annotations

import pytest
from conftest import approved, on_the_fake, run, seeded
from samples import DELTA, SPEC, tasks_for

from adk_spec.domain.delta_md import changed_ids, parse_delta
from adk_spec.domain.review_md import render_review
from adk_spec.domain.spec_md import parse_spec
from adk_spec.workspace.files import read_text, write_text

DELTAS = {"auth": parse_delta(DELTA)}  # adds 004, modifies 002, removes 001
LIVING = {"auth": parse_spec(SPEC)}
VIEW = ".spec/changes/passkeys/reports/review.md"

#: Another change that modifies REQ-AUTH-002 too.
OTHER = """\
# Delta: auth

## MODIFIED Requirements

### REQ-AUTH-002: Lock after failures

The system MUST lock an account after ten failed attempts.

#### Scenario: Too many failures

- WHEN a tenth attempt fails
- THEN the account is locked
"""

#: Another change that only mentions REQ-AUTH-002 in what it adds.
MENTION = """\
# Delta: auth

## ADDED Requirements

### REQ-AUTH-005: Unlock by email

The system SHALL unlock an account that REQ-AUTH-002 locked once the user confirms by email.

#### Scenario: Confirmed

- WHEN the user confirms by email
- THEN the account is unlocked
"""


def another(workspace, text: str, change: str = "other"):
    folder = workspace.new_change(change, "lean")
    write_text(folder / "specs" / "auth" / "spec.md", text)
    return folder


def test_a_modified_requirement_is_shown_as_a_diff_of_the_living_one() -> None:
    text = render_review("passkeys", DELTAS, LIVING, {})
    assert "-The system MUST lock an account after five failed attempts." in text
    assert "+The system MUST lock an account after three failed attempts." in text
    assert "### REQ-AUTH-004: Sign in with a passkey" in text
    assert "The system SHALL let a user sign in with a passkey." in text
    assert "REQ-AUTH-001" in text and "Passwords are retired in favour of passkeys." in text
    assert "Also changed" not in text


def test_the_view_names_another_open_change_on_the_same_requirement() -> None:
    text = render_review("passkeys", DELTAS, LIVING, {"REQ-AUTH-002": ["other"]})
    assert "Also changed by open changes" in text and "REQ-AUTH-002: other" in text


def test_another_open_change_modifying_a_requirement_is_named(tmp_path) -> None:
    ws = seeded(tmp_path)
    another(ws, OTHER)
    assert ws.touching("passkeys") == {"REQ-AUTH-002": ["other"]}


def test_a_requirement_only_mentioned_in_another_change_is_no_overlap(tmp_path) -> None:
    ws = seeded(tmp_path)
    another(ws, MENTION)
    assert ws.touching("passkeys") == {}


def test_an_archived_change_is_no_overlap(tmp_path) -> None:
    ws = seeded(tmp_path)
    another(ws, OTHER)
    ws.save_state(ws.state("other").model_copy(update={"status": "archived"}))
    assert ws.touching("passkeys") == {}


@pytest.mark.parametrize("command", [("rebase", "passkeys"), ("check", "passkeys", "--no-model")])
def test_a_command_that_leaves_a_draft_to_be_read_writes_the_view(tmp_path, capsys, command) -> None:
    seeded(tmp_path)
    capsys.readouterr()
    run(tmp_path, *command)
    assert (tmp_path / VIEW).is_file()
    assert f"review    {VIEW}: 1 added, 1 modified, 1 removed" in capsys.readouterr().out


def test_an_approved_change_edited_since_is_given_the_view_again(tmp_path) -> None:
    """Found by the cleanup review: the view was written for a draft alone, and an approved change edited since owes
    an approval as much."""
    seeded(tmp_path)
    approved(tmp_path)
    brief = tmp_path / ".spec/changes/passkeys/brief.md"
    write_text(brief, read_text(brief) + "\nAn edit after the approval.\n")
    run(tmp_path, "check", "passkeys", "--no-model")
    assert (tmp_path / VIEW).is_file()


def test_a_heading_inside_a_fence_is_no_change() -> None:
    fenced = OTHER.replace("### REQ-AUTH-002:", "```\n### REQ-AUTH-002:", 1).replace("ten failed", "ten failed\n```", 1)
    assert changed_ids(OTHER) == ["REQ-AUTH-002"] and changed_ids(fenced) == []


@pytest.mark.usefixtures("fake_provider")
def test_a_proposed_change_gets_its_view(tmp_path, capsys, monkeypatch) -> None:
    on_the_fake(monkeypatch)
    seeded(tmp_path)
    assert run(tmp_path, "propose", "Let users sign in with a passkey.", "--id", "fresh", "--no-input") == 0
    assert (tmp_path / ".spec/changes/fresh/reports/review.md").is_file()
    assert "review    .spec/changes/fresh/reports/review.md" in capsys.readouterr().out


def test_an_approved_change_is_not_given_the_view_again(tmp_path) -> None:
    seeded(tmp_path)
    approved(tmp_path)
    assert not (tmp_path / VIEW).is_file()


def test_approve_notes_another_open_change_on_the_same_requirement(tmp_path, capsys) -> None:
    ws = seeded(tmp_path)
    another(ws, OTHER)
    capsys.readouterr()
    approved(tmp_path)
    (note,) = [line for line in capsys.readouterr().out.splitlines() if line.startswith("note ")]
    assert "REQ-AUTH-002" in note and "other" in note


def test_archive_stopped_by_a_moved_base_names_the_view(tmp_path, capsys) -> None:
    seeded(tmp_path)
    approved(tmp_path)
    write_text(tmp_path / ".spec/specs/auth/spec.md", SPEC.replace("five failed", "seven failed"))
    capsys.readouterr()
    assert run(tmp_path, "archive", "passkeys") == 1
    assert VIEW in capsys.readouterr().err
    assert "-The system MUST lock an account after seven failed attempts." in read_text(tmp_path / VIEW)


def test_a_modified_requirement_the_living_spec_holds_as_it_is_says_so() -> None:
    same = parse_delta(DELTA.replace("three failed attempts", "five failed attempts").replace("a third", "a fifth"))
    living = parse_spec(SPEC.replace("- GIVEN four failed attempts\n", "").replace("- AND the user is told why\n", ""))
    assert "REQ-AUTH-002 is unchanged from the living spec." in render_review(
        "passkeys", {"auth": same}, {"auth": living}, {}
    )


def test_a_view_that_cannot_be_written_does_not_fail_the_command(tmp_path, monkeypatch) -> None:
    """Found by the code review: a finished command ended in exit 3 where `reports/review.md` would not be written."""
    from adk_spec.workspace.layout import Workspace

    seeded(tmp_path)
    writing = Workspace.write_report

    def held(self, change_id, name, text):
        if name == "review.md":
            raise OSError(13, "Permission denied")
        return writing(self, change_id, name, text)

    monkeypatch.setattr(Workspace, "write_report", held)
    assert run(tmp_path, "rebase", "passkeys") == 0


def test_a_change_folder_that_is_a_link_refuses_approve_before_it_records(tmp_path, capsys) -> None:
    """Found by the code review: an open change's folder that is a link stopped `approve` after it was recorded.
    Found by the audit of 25 November: a link under `.spec` is refused when the workspace is opened."""
    ws = seeded(tmp_path)
    elsewhere = another(ws, OTHER).rename(tmp_path / "elsewhere")
    try:
        (tmp_path / ".spec/changes/other").symlink_to(elsewhere, target_is_directory=True)
    except OSError:
        pytest.skip("no symbolic link can be made here")
    recorded = read_text(tmp_path / ".spec/changes/passkeys/change.json")
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer") == 2
    assert "`.spec/changes/other` is a link" in capsys.readouterr().err
    assert read_text(tmp_path / ".spec/changes/passkeys/change.json") == recorded


def test_a_strict_change_approved_once_gives_its_second_approver_a_current_view(
    tmp_path, monkeypatch, fake_provider
) -> None:
    """Found by the code review: approved once, a strict change was not stale, and its second approver read the view
    of the files before the first approver's edit."""
    from test_strict import planned

    on_the_fake(monkeypatch)
    planned(tmp_path, fake_provider)
    delta = tmp_path / ".spec/changes/ledger/specs/auth/spec.md"
    lines = read_text(delta).split("\n")
    at = next(at for at, line in enumerate(lines) if "SHALL" in line)
    lines[at] = f"{lines[at].rstrip()} Edited before the first approval."
    write_text(delta, "\n".join(lines))
    assert run(tmp_path, "approve", "ledger", "--by", "ana") == 0
    assert "Edited before the first approval." in read_text(tmp_path / ".spec/changes/ledger/reports/review.md")


def test_a_strict_change_approved_once_names_its_overlaps_once(tmp_path, capsys, monkeypatch, fake_provider) -> None:
    """Found by the closing code review: the first of two approvals named each overlap twice, on the `note` line and
    again on the `review` line that follows it."""
    from test_strict import planned

    on_the_fake(monkeypatch)
    planned(tmp_path, fake_provider)
    folder = tmp_path / ".spec/changes/ledger"
    write_text(folder / "specs/auth/spec.md", OTHER)  # it modifies what the seeded `passkeys` modifies
    write_text(folder / "tasks.md", tasks_for("REQ-AUTH-002"))
    capsys.readouterr()
    assert run(tmp_path, "approve", "ledger", "--by", "ana") == 0
    out = capsys.readouterr().out
    assert out.count("also changed by") == 1 and "review " in out


def test_check_without_a_model_brings_a_hand_edit_into_the_view_and_the_approval_goes_on(tmp_path) -> None:
    """A command run after a hand edit writes the view again, and a view that shows the specs as they are holds no
    approval back."""
    seeded(tmp_path)
    delta = tmp_path / ".spec/changes/passkeys/specs/auth/spec.md"
    write_text(delta, read_text(delta).replace("three failed attempts", "four failed attempts"))
    assert run(tmp_path, "check", "passkeys", "--no-model") == 0
    assert "+The system MUST lock an account after four failed attempts." in read_text(tmp_path / VIEW)
    approved(tmp_path)


def test_a_new_capabilitys_purpose_is_in_its_view() -> None:
    """Found by the review of the closing fixes: the purpose a new capability's living spec opens on was approved
    unseen."""
    added = DELTA.split("## ADDED Requirements\n\n")[1].split("\n## MODIFIED")[0].replace("AUTH", "SEARCH")
    new = parse_delta("# Delta: search\n\n## Purpose\n\nFind things.\n\n## ADDED Requirements\n\n" + added)
    # In a fence of its own, as a requirement is: found by a review, a purpose opening an HTML comment hid the rest.
    assert "### Purpose\n\n```markdown\nFind things.\n```" in render_review("passkeys", {"search": new}, LIVING, {})


def test_a_removed_requirement_is_shown_as_the_living_spec_holds_it() -> None:
    """Found by a review of the closing fixes: the approver read only a removed requirement's name and reason, and the
    archive took out text they were never shown."""
    assert "The system SHALL let a registered user sign in with email" in render_review("passkeys", DELTAS, LIVING, {})


def test_a_generated_file_is_never_dropped_through_a_link(tmp_path) -> None:
    """Found by the third review of the closing fixes: a change's `reports/` that is a link had a file of its target
    removed, where writing there is refused."""
    ws = seeded(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    write_text(outside / "review.md", "theirs\n")
    reports = tmp_path / ".spec/changes/passkeys/reports"
    if reports.exists():
        import shutil

        shutil.rmtree(reports)
    try:
        reports.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("no symbolic link can be made here")
    ws.drop("passkeys", "reports/review.md")
    assert read_text(outside / "review.md") == "theirs\n"
