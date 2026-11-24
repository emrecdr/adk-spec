"""What code says of a change's files against each other, with no model: which requirement no task serves, and
which task names a requirement nothing holds."""

from __future__ import annotations

import pytest
from conftest import CANNED_FINDINGS, on_the_fake, run, seeded
from samples import BRIEF, DELTA, SPEC, TASKS

from adk_spec.domain.check import coverage, coverage_of, nameable, owed
from adk_spec.domain.convert import to_findings
from adk_spec.domain.delta_md import parse_delta
from adk_spec.domain.drafts import FindingsDraft
from adk_spec.domain.lifecycle import approval_files
from adk_spec.domain.spec_md import parse_spec
from adk_spec.domain.tasks_md import parse_tasks
from adk_spec.domain.validate import validate_delta
from adk_spec.workspace.files import read_text, write_text
from adk_spec.workspace.layout import Workspace, findings_of
from adk_spec.workspace.runs import listed, read

DELTAS = {"auth": parse_delta(DELTA)}  # adds 004, modifies 002, removes 001
LIVING = {"auth": parse_spec(SPEC)}  # holds 001 and 002, has retired 003
ALL = nameable(DELTAS, LIVING)


def test_a_change_owes_a_task_for_what_it_adds_and_what_it_modifies() -> None:
    assert owed(DELTAS) == {"REQ-AUTH-004", "REQ-AUTH-002"}
    may = nameable(DELTAS, LIVING)
    assert may == {"REQ-AUTH-004", "REQ-AUTH-002", "REQ-AUTH-001"}, "a task may name what the change removes too"


def test_the_sample_task_list_covers_the_sample_delta() -> None:
    assert coverage(parse_tasks(TASKS), owed=owed(DELTAS), nameable=ALL) == []


def test_a_requirement_no_task_names_is_found() -> None:
    wanted = frozenset({"REQ-AUTH-004", "REQ-AUTH-002", "REQ-AUTH-009"})
    found = coverage(parse_tasks(TASKS), owed=wanted, nameable=ALL | wanted)
    assert [(f.code, f.severity) for f in found] == [("check.requirement-no-task", "ERROR")]
    assert "REQ-AUTH-009" in found[0].message


def test_a_task_naming_an_id_nothing_holds_is_found() -> None:
    found = coverage(parse_tasks(TASKS), owed=frozenset(), nameable=frozenset({"REQ-AUTH-004"}))
    assert [(f.code, f.severity) for f in found] == [("check.task-unknown-requirement", "ERROR")]
    assert "T002" in found[0].message and "REQ-AUTH-002" in found[0].message


def test_a_change_with_no_task_yet_owes_no_coverage(tmp_path) -> None:
    ws = seeded(tmp_path)
    (tmp_path / ".spec/changes/passkeys/tasks.md").unlink()
    loaded = ws.load_change("passkeys")
    assert coverage_of(loaded.change, ws.specs()[0]) == []
    assert [f.code for f in findings_of(loaded, ws.specs()[0]) if f.path == "tasks.md"] == ["change.missing-tasks"]


def test_every_command_that_reads_a_change_sees_its_coverage(tmp_path) -> None:
    ws = seeded(tmp_path)
    delta = tmp_path / ".spec/changes/passkeys/specs/auth/spec.md"
    more = (
        "### REQ-AUTH-005: Sign out everywhere\n\nThe system SHALL end every session of a user on request.\n\n"
        "#### Scenario: Asked\n\n- WHEN the user asks to sign out everywhere\n- THEN every session ends\n\n"
    )
    write_text(delta, read_text(delta).replace("## MODIFIED Requirements\n", more + "## MODIFIED Requirements\n"))
    found = [f for f in findings_of(ws.load_change("passkeys"), ws.specs()[0]) if f.code.startswith("check.")]
    assert [(f.code, f.path) for f in found] == [("check.requirement-no-task", "tasks.md")]
    assert "REQ-AUTH-005" in found[0].message


def test_a_modified_requirement_that_did_not_change_is_a_warning() -> None:
    living = LIVING["auth"]
    same = parse_delta(DELTA).model_copy(update={"modified": (living.requirements[1],), "added": (), "removed": ()})
    found = validate_delta(same, living, {})
    assert ("delta.modified-unchanged", "WARNING") in [(f.code, f.severity) for f in found]
    assert not any(f.code == "delta.modified-unchanged" for f in validate_delta(DELTAS["auth"], living, {}))


# The model's pass, and the command.

CHECK = "You review the files of a change"
REAL = {
    "kind": "contradiction",
    "severity": "critical",
    "file": "brief.md",
    "quote": "the top source of account takeovers",
    "message": "The delta keeps password sign-in.",
}
REPORT = ".spec/changes/passkeys/reports/check.md"


@pytest.fixture(autouse=True)
def _fake_arm(monkeypatch) -> None:
    on_the_fake(monkeypatch)


def standard(root) -> Workspace:
    """The seeded change as a standard one: what owes a check before approval."""
    ws = seeded(root)
    ws.save_state(ws.load_change("passkeys").change.state.model_copy(update={"tier": "standard"}))
    return ws


def state(ws: Workspace):
    return ws.load_change("passkeys").change.state


def test_a_finding_is_kept_only_where_its_quote_is_in_the_file() -> None:
    texts = {"brief.md": BRIEF, "specs/auth/spec.md": DELTA}
    invented = {**REAL, "quote": "Passwords are never used here"}
    elsewhere = {**REAL, "file": "tasks.md"}
    short = {**REAL, "quote": "the top"}
    draft = FindingsDraft.model_validate({"findings": [REAL, invented, elsewhere, short]})
    kept, dropped = to_findings(draft, texts)
    assert [(f.code, f.severity, f.path, f.line) for f in kept] == [("check.contradiction", "ERROR", "brief.md", 5)]
    assert dropped == 3 and kept[0].message == "The delta keeps password sign-in."


def test_a_quote_is_found_across_a_line_break_and_stray_spaces() -> None:
    quote = "WHEN the user presents a registered passkey\n   - THEN the system   starts a session"
    wrapped = {**REAL, "kind": "ambiguity", "severity": "note", "file": "specs/auth/spec.md", "quote": quote}
    kept, dropped = to_findings(FindingsDraft.model_validate({"findings": [wrapped]}), {"specs/auth/spec.md": DELTA})
    assert dropped == 0 and [(f.code, f.severity, f.line) for f in kept] == [("check.ambiguity", "INFO", 11)]


def test_check_writes_a_report_and_records_what_it_read(tmp_path, capsys, fake_provider) -> None:
    ws = standard(tmp_path)
    capsys.readouterr()
    assert run(tmp_path, "check", "passkeys") == 0
    held = state(ws).check
    assert (held.blocking, held.model) == (0, "fake on gemini")
    files = approval_files(ws.approval_texts("passkeys"))
    assert files.items() <= held.files.items(), "the change's own files, and beside them what else the check read"
    report = read_text(tmp_path / REPORT)
    assert "check.ambiguity" in report and "brief.md:25" in report and "Which browsers are in scope" in report
    out = capsys.readouterr().out
    assert REPORT in out and "check 120 in 1 call: 120 total" in out and "approve passkeys" in out
    sent = str(fake_provider.requests[0].config.system_instruction)
    assert "=== brief.md\n# Sign in with a passkey" in sent and "=== specs/auth/spec.md\n# Delta: auth" in sent
    assert read(listed(ws)[0]).command == "check"


def test_a_critical_finding_blocks_approval_until_it_is_fixed_or_overridden(tmp_path, capsys, fake_provider) -> None:
    ws = standard(tmp_path)
    fake_provider.answers_when(CHECK, {"findings": [REAL]})
    assert run(tmp_path, "check", "passkeys") == 1 and state(ws).check.blocking == 1
    capsys.readouterr()
    assert run(tmp_path, "status") == 0 and "reports/check.md" in capsys.readouterr().out
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer") == 1
    assert "check.blocking" in capsys.readouterr().out
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer", "--override", "the delta is right") == 0
    approval = state(ws).approval
    assert approval.override == "the delta is right" and state(ws).status == "approved"


def test_approve_checks_again_after_an_edit(tmp_path, capsys, fake_provider) -> None:
    """An edit makes a check stale. A person no longer has to run `check` again before `approve`: the approval
    makes the check it needs, of the files as they now stand."""
    ws = standard(tmp_path)
    assert run(tmp_path, "check", "passkeys") == 0
    brief = tmp_path / ".spec/changes/passkeys/brief.md"
    write_text(brief, read_text(brief).replace("No change to session length.", "No change to sessions."))
    capsys.readouterr()
    assert run(tmp_path, "status") == 0 and "run `adk-spec approve passkeys`" in capsys.readouterr().out
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer") == 0
    assert len(fake_provider.requests) == 2 and state(ws).status == "approved"
    assert state(ws).approval.files.items() <= state(ws).check.files.items(), "what was approved is what was checked"


def test_approve_makes_the_check_a_standard_change_owes(tmp_path, capsys, fake_provider) -> None:
    """The simple flow: `check` was a command a person ran only because `approve` asked for it."""
    import re

    ws = standard(tmp_path)
    capsys.readouterr()
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer") == 0
    out = capsys.readouterr().out
    assert len(fake_provider.requests) == 1 and state(ws).status == "approved" and state(ws).check.blocking == 0
    assert re.search(rf"checked   {re.escape(REPORT)}: \d+ findings?, 0 blocking", out)
    assert "approved `passkeys` by reviewer" in out and "tokens    check 120 in 1 call: 120 total" in out
    assert "next      implement tasks.md, then run `adk-spec verify passkeys`" in out
    assert "check.ambiguity" in read_text(tmp_path / REPORT), "the report is written as `check` writes it"


def test_a_current_check_is_not_made_again(tmp_path, capsys, fake_provider) -> None:
    standard(tmp_path)
    assert run(tmp_path, "check", "passkeys") == 0
    capsys.readouterr()
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer") == 0
    out = capsys.readouterr().out
    assert len(fake_provider.requests) == 1 and "checked   " not in out and "tokens" not in out


def test_a_lean_change_is_approved_with_no_check_and_no_model(tmp_path, fake_provider) -> None:
    ws = seeded(tmp_path)
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer") == 0
    assert fake_provider.requests == [] and state(ws).check is None


def test_a_blocking_finding_of_its_own_check_stops_the_approval(tmp_path, capsys, fake_provider) -> None:
    ws = standard(tmp_path)
    fake_provider.answers_when(CHECK, {"findings": [REAL]})
    capsys.readouterr()
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer") == 1
    said = capsys.readouterr()
    assert "check.contradiction" in said.out and "The delta keeps password sign-in." in said.out
    assert "1 blocking" in said.out and "is not approved" in said.err and REPORT in said.out
    assert state(ws).approval is None and state(ws).check.blocking == 1, "the check is recorded, the approval is not"


def test_an_override_does_not_reach_a_check_made_in_the_same_run(tmp_path, capsys, fake_provider) -> None:
    """A person cannot set aside a finding they have not been shown: `--override` typed on the run that makes the
    check is not applied. Typed again, once the finding has been printed, it is."""
    ws = standard(tmp_path)
    fake_provider.answers_when(CHECK, {"findings": [REAL]})
    capsys.readouterr()
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer", "--override", "no time") == 1
    said = capsys.readouterr()
    assert "check.contradiction" in said.out and state(ws).approval is None
    assert "--override was not applied" in said.err and "read what it found" in said.err
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer", "--override", "the delta is right") == 0
    assert state(ws).approval.override == "the delta is right" and len(fake_provider.requests) == 1


def test_approve_with_no_provider_says_so_and_names_the_way_without_one(tmp_path, monkeypatch, capsys) -> None:
    ws = standard(tmp_path)
    monkeypatch.delenv("GOOGLE_API_KEY")
    capsys.readouterr()
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer") == 2
    err = capsys.readouterr().err
    assert "GOOGLE_API_KEY" in err and "adk-spec check passkeys --no-model" in err
    assert state(ws).check is None and state(ws).approval is None


def test_approve_with_no_provider_names_no_way_a_models_finding_refuses(
    tmp_path, monkeypatch, capsys, fake_provider
) -> None:
    """Found by the code review: with a model's blocking check stale and no provider, `approve` named
    `check --no-model`, which refuses to clear what a model found, and the person went round in a loop."""
    standard(tmp_path)
    fake_provider.answers_when(CHECK, {"findings": [REAL]})
    assert run(tmp_path, "check", "passkeys") == 1
    brief = tmp_path / ".spec/changes/passkeys/brief.md"
    write_text(brief, read_text(brief) + "\nOne word more.\n")
    monkeypatch.delenv("GOOGLE_API_KEY")
    capsys.readouterr()
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer") == 2
    err = capsys.readouterr().err
    assert "--no-model" not in err and "only a model clears" in err


def test_approve_calls_no_model_where_a_file_does_not_read(tmp_path, capsys, fake_provider) -> None:
    ws = standard(tmp_path)
    delta = tmp_path / ".spec/changes/passkeys/specs/auth/spec.md"
    write_text(delta, read_text(delta).replace("### REQ-AUTH-002", "### REQ-AUTH-099"))
    capsys.readouterr()
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer") == 1
    said = capsys.readouterr()
    assert "delta.target-missing" in said.out and "check.missing" not in said.out, (
        "what it will make itself is no finding"
    )
    assert fake_provider.requests == [] and state(ws).check is None and state(ws).approval is None


def test_a_check_that_does_not_finish_approves_nothing(tmp_path, capsys, fake_provider) -> None:
    ws = standard(tmp_path)
    fake_provider.raises_when(CHECK, RuntimeError("the provider fell over"))
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer") == 3
    assert "the provider fell over" in capsys.readouterr().err
    assert state(ws).check is None and state(ws).approval is None and not (tmp_path / REPORT).exists()


def test_no_model_runs_the_codes_passes_alone(tmp_path, fake_provider) -> None:
    ws = standard(tmp_path)
    assert run(tmp_path, "check", "passkeys", "--no-model") == 0
    assert fake_provider.requests == [] and state(ws).check.model is None
    assert "by code alone" in read_text(tmp_path / REPORT)
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer") == 0


def test_a_failed_pass_records_no_check_and_writes_no_report(tmp_path, capsys, fake_provider) -> None:
    ws = standard(tmp_path)
    fake_provider.raises_when(CHECK, RuntimeError("the provider fell over"))
    assert run(tmp_path, "check", "passkeys") == 3
    assert "the provider fell over" in capsys.readouterr().err
    assert state(ws).check is None and not (tmp_path / REPORT).exists()


def test_an_error_of_structure_is_reported_and_the_model_is_not_asked(tmp_path, capsys, fake_provider) -> None:
    ws = standard(tmp_path)
    delta = tmp_path / ".spec/changes/passkeys/specs/auth/spec.md"
    write_text(delta, read_text(delta).replace("### REQ-AUTH-002", "### REQ-AUTH-099"))
    assert run(tmp_path, "check", "passkeys") == 1
    assert fake_provider.requests == [] and state(ws).check.blocking >= 1
    assert "delta.target-missing" in read_text(tmp_path / REPORT)
    assert "fix what the check lists first" in capsys.readouterr().err


def test_a_finding_whose_quote_is_nowhere_is_left_out_and_counted(tmp_path, capsys, fake_provider) -> None:
    ws = standard(tmp_path)
    invented = {**REAL, "quote": "Passwords are never used here"}
    fake_provider.answers_when(CHECK, {"findings": [invented, CANNED_FINDINGS["findings"][0]]})
    assert run(tmp_path, "check", "passkeys") == 0 and state(ws).check.blocking == 0
    assert "1 finding of the model was left out" in capsys.readouterr().out
    report = read_text(tmp_path / REPORT)
    assert "check.contradiction" not in report and "left out" in report


def test_a_report_is_no_part_of_an_approval(tmp_path, capsys, fake_provider) -> None:
    ws = standard(tmp_path)
    assert run(tmp_path, "check", "passkeys") == 0
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer") == 0
    assert run(tmp_path, "check", "passkeys") == 0, "a change may be checked again once approved"
    capsys.readouterr()
    assert run(tmp_path, "status") == 0 and "approve again" not in capsys.readouterr().out
    assert state(ws).status == "approved" and len(fake_provider.requests) == 2


def test_a_models_wording_reaches_the_terminal_and_the_report_as_plain_text(tmp_path, capsys, fake_provider) -> None:
    """Found by the code review: a finding's message was printed and written with its control characters."""
    standard(tmp_path)
    hostile = {**CANNED_FINDINGS["findings"][0], "message": f"{chr(27)}[2J{chr(27)}]0;owned{chr(7)} Not said."}
    fake_provider.answers_when(CHECK, {"findings": [hostile]})
    assert run(tmp_path, "check", "passkeys") == 0
    out, report = capsys.readouterr().out, read_text(tmp_path / REPORT)
    for text in (out, report):
        assert chr(27) not in text and chr(7) not in text and "Not said." in text


def test_a_check_by_code_alone_does_not_clear_what_a_model_found(tmp_path, capsys, fake_provider) -> None:
    """Found by the code review: `check --no-model` on the same files counted the code's findings alone, so a
    blocking finding of the model's was gone with nothing fixed and no reason recorded."""
    ws = standard(tmp_path)
    fake_provider.answers_when(CHECK, {"findings": [REAL]})
    assert run(tmp_path, "check", "passkeys") == 1
    before = read_text(tmp_path / REPORT)
    capsys.readouterr()
    assert run(tmp_path, "check", "passkeys", "--no-model") == 1
    assert "stands" in capsys.readouterr().err and read_text(tmp_path / REPORT) == before
    held = state(ws).check
    assert (held.blocking, held.model) == (1, "fake on gemini")
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer") == 1


def test_a_check_by_code_alone_after_an_edit_does_not_clear_what_a_model_found(tmp_path, capsys, fake_provider) -> None:
    """Found by the fourth audit: once any file the check read was edited, `check --no-model` recorded a check by
    code alone over the model's, and an approval went through with the model's blocking finding never fixed, on
    the strict tier too, where nothing may be set aside. Only a model clears what a model found."""
    ws = standard(tmp_path)
    fake_provider.answers_when(CHECK, {"findings": [REAL]})
    assert run(tmp_path, "check", "passkeys") == 1
    brief = tmp_path / ".spec/changes/passkeys/brief.md"
    write_text(brief, read_text(brief) + "\nOne word more.\n")
    capsys.readouterr()
    assert run(tmp_path, "check", "passkeys", "--no-model") == 1
    assert "asks the model again" in capsys.readouterr().err
    held = state(ws).check
    assert (held.blocking, held.model) == (1, "fake on gemini")
    asked = len(fake_provider.requests)
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer") == 1
    assert len(fake_provider.requests) > asked, "the approval asked the model again"


def test_a_check_by_code_alone_leaves_the_report_of_the_model_it_does_not_replace(tmp_path, fake_provider) -> None:
    """Found by the cleanup review: with an error in the files, `check` ran by code alone, kept the model's record,
    and wrote its own report over the model's, which then no longer listed what blocked."""
    ws = standard(tmp_path)
    fake_provider.answers_when(CHECK, {"findings": [REAL]})
    assert run(tmp_path, "check", "passkeys") == 1
    before = read_text(tmp_path / REPORT)
    write_text(tmp_path / ".spec/changes/passkeys/tasks.md", "# Tasks\n\nNot a task.\n")
    assert run(tmp_path, "check", "passkeys") == 1
    assert read_text(tmp_path / REPORT) == before and state(ws).check.model == "fake on gemini"


def test_a_living_spec_that_does_not_read_makes_no_task_a_stranger(tmp_path, capsys) -> None:
    """Found by the code review: with another capability's spec unreadable, a task that rightly named one of its
    requirements was said to name a requirement no living spec holds."""
    ws = seeded(tmp_path)
    ws.write_specs({"billing": parse_spec(SPEC.replace("# auth", "# billing").replace("REQ-AUTH", "REQ-BILLING"))})
    tasks = tmp_path / ".spec/changes/passkeys/tasks.md"
    write_text(tasks, read_text(tasks).replace("T003 Update", "T003 [REQ-BILLING-001] Update"))
    assert not [f for f in findings_of(ws.load_change("passkeys"), ws.specs()[0]) if f.code.startswith("check.")]
    spec = tmp_path / ".spec/specs/billing/spec.md"
    write_text(spec, read_text(spec).replace("## Requirements", "## Requirments"))
    specs, _problems = ws.specs()
    unreadable = set(ws.capabilities()) - set(specs)
    assert unreadable == {"billing"}
    found = findings_of(ws.load_change("passkeys"), specs, unreadable)
    assert not [f for f in found if f.code.startswith("check.")]
    capsys.readouterr()
    assert run(tmp_path, "validate", "passkeys") == 1  # the spec's own fault, and nothing said of the task
    assert "check.task-unknown-requirement" not in capsys.readouterr().out


def test_a_report_leaves_a_findings_own_words_alone() -> None:
    """Found by the code review: tidying the place of a finding also rewrote ` :` inside its message."""
    from adk_spec.domain.model import Finding
    from adk_spec.domain.report_md import render_check

    worded = Finding(
        severity="WARNING", code="check.ambiguity", message="the ratio a : b is wrong", path="brief.md", line=3
    )
    placeless = Finding(severity="ERROR", code="check.missing", message="nothing : here")
    report = render_check("x", "t", [worded, placeless], model=None)
    assert "- `check.ambiguity` brief.md:3: the ratio a : b is wrong" in report
    assert "- `check.missing`: nothing : here" in report


def test_the_check_is_told_to_report_every_fault_it_finds(tmp_path, fake_provider) -> None:
    """The second live measurement: the model mostly gave one finding a run, and where it named one fault it left
    the next unsaid: a planted contradiction was caught in one run of three beside a gap it named in all three."""
    standard(tmp_path)
    assert run(tmp_path, "check", "passkeys") == 0
    (sent,) = [str(r.config.system_instruction) for r in fake_provider.requests]
    assert sent.startswith(CHECK)
    assert "Report every fault you find. One finding does not excuse the next." in sent
    assert "An empty list is a good answer." in sent, "and still none where there is none"


# Found by the code review of the simple flow.


def test_a_check_goes_stale_when_a_rule_it_read_changes(tmp_path, capsys, fake_provider) -> None:
    """A blocking finding said "fix them and approve again", and the approval makes a check again only where the
    check is stale. A fix made in the repository's rules, which the check read and which is no file of the change,
    left the check current and blocking: every further `approve` refused with the same sentence."""
    ws = standard(tmp_path)
    fake_provider.answers_each_time(CHECK, iter([{"findings": [REAL]}, None]))
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer") == 1 and state(ws).check.blocking == 1
    assert ".spec/constitution.md" in state(ws).check.files, "what the check read beside the change's own files"
    rules = tmp_path / ".spec/constitution.md"
    write_text(rules, read_text(rules) + "\nPassword sign-in stays until passkeys are proven.\n")
    capsys.readouterr()
    assert run(tmp_path, "status") == 0 and "run `adk-spec approve passkeys`" in capsys.readouterr().out
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer") == 0
    assert len(fake_provider.requests) == 2 and state(ws).status == "approved"


def test_a_check_goes_stale_when_a_living_spec_it_read_changes(tmp_path, fake_provider) -> None:
    ws = standard(tmp_path)
    assert run(tmp_path, "check", "passkeys") == 0
    assert ".spec/specs/auth/spec.md" in state(ws).check.files
    living = tmp_path / ".spec/specs/auth/spec.md"
    assert "after five failed attempts" in read_text(living)
    write_text(living, read_text(living).replace("after five failed attempts", "after six failed attempts"))
    assert run(tmp_path, "check", "passkeys", "--no-model") in (0, 1)
    assert len(fake_provider.requests) == 1 and state(ws).check.model is None, "the model's check no longer stands"


def test_an_approval_waits_for_living_specs_that_read(tmp_path, capsys, fake_provider) -> None:
    """A living spec that does not read makes the code's check of coverage step aside in silence. An approval, and
    the model call it now makes, went through with a requirement no task served."""
    ws = standard(tmp_path)
    write_text(tmp_path / ".spec/specs/billing/spec.md", "not a spec\n")
    capsys.readouterr()
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer") == 1
    said = capsys.readouterr()
    assert "a living spec does not read" in said.err and ".spec/specs/billing/spec.md" in said.out
    assert fake_provider.requests == [] and state(ws).check is None and state(ws).approval is None
    assert run(tmp_path, "check", "passkeys") == 1 and fake_provider.requests == []
    assert "a living spec does not read" in capsys.readouterr().err


def test_approve_says_which_bases_it_recorded(tmp_path, capsys) -> None:
    """A base recorded in silence at approval time is whatever the requirement says then, not what the delta was
    written against: a person is told which requirements to read again."""
    seeded(tmp_path)
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer") == 0
    assert "based     REQ-AUTH-001, REQ-AUTH-002 as the living spec holds them now" in capsys.readouterr().out
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer") == 0
    assert "based     " not in capsys.readouterr().out, "nothing is said where nothing was recorded"


def test_a_change_too_large_for_the_models_check_is_told_the_way_without_one(
    tmp_path, monkeypatch, capsys, fake_provider
) -> None:
    from adk_spec.workspace import context

    ws = standard(tmp_path)
    monkeypatch.setattr(context, "CONTEXT_MAX_CHARS", 10)
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer") == 2
    assert "adk-spec check passkeys --no-model" in capsys.readouterr().err
    assert fake_provider.requests == [] and state(ws).approval is None


def test_a_finding_that_quotes_a_line_as_the_model_was_shown_it_is_kept(tmp_path, fake_provider) -> None:
    """The same fault as in `verify`: a finding on a line the scrub had rewritten was left out, its quote being
    looked for in the file as it stood before."""
    from adk_spec.domain.secrets import scrub

    ws = standard(tmp_path)
    line = 'The test account signs in with password = "' + "hunter2-" + 'hunter2".'
    shown = scrub(line)[0]
    assert shown != line
    brief = tmp_path / ".spec/changes/passkeys/brief.md"
    write_text(brief, read_text(brief).replace("Browsers in scope support WebAuthn.", line))
    written = {**REAL, "quote": shown, "message": "A password is written out in the brief."}
    fake_provider.answers_when(CHECK, {"findings": [written]})
    assert run(tmp_path, "check", "passkeys") == 1
    assert state(ws).check.blocking == 1 and "A password is written out in the brief." in read_text(tmp_path / REPORT)
    assert "hunter2" not in str(fake_provider.requests[-1].config.system_instruction)


def test_a_refused_approval_counts_nothing_the_finding_above_it_says(tmp_path, capsys, fake_provider) -> None:
    """Found by the third audit: the check said "2 blocking" and the refusal "1 findings block it", the one finding
    that says the check blocks. The refusal points at the findings it printed, which say what to do."""
    standard(tmp_path)
    fake_provider.answers_when(CHECK, {"findings": [REAL]})
    capsys.readouterr()
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer") == 1
    said = capsys.readouterr().err
    assert "`passkeys` is not approved: the finding above blocks it" in said and "findings block it" not in said


def test_a_lean_changes_old_check_does_not_hold_a_check_by_code_alone(tmp_path, fake_provider) -> None:
    """Found by the code review: a lean change owes no check, yet a model's old blocking check made every
    `check --no-model` end with exit 1 after the files were fixed."""
    seeded(tmp_path)  # lean
    fake_provider.answers_when(CHECK, {"findings": [REAL]})
    assert run(tmp_path, "check", "passkeys") == 1
    brief = tmp_path / ".spec/changes/passkeys/brief.md"
    write_text(brief, read_text(brief) + "\nFixed.\n")
    assert run(tmp_path, "check", "passkeys", "--no-model") == 0
