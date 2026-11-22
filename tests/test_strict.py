"""The `strict` tier: a design always owed, `propose` stopping after the brief and the specs for a person to read,
two different approvers, and warnings of the check that block with no override."""

from __future__ import annotations

import io

import pytest
from conftest import BRIEF_WITH_A_MARKER, CANNED_BRIEF, CANNED_TRIAGE, on_the_fake, run, seeded, state_of

from adk_spec.workspace.files import read_text, write_text
from adk_spec.workspace.layout import Workspace

REQUEST = "Move billing to the new ledger, with every invoice kept as it was."
TRIAGE, BRIEF = "You size a change request", "You write the brief of a change"
DESIGN, TASKS = "You write the design of a change", "You break a change into tasks"
FOLDER = ".spec/changes/ledger"


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
    assert sum(str(r.config.system_instruction).startswith(BRIEF) for r in fake_provider.requests) == 2


def test_a_change_that_owes_a_design_and_has_none_is_not_approved_and_plan_is_next(tmp_path, capsys) -> None:
    from adk_spec.domain.lifecycle import next_step
    from adk_spec.domain.validate import validate_change

    ws = seeded(tmp_path)
    ws.save_state(ws.load_change("passkeys").change.state.model_copy(update={"needs_design": True}))
    assert run(tmp_path, "approve", "passkeys", "--by", "ana") != 0
    said = capsys.readouterr()
    assert "ERROR change.missing-design" in said.out and "not approved" in said.err
    change = ws.load_change("passkeys").change
    found = validate_change(change, ws.specs()[0])
    assert next_step(change.state, found, []).phrase == "run `adk-spec plan passkeys`"


def strict_proposed(root, *argv: str, request: str = REQUEST) -> int:
    return run(root, "propose", request, "--tier", "strict", "--id", "ledger", "--no-input", "--no-explore", *argv)


def drafted_by(fake_provider, opening: str) -> int:
    return sum(str(r.config.system_instruction).startswith(opening) for r in fake_provider.requests)


def test_a_strict_propose_stops_after_the_brief_and_the_specs(tmp_path, capsys, fake_provider) -> None:
    seeded(tmp_path)
    capsys.readouterr()
    assert strict_proposed(tmp_path) == 0
    folder = tmp_path / FOLDER
    assert (folder / "brief.md").is_file() and (folder / "specs/auth/spec.md").is_file()
    assert not (folder / "tasks.md").exists() and not (folder / "design.md").exists()
    assert drafted_by(fake_provider, TASKS) == 0 and drafted_by(fake_provider, DESIGN) == 0
    out = capsys.readouterr().out
    assert "plan      waits: a strict change is read first" in out and "run `adk-spec plan ledger`" in out


def test_plan_goes_on_after_the_stop_and_drafts_a_design(tmp_path, fake_provider) -> None:
    seeded(tmp_path)
    assert strict_proposed(tmp_path) == 0
    assert run(tmp_path, "plan", "ledger", "--no-explore") == 0
    folder = tmp_path / FOLDER
    assert (folder / "design.md").is_file() and (folder / "tasks.md").is_file()
    assert drafted_by(fake_provider, DESIGN) == 1


def test_a_strict_revision_stops_before_the_plan_as_a_new_one_does(tmp_path, fake_provider) -> None:
    seeded(tmp_path)
    assert strict_proposed(tmp_path) == 0
    assert run(tmp_path, "propose", "Also keep the old invoice numbers.", "--id", "ledger", "--no-input") == 0
    assert drafted_by(fake_provider, TASKS) == 0


def planned(root) -> None:
    """A strict change, `ledger`, proposed and planned: ready to be approved."""
    seeded(root)
    assert strict_proposed(root) == 0
    assert run(root, "plan", "ledger", "--no-explore") == 0


@pytest.mark.usefixtures("fake_provider")
def test_two_different_names_approve_a_strict_change(tmp_path, capsys) -> None:
    planned(tmp_path)
    capsys.readouterr()
    assert run(tmp_path, "approve", "ledger", "--by", "ana") == 0
    held = state_of(tmp_path, "ledger")
    assert (held["status"], held["approval"]["by"]) == ("draft", "ana")
    out = capsys.readouterr().out
    assert "approved  once, by ana" in out and "have someone other than ana run `adk-spec approve ledger`" in out
    assert run(tmp_path, "approve", "ledger", "--by", "ana") != 0
    assert "another name" in capsys.readouterr().err
    assert run(tmp_path, "approve", "ledger", "--by", "ben") == 0
    held = state_of(tmp_path, "ledger")
    assert (held["status"], held["approval"]["by"], held["approval"]["second"]["by"]) == ("approved", "ana", "ben")
    assert "by ben, after ana" in capsys.readouterr().out


@pytest.mark.usefixtures("fake_provider")
def test_an_edit_between_the_two_approvals_voids_the_first(tmp_path) -> None:
    planned(tmp_path)
    assert run(tmp_path, "approve", "ledger", "--by", "ana") == 0
    brief = tmp_path / FOLDER / "brief.md"
    write_text(brief, read_text(brief).rstrip("\n") + "\n\nAn edit after the first approval.\n")
    assert run(tmp_path, "approve", "ledger", "--by", "ben") == 0
    held = state_of(tmp_path, "ledger")
    assert (held["status"], held["approval"]["by"], held["approval"]["second"]) == ("draft", "ben", None)


@pytest.mark.usefixtures("fake_provider")
def test_a_strict_change_approved_once_is_not_verified(tmp_path, capsys) -> None:
    from conftest import repository

    planned(tmp_path)
    repository(tmp_path)
    assert run(tmp_path, "approve", "ledger", "--by", "ana") == 0
    capsys.readouterr()
    assert run(tmp_path, "verify", "ledger") != 0
    assert "owes a second approval" in capsys.readouterr().err


@pytest.mark.usefixtures("fake_provider")
def test_a_warning_blocks_a_strict_approval_and_no_override_sets_it_aside(tmp_path, capsys) -> None:
    planned(tmp_path)
    tasks = tmp_path / FOLDER / "tasks.md"
    write_text(tasks, "\n".join(line for line in read_text(tasks).splitlines() if "verify:" not in line) + "\n")
    capsys.readouterr()
    assert run(tmp_path, "approve", "ledger", "--by", "ana") != 0
    assert "tasks.no-verify" in capsys.readouterr().out
    assert run(tmp_path, "approve", "ledger", "--by", "ana", "--override", "it is fine") != 0
    assert "a strict change sets no blocking finding aside" in capsys.readouterr().err
    assert state_of(tmp_path, "ledger")["approval"] is None
