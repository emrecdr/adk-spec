"""The `strict` tier: a design always owed, `propose` stopping after the brief and the specs for a person to read,
two different approvers, and warnings of the check that block with no override."""

from __future__ import annotations

import io

import pytest
from conftest import (
    BRIEF_WITH_A_MARKER,
    CANNED_BRIEF,
    CANNED_TRIAGE,
    asked,
    on_the_fake,
    repository,
    run,
    seeded,
    state_of,
)

from adk_spec.workspace.files import read_text, write_text
from adk_spec.workspace.layout import Workspace

REQUEST = "Move billing to the new ledger, with every invoice kept as it was."
TRIAGE, BRIEF = "You size a change request", "You write the brief of a change"
DESIGN, TASKS = "You write the design of a change", "You break a change into tasks"
FOLDER = ".spec/changes/ledger"
CHECK = "You review the files of a change against each other"


@pytest.fixture(autouse=True)
def _fake_arm(monkeypatch) -> None:
    on_the_fake(monkeypatch)


def test_new_takes_the_strict_tier_and_it_owes_a_design(tmp_path) -> None:
    Workspace.init(tmp_path)
    assert run(tmp_path, "new", "ledger", "--tier", "strict") == 0
    held = state_of(tmp_path, "ledger")
    assert (held["tier"], held["needs_design"]) == ("strict", True)


def test_the_config_may_name_strict_as_the_default_tier(tmp_path) -> None:
    ws = Workspace.init(tmp_path)
    config = ws.home / "config.toml"
    write_text(config, read_text(config).replace('default_tier = "standard"', 'default_tier = "strict"'))
    assert run(tmp_path, "new", "ledger") == 0 and state_of(tmp_path, "ledger")["tier"] == "strict"


def test_the_sizing_models_strict_is_taken_as_it_is(tmp_path, fake_provider) -> None:
    seeded(tmp_path)
    fake_provider.answers_when(TRIAGE, {**CANNED_TRIAGE, "tier": "strict"})
    assert run(tmp_path, "propose", REQUEST, "--id", "ledger", "--no-input", "--no-explore") == 0
    held = state_of(tmp_path, "ledger")
    assert (held["tier"], held["needs_design"]) == ("strict", True)


def test_a_strict_brief_with_an_open_point_is_asked_as_a_standard_one_is(tmp_path, monkeypatch, fake_provider) -> None:
    seeded(tmp_path)
    fake_provider.answers_each_time(BRIEF, iter([BRIEF_WITH_A_MARKER, CANNED_BRIEF]))
    monkeypatch.setattr("sys.stdin", io.StringIO("Chrome and Firefox\n"))
    assert run(tmp_path, "propose", REQUEST, "--tier", "strict", "--id", "asked", "--no-explore") == 0
    assert asked(fake_provider, BRIEF) == 2


def test_a_change_that_owes_a_design_and_has_none_is_not_approved_and_plan_is_next(tmp_path, capsys) -> None:
    from adk_spec.domain.lifecycle import next_step
    from adk_spec.domain.validate import validate_change

    ws = seeded(tmp_path)
    ws.save_state(ws.load_change("passkeys").change.state.model_copy(update={"needs_design": True}))
    assert run(tmp_path, "approve", "passkeys", "--by", "ana") != 0
    said = capsys.readouterr()
    assert "WARNING change.missing-design" in said.out and "not approved" in said.err
    change = ws.load_change("passkeys").change
    found = validate_change(change, ws.specs()[0])
    assert next_step(change.state, found, []).phrase == "run `adk-spec plan passkeys`"


def strict_proposed(root, *argv: str, request: str = REQUEST) -> int:
    return run(root, "propose", request, "--tier", "strict", "--id", "ledger", "--no-input", "--no-explore", *argv)


def test_a_strict_propose_stops_after_the_brief_and_the_specs(tmp_path, capsys, fake_provider) -> None:
    seeded(tmp_path)
    capsys.readouterr()
    assert strict_proposed(tmp_path) == 0
    folder = tmp_path / FOLDER
    assert (folder / "brief.md").is_file() and (folder / "specs/auth/spec.md").is_file()
    assert not (folder / "tasks.md").exists() and not (folder / "design.md").exists()
    assert asked(fake_provider, TASKS) == 0 and asked(fake_provider, DESIGN) == 0
    out = capsys.readouterr().out
    assert "plan      waits: the change is read before it is planned" in out
    # Found by the cleanup review: the sentence was said twice, and the `next` line dropped the command's flags.
    assert "next      read brief.md and the specs, then run `adk-spec plan ledger" in out
    assert out.count("read brief.md and the specs") == 1


def test_plan_goes_on_after_the_stop_and_drafts_a_design(tmp_path, fake_provider) -> None:
    seeded(tmp_path)
    assert strict_proposed(tmp_path) == 0
    assert run(tmp_path, "plan", "ledger", "--no-explore") == 0
    folder = tmp_path / FOLDER
    assert (folder / "design.md").is_file() and (folder / "tasks.md").is_file()
    assert asked(fake_provider, DESIGN) == 1


def test_a_strict_revision_stops_before_the_plan_as_a_new_one_does(tmp_path, fake_provider) -> None:
    seeded(tmp_path)
    assert strict_proposed(tmp_path) == 0
    assert run(tmp_path, "propose", "Also keep the old invoice numbers.", "--id", "ledger", "--no-input") == 0
    assert asked(fake_provider, TASKS) == 0


def planned(root, fake_provider) -> None:
    """A strict change, `ledger`, proposed and planned: ready to be approved, its check finding nothing."""
    fake_provider.answers_if_asked(CHECK, {"findings": []})  # an approval that stops first asks no check
    seeded(root)
    assert strict_proposed(root) == 0
    assert run(root, "plan", "ledger", "--no-explore") == 0


def test_two_different_names_approve_a_strict_change(tmp_path, capsys, fake_provider) -> None:
    planned(tmp_path, fake_provider)
    capsys.readouterr()
    assert run(tmp_path, "approve", "ledger", "--by", "ana") == 0
    held = state_of(tmp_path, "ledger")
    assert (held["status"], held["approval"]["by"]) == ("draft", "ana")
    out = capsys.readouterr().out
    assert (
        "approved `ledger` once, by ana" in out and "have someone other than ana run `adk-spec approve ledger`" in out
    )
    assert run(tmp_path, "approve", "ledger", "--by", "ana") != 0
    assert "another name" in capsys.readouterr().err
    assert run(tmp_path, "approve", "ledger", "--by", "ben") == 0
    held = state_of(tmp_path, "ledger")
    assert (held["status"], held["approval"]["by"], held["approval"]["second"]["by"]) == ("approved", "ana", "ben")
    assert "approved `ledger` by ben, after ana" in capsys.readouterr().out


def test_an_edit_between_the_two_approvals_voids_the_first(tmp_path, fake_provider) -> None:
    planned(tmp_path, fake_provider)
    assert run(tmp_path, "approve", "ledger", "--by", "ana") == 0
    brief = tmp_path / FOLDER / "brief.md"
    write_text(brief, read_text(brief).rstrip("\n") + "\n\nAn edit after the first approval.\n")
    assert run(tmp_path, "approve", "ledger", "--by", "ben") == 0
    held = state_of(tmp_path, "ledger")
    assert (held["status"], held["approval"]["by"], held["approval"]["second"]) == ("draft", "ben", None)


def test_a_strict_change_approved_once_is_not_verified(tmp_path, capsys, fake_provider) -> None:
    planned(tmp_path, fake_provider)
    repository(tmp_path)
    assert run(tmp_path, "approve", "ledger", "--by", "ana") == 0
    capsys.readouterr()
    assert run(tmp_path, "verify", "ledger") != 0
    assert "owes a second approval" in capsys.readouterr().err


def test_a_warning_blocks_a_strict_approval_and_no_override_sets_it_aside(tmp_path, capsys, fake_provider) -> None:
    planned(tmp_path, fake_provider)
    tasks = tmp_path / FOLDER / "tasks.md"
    write_text(tasks, "\n".join(line for line in read_text(tasks).splitlines() if "verify:" not in line) + "\n")
    capsys.readouterr()
    assert run(tmp_path, "approve", "ledger", "--by", "ana") != 0
    assert "tasks.no-verify" in capsys.readouterr().out
    assert run(tmp_path, "approve", "ledger", "--by", "ana", "--override", "it is fine") != 0
    assert "a strict change sets no blocking finding aside" in capsys.readouterr().err
    assert state_of(tmp_path, "ledger")["approval"] is None


def test_one_name_reapproving_an_edited_strict_change_leaves_it_a_draft(tmp_path, fake_provider) -> None:
    """Found by the cleanup review: approved by two, edited, then approved by one, it stayed approved."""
    planned(tmp_path, fake_provider)
    assert run(tmp_path, "approve", "ledger", "--by", "ana") == 0
    assert run(tmp_path, "approve", "ledger", "--by", "ben") == 0
    brief = tmp_path / FOLDER / "brief.md"
    write_text(brief, read_text(brief).rstrip("\n") + "\n\nAn edit after both approvals.\n")
    assert run(tmp_path, "approve", "ledger", "--by", "ana") == 0
    held = state_of(tmp_path, "ledger")
    assert (held["status"], held["approval"]["by"], held["approval"]["second"]) == ("draft", "ana", None)


def test_the_domain_never_takes_one_name_for_both_approvals() -> None:
    """Found by the cleanup review: only the command refused the same name twice."""
    from adk_spec.domain.lifecycle import approve
    from adk_spec.domain.model import ChangeState

    files = {"brief.md": "a"}
    once = approve(ChangeState(id="c", tier="strict"), files=files, by="ana", at="1")
    twice = approve(once, files=files, by="ana", at="2")
    assert (twice.status, twice.approval.by, twice.approval.second) == ("draft", "ana", None)


def test_a_strict_warning_is_said_to_block_and_a_warning_of_the_check_blocks_too() -> None:
    """Found by the cleanup review: the next line said to approve a strict change a warning blocks, and a warning
    the model's check found counted for nothing."""
    from adk_spec.domain.lifecycle import check_blockers, checked, next_step
    from adk_spec.domain.model import ChangeState, Finding

    warning = Finding(severity="WARNING", code="tasks.no-verify", message="T001 has no `verify` line. Say how.")
    state = ChangeState(id="c", tier="strict")
    assert next_step(state, [warning], ["approval"]).phrase == "fix what `adk-spec validate c` lists"
    after = checked(state, [warning], files={"brief.md": "a"}, at="1", model="m")
    assert after.check.blocking == 1
    (owed,) = check_blockers(after, {"brief.md": "a"})
    assert "--override" not in owed.message


@pytest.mark.usefixtures("fake_provider")
def test_the_stop_names_plan_with_no_explore_where_the_person_gave_it(tmp_path, capsys) -> None:
    seeded(tmp_path)
    capsys.readouterr()
    assert strict_proposed(tmp_path) == 0
    assert "then run `adk-spec plan ledger --no-explore`" in capsys.readouterr().out


def test_approving_again_a_strict_change_two_names_approved_changes_nothing(tmp_path, capsys, fake_provider) -> None:
    """Found by the review: a third name approving unchanged files dropped it back to a draft, the second lost."""
    planned(tmp_path, fake_provider)
    assert run(tmp_path, "approve", "ledger", "--by", "ana") == 0
    assert run(tmp_path, "approve", "ledger", "--by", "ben") == 0
    before = state_of(tmp_path, "ledger")
    capsys.readouterr()
    assert run(tmp_path, "approve", "ledger", "--by", "carl") != 0
    assert "approved already, by ana and ben" in capsys.readouterr().err
    assert state_of(tmp_path, "ledger") == before


def test_one_person_is_one_name_whatever_its_case(tmp_path, capsys, fake_provider) -> None:
    planned(tmp_path, fake_provider)
    assert run(tmp_path, "approve", "ledger", "--by", "ana") == 0
    capsys.readouterr()
    assert run(tmp_path, "approve", "ledger", "--by", " Ana ") != 0
    assert state_of(tmp_path, "ledger")["status"] == "draft"


def test_an_open_point_or_an_error_comes_before_the_design_a_plan_drafts() -> None:
    """Found by the review: a design owed and missing came first, and hid what `plan` cannot settle."""
    from adk_spec.domain.lifecycle import next_step
    from adk_spec.domain.model import ChangeState, Finding

    def held(code: str, severity: str = "WARNING") -> Finding:
        return Finding(severity=severity, code=code, message="A finding long enough to say something here.")

    state = ChangeState(id="c", tier="strict", needs_design=True)
    design = held("change.missing-design")
    settled = next_step(state, [design, held("brief.marker-unresolved")], []).phrase
    read_first = "read brief.md and the specs, then run `adk-spec plan c`"
    assert settled == f"settle the open point in brief.md, then {read_first}"
    assert next_step(state, [design, held("delta.empty", "ERROR")], []).phrase == "fix what `adk-spec validate c` lists"
    assert next_step(state, [design], []).phrase == "read brief.md and the specs, then run `adk-spec plan c`"


def test_a_strict_check_report_counts_a_warning_as_blocking() -> None:
    """Found by the review: the report said nothing blocks, and the approval it pointed to refused."""
    from adk_spec.domain.model import Finding
    from adk_spec.domain.report_md import render_check

    warning = Finding(severity="WARNING", code="check.ambiguity", message="Which browsers are in scope is not said.")
    report = render_check("c", "t", [warning], model="m", warnings_block=True)
    assert "1 blocking." in report and report.index("## Blocking") < report.index("Which browsers")
    assert "Nothing blocks" in render_check("c", "t", [warning], model="m")


def test_plan_keeps_a_design_a_person_wrote_on_a_strict_change(tmp_path, fake_provider) -> None:
    """Found by the review: `plan` wrote its own design over the one a person wrote for a strict change."""
    from samples import BRIEF, DELTA

    seeded(tmp_path)
    assert run(tmp_path, "new", "ledger", "--tier", "strict") == 0
    folder = tmp_path / FOLDER
    write_text(folder / "brief.md", BRIEF)
    write_text(folder / "specs/auth/spec.md", DELTA)
    mine = "# Design\n\n## Context\n\nWritten by hand.\n"
    write_text(folder / "design.md", mine)
    assert run(tmp_path, "plan", "ledger", "--no-explore") == 0
    assert (folder / "tasks.md").is_file(), "the plan was drafted"
    assert read_text(folder / "design.md") == mine and asked(fake_provider, DESIGN) == 0


def test_an_approved_strict_change_revised_as_it_stands_names_the_step_that_changes_it(
    tmp_path, capsys, fake_provider
) -> None:
    """Found by the code review: revised as it stood, an approved strict change was said to wait for a plan, which
    refuses an approved change, beside a next line to implement it; and its kept line named no step."""
    planned(tmp_path, fake_provider)
    assert run(tmp_path, "approve", "ledger", "--by", "ana") == 0
    assert run(tmp_path, "approve", "ledger", "--by", "ben") == 0
    tasks = tmp_path / FOLDER / "tasks.md"
    write_text(tasks, read_text(tasks).replace("- [ ]", "- [x]", 1))
    capsys.readouterr()
    assert run(tmp_path, "propose", "Keep it as it is.", "--id", "ledger", "--no-input") == 0
    out = capsys.readouterr().out
    assert state_of(tmp_path, "ledger")["status"] == "approved" and "plan      waits" not in out
    step = "a task is ticked: to change it, edit tasks.md, then run `adk-spec approve ledger` again"
    assert f"kept      tasks.md: {step}" in out


def test_a_strict_revision_with_a_ticked_task_names_the_plan_that_goes_on(tmp_path, capsys, fake_provider) -> None:
    """Found by the review: the stop named a `plan` that a ticked task refuses, and one that reads the code."""
    planned(tmp_path, fake_provider)
    tasks = tmp_path / FOLDER / "tasks.md"
    write_text(tasks, read_text(tasks).replace("- [ ]", "- [x]", 1))
    capsys.readouterr()
    assert run(tmp_path, "propose", "Also keep the old invoice numbers.", "--id", "ledger", "--no-input") == 0
    out = capsys.readouterr().out
    assert "kept      tasks.md: a task is ticked. `adk-spec plan ledger --replace" in out
    # Found by the code review: the next line named `plan --replace`, which throws ticked work away, where `status`
    # named another step.
    (step,) = [line for line in out.splitlines() if line.startswith("next ")]
    assert "--replace" not in step
