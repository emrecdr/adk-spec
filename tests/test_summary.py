"""What a reviewer of the pull request reads: a summary `verify` writes, and the changelog `archive` keeps."""

from __future__ import annotations

import pytest
from conftest import approved, on_the_fake, run, seeded
from samples import BRIEF, DELTA, tasks_for
from test_review import MENTION
from test_verify import REPORT, approved_in_a_repository, implemented

from adk_spec.domain.brief_md import parse_brief
from adk_spec.domain.changelog_md import changelog_entry, with_entry
from adk_spec.domain.delta_md import parse_delta
from adk_spec.domain.model import Change, ChangeState
from adk_spec.domain.summary_md import render_summary
from adk_spec.workspace.files import read_text, write_text

DELTAS = {"auth": parse_delta(DELTA)}  # adds 004, modifies 002, removes 001
SUMMARY = ".spec/changes/passkeys/reports/summary.md"
CHANGELOG = ".spec/changelog.md"


@pytest.fixture(autouse=True)
def _fake_arm(monkeypatch) -> None:
    on_the_fake(monkeypatch)


def test_the_summary_holds_the_why_the_requirements_and_the_verdicts() -> None:
    change = Change(state=ChangeState(id="passkeys", tier="lean"), brief=parse_brief(BRIEF), deltas=DELTAS, tasks=None)
    text = render_summary(change, {"REQ-AUTH-004": "met", "REQ-AUTH-002": "unmet"}, {".": "passed"}, None)
    assert text.startswith("# Sign in with a passkey\n")
    assert "Passwords are the top source of account takeovers." in text
    assert "- Added REQ-AUTH-004: Sign in with a passkey (auth)" in text
    assert "- Removed REQ-AUTH-001: Sign in with email (auth)" in text
    assert "- REQ-AUTH-002: unmet" in text and "- Tests: passed" in text


def test_verify_writes_the_summary_and_names_it_on_its_one_line(tmp_path, capsys) -> None:
    approved_in_a_repository(tmp_path)
    implemented(tmp_path)
    capsys.readouterr()
    assert run(tmp_path, "verify", "passkeys") == 0
    (wrote,) = [line for line in capsys.readouterr().out.splitlines() if line.startswith("wrote ")]
    assert REPORT in wrote and SUMMARY in wrote
    assert "Approved by reviewer" in read_text(tmp_path / SUMMARY)


def test_archive_writes_a_changelog_entry_newest_first(tmp_path) -> None:
    ws = seeded(tmp_path)
    approved(tmp_path)
    assert run(tmp_path, "archive", "passkeys") == 0, "a lean change is archived without a verification"
    folder = ws.new_change("unlock", "lean")
    write_text(folder / "brief.md", BRIEF)
    write_text(folder / "tasks.md", tasks_for("REQ-AUTH-005"))
    write_text(folder / "specs" / "auth" / "spec.md", MENTION)
    assert run(tmp_path, "approve", "unlock", "--by", "reviewer") == 0
    assert run(tmp_path, "archive", "unlock") == 0
    text = read_text(tmp_path / CHANGELOG)
    assert text.startswith("# Changelog\n") and text.index("## unlock") < text.index("## passkeys")
    assert "- Added REQ-AUTH-005: Unlock by email (auth)" in text


def test_a_persons_edits_below_the_heading_are_kept() -> None:
    before = "# Changelog\n\nA note a person wrote.\n\n## old, 2026-01-01\n\n- Added REQ-X-001: Old (x)\n"
    entry = changelog_entry("passkeys", "2026-11-24", DELTAS)
    after = with_entry(before, entry)
    assert after.startswith("# Changelog\n\nA note a person wrote.\n\n## passkeys, 2026-11-24\n")
    assert after.endswith("\n\n## old, 2026-01-01\n\n- Added REQ-X-001: Old (x)\n")
    assert with_entry(None, entry).startswith("# Changelog\n\n## passkeys, 2026-11-24\n")


def test_a_changelog_that_does_not_read_is_left_and_the_change_archived(tmp_path, capsys) -> None:
    seeded(tmp_path)
    approved(tmp_path)
    (tmp_path / CHANGELOG).write_bytes(b"\xff\xfe not text")
    capsys.readouterr()
    assert run(tmp_path, "archive", "passkeys") == 0
    assert (tmp_path / CHANGELOG).read_bytes() == b"\xff\xfe not text"
    assert f"kept      {CHANGELOG}: " in capsys.readouterr().out


def test_a_heading_of_a_persons_own_is_kept_whole() -> None:
    """Found by the code review: `# Changelog of the API` lost its first two words, and a file opening on a blank line
    got a second heading."""
    entry = changelog_entry("passkeys", "2026-11-24", DELTAS)
    theirs = with_entry("# Changelog of the API\n\n## old, 2026-01-01\n", entry)
    assert theirs.startswith("# Changelog\n\n# Changelog of the API\n\n## passkeys")
    assert with_entry("\n# Changelog\n\n## old, 2026-01-01\n", entry).count("# Changelog") == 1


def test_the_summary_says_an_override_and_its_reason() -> None:
    change = Change(state=ChangeState(id="passkeys", tier="lean"), brief=parse_brief(BRIEF), deltas=DELTAS, tasks=None)
    text = render_summary(change, {"REQ-AUTH-002": "unmet"}, {}, None, override="the judge misread the lockout")
    assert "Verified by override: the judge misread the lockout" in text


def test_a_changelog_that_is_a_link_is_left_and_the_change_archived(tmp_path, capsys) -> None:
    """Found by the code review: a linked changelog stopped the archive, refused by the write's path rules."""
    seeded(tmp_path)
    approved(tmp_path)
    write_text(tmp_path / ".spec/real.md", "# Changelog\n")
    try:
        (tmp_path / CHANGELOG).symlink_to(tmp_path / ".spec/real.md")
    except OSError:
        pytest.skip("no symbolic link can be made here")
    capsys.readouterr()
    assert run(tmp_path, "archive", "passkeys") == 0
    assert (
        f"kept      {CHANGELOG}: " in capsys.readouterr().out
        and read_text(tmp_path / ".spec/real.md") == "# Changelog\n"
    )


def test_a_heading_of_a_persons_introduction_is_no_entry() -> None:
    """Found by the code review: a `## ` heading in a person's introduction was read as the first entry, and the new
    entry split their introduction."""
    intro = "# Changelog\n\nIntro.\n\n## How to read this\n\nText.\n"
    after = with_entry(intro, changelog_entry("passkeys", "2026-11-24", DELTAS))
    assert after.index("Text.") < after.index("## passkeys, 2026-11-24")
