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
