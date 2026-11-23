"""The `adk-spec` command, run in process: what it prints, what it writes and how it exits."""

from __future__ import annotations

import json

import pytest
from conftest import approved, held_open_from, run, seeded, state_of
from samples import BRIEF, DELTA, SPEC, tasks_for

from adk_spec.domain.spec_md import parse_spec
from adk_spec.interfaces.cli import main
from adk_spec.workspace.files import read_text, write_text
from adk_spec.workspace.layout import Workspace


def test_version_names_the_package_and_its_version(capsys) -> None:
    with pytest.raises(SystemExit) as stopped:
        main(["--version"])
    assert stopped.value.code == 0 and capsys.readouterr().out.strip() == "adk-spec 0.1.0"


def test_a_usage_error_ends_by_naming_help(capsys) -> None:
    with pytest.raises(SystemExit) as stopped:
        main(["--no-such-flag"])
    assert stopped.value.code == 2 and "--help lists every" in capsys.readouterr().err


def test_init_then_status_says_there_is_nothing_yet(tmp_path, capsys) -> None:
    assert run(tmp_path, "init") == 0 and run(tmp_path, "status") == 0
    assert "no open changes" in capsys.readouterr().out


def test_new_makes_a_draft_at_the_configs_tier(tmp_path) -> None:
    run(tmp_path, "init")
    assert run(tmp_path, "new", "passkeys") == 0 and run(tmp_path, "new", "small-fix", "--tier", "lean") == 0
    state = json.loads((tmp_path / ".spec/changes/passkeys/change.json").read_text(encoding="utf-8"))
    assert (state["id"], state["tier"], state["status"]) == ("passkeys", "standard", "draft")
    assert json.loads((tmp_path / ".spec/changes/small-fix/change.json").read_text(encoding="utf-8"))["tier"] == "lean"


def test_validate_lists_each_finding_with_its_place_and_fails_on_an_error(tmp_path, capsys) -> None:
    Workspace.init(tmp_path)
    broken = SPEC.replace("#### Scenario: Too many failures", "#### Scenario Too many failures")
    write_text(tmp_path / ".spec/specs/auth/spec.md", broken)
    assert run(tmp_path, "validate") == 1
    out = capsys.readouterr().out
    assert "ERROR syntax .spec/specs/auth/spec.md:22" in out and "1 errors, 0 warnings" in out


def test_warnings_fail_only_under_strict(tmp_path, capsys) -> None:
    Workspace.init(tmp_path)
    write_text(tmp_path / ".spec/specs/auth/spec.md", SPEC.replace("The system SHALL let", "The system lets"))
    assert run(tmp_path, "validate") == 0
    assert "WARNING spec.no-shall .spec/specs/auth/spec.md" in capsys.readouterr().out
    assert run(tmp_path, "validate", "--strict") == 1


def test_validate_json_is_the_findings_as_data(tmp_path, capsys) -> None:
    seeded(tmp_path)
    assert run(tmp_path, "validate", "passkeys", "--json") == 0
    said = json.loads(capsys.readouterr().out)
    assert said["failed"] is False and {f["code"] for f in said["findings"]} == {"delta.base-missing"}
    assert said["findings"][0]["path"] == ".spec/changes/passkeys/specs/auth/spec.md"


def test_status_names_the_next_step_of_each_change(tmp_path, capsys) -> None:
    seeded(tmp_path)
    assert run(tmp_path, "status", "--json") == 0
    row = {
        "id": "passkeys",
        "tier": "lean",
        "status": "draft",
        "actor": "you",
        "next": "run `adk-spec approve passkeys`",
    }
    assert json.loads(capsys.readouterr().out) == {"changes": [row]}
    assert run(tmp_path, "status") == 0
    assert "passkeys" in (line := capsys.readouterr().out.strip()) and "run `adk-spec approve passkeys`" in line


def test_outside_a_workspace_is_a_sentence_and_exit_2(tmp_path, capsys) -> None:
    assert run(tmp_path, "status") == 2
    out = capsys.readouterr()
    assert "adk-spec init" in out.err and "Traceback" not in out.err


def test_a_change_that_is_not_there_is_a_sentence_and_exit_2(tmp_path, capsys) -> None:
    seeded(tmp_path)
    assert run(tmp_path, "validate", "no-such") == 2
    assert "no change `no-such`" in capsys.readouterr().err


def living_bytes(tmp_path, capability: str = "auth") -> bytes:
    return (tmp_path / f".spec/specs/{capability}/spec.md").read_bytes()


def test_the_whole_lean_lifecycle_runs_without_a_model(tmp_path, capsys) -> None:
    seeded(tmp_path)
    assert run(tmp_path, "validate", "passkeys") == 0
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer") == 0, "three commands: no `rebase` first"
    state = state_of(tmp_path)
    assert state["status"] == "approved" and state["approval"]["by"] == "reviewer"
    assert set(state["approval"]["files"]) == {"brief.md", "tasks.md", "specs/auth/spec.md"}
    tasks = tmp_path / ".spec/changes/passkeys/tasks.md"
    write_text(tasks, read_text(tasks).replace("- [ ] T001", "- [x] T001"))
    assert run(tmp_path, "archive", "passkeys") == 0
    merged = parse_spec(living_bytes(tmp_path).decode())
    assert [r.id for r in merged.requirements] == ["REQ-AUTH-002", "REQ-AUTH-004"]
    assert merged.retired[-1].change == "passkeys"
    assert state_of(tmp_path)["status"] == "archived" and run(tmp_path, "validate") == 0
    capsys.readouterr()
    assert run(tmp_path, "status") == 0 and "no open changes" in capsys.readouterr().out
    assert run(tmp_path, "status", "--all") == 0 and "archived" in capsys.readouterr().out


def test_an_edit_after_approval_stops_the_archive_and_writes_nothing(tmp_path, capsys) -> None:
    seeded(tmp_path)
    approved(tmp_path)
    delta = tmp_path / ".spec/changes/passkeys/specs/auth/spec.md"
    write_text(delta, read_text(delta).replace("three failed attempts", "two failed attempts"))
    before = living_bytes(tmp_path)
    assert run(tmp_path, "archive", "passkeys") == 1
    assert "specs/auth/spec.md" in capsys.readouterr().err and living_bytes(tmp_path) == before
    assert state_of(tmp_path)["status"] == "approved"


def test_a_second_change_to_one_requirement_is_stopped_at_archive(tmp_path, capsys) -> None:
    ws = seeded(tmp_path)
    folder = ws.new_change("stricter-lock", "lean")
    write_text(folder / "brief.md", BRIEF)
    write_text(folder / "tasks.md", tasks_for("REQ-AUTH-002"))
    block = DELTA.split("## MODIFIED Requirements\n\n")[1].split("\n## REMOVED")[0].replace("three", "two")
    write_text(folder / "specs" / "auth" / "spec.md", "# Delta: auth\n\n## MODIFIED Requirements\n\n" + block)
    for change in ("passkeys", "stricter-lock"):
        approved(tmp_path, change)
    assert run(tmp_path, "archive", "passkeys") == 0
    after_first = living_bytes(tmp_path)
    capsys.readouterr()
    assert run(tmp_path, "archive", "stricter-lock") == 1
    said = capsys.readouterr()
    assert "delta.base-stale" in said.out and "rebase" in said.err and living_bytes(tmp_path) == after_first
    assert state_of(tmp_path, "stricter-lock")["status"] == "approved"


def test_a_standard_change_waits_for_verify(tmp_path, capsys) -> None:
    seeded(tmp_path)
    run(tmp_path, "new", "audited", "--tier", "standard")
    source, target = tmp_path / ".spec/changes/passkeys", tmp_path / ".spec/changes/audited"
    for name in ("brief.md", "tasks.md", "specs/auth/spec.md"):
        write_text(target / name, read_text(source / name))
    assert run(tmp_path, "rebase", "audited") == 0
    assert run(tmp_path, "check", "audited", "--no-model") == 0, "a standard change is checked before it is approved"
    assert run(tmp_path, "approve", "audited", "--by", "reviewer") == 0
    capsys.readouterr()
    assert run(tmp_path, "archive", "audited") == 1 and "verify" in capsys.readouterr().err


def test_an_archive_writes_no_capability_when_one_refuses(tmp_path) -> None:
    ws = seeded(tmp_path)
    ws.write_specs({"billing": parse_spec(SPEC.replace("# auth", "# billing").replace("REQ-AUTH", "REQ-BILLING"))})
    billing = DELTA.replace("# Delta: auth", "# Delta: billing").replace("REQ-AUTH", "REQ-BILLING")
    write_text(tmp_path / ".spec/changes/passkeys/specs/billing/spec.md", billing)
    served = ("REQ-AUTH-004", "REQ-AUTH-002", "REQ-BILLING-004", "REQ-BILLING-002")
    write_text(tmp_path / ".spec/changes/passkeys/tasks.md", tasks_for(*served))
    approved(tmp_path)
    spec = tmp_path / ".spec/specs/billing/spec.md"
    write_text(spec, read_text(spec).replace("after five failed", "after nine failed"))
    before = living_bytes(tmp_path)
    assert run(tmp_path, "archive", "passkeys") == 1 and living_bytes(tmp_path) == before
    assert state_of(tmp_path)["status"] == "approved"


def test_a_rebase_voids_an_approval_and_says_what_was_stale(tmp_path, capsys) -> None:
    seeded(tmp_path)
    approved(tmp_path)
    write_text(tmp_path / ".spec/specs/auth/spec.md", SPEC.replace("after five failed", "after nine failed"))
    capsys.readouterr()
    assert run(tmp_path, "rebase", "passkeys") == 0
    out = capsys.readouterr().out
    assert "REQ-AUTH-002  was stale" in out and "REQ-AUTH-001  unchanged" in out
    assert state_of(tmp_path)["status"] == "draft" and state_of(tmp_path)["approval"] is None


def test_a_rebase_that_changes_nothing_keeps_the_approval(tmp_path) -> None:
    seeded(tmp_path)
    approved(tmp_path)
    assert run(tmp_path, "rebase", "passkeys") == 0 and state_of(tmp_path)["status"] == "approved"


def test_an_approval_names_the_account_where_no_name_is_given(tmp_path, monkeypatch) -> None:
    seeded(tmp_path)
    monkeypatch.setattr("getpass.getuser", lambda: "the-account")
    assert run(tmp_path, "rebase", "passkeys") == 0 and run(tmp_path, "approve", "passkeys") == 0
    approval = state_of(tmp_path)["approval"]
    assert approval["by"] == "the-account" and approval["at"].endswith("+00:00")


def test_an_archived_change_is_archived_once(tmp_path, capsys) -> None:
    seeded(tmp_path)
    approved(tmp_path)
    assert run(tmp_path, "archive", "passkeys") == 0
    after = living_bytes(tmp_path)
    capsys.readouterr()
    assert run(tmp_path, "archive", "passkeys") == 1 and "already" in capsys.readouterr().err
    assert run(tmp_path, "approve", "passkeys") == 1 and living_bytes(tmp_path) == after


def test_the_installed_package_is_found_from_any_folder(tmp_path) -> None:
    """The suite runs with the checkout on the path, so it cannot see an install that maps no package: found by
    running the installed command by hand, which failed with `No module named 'adk_spec'` outside the checkout."""
    import os
    import subprocess
    import sys

    env = {name: value for name, value in os.environ.items() if name != "PYTHONPATH"}
    probe = "import adk_spec.interfaces.cli as cli; print(cli.PROG)"
    done = subprocess.run(
        [sys.executable, "-c", probe], cwd=tmp_path, env=env, capture_output=True, encoding="utf-8", check=False
    )
    assert done.returncode == 0 and done.stdout.strip() == "adk-spec", done.stderr


def test_an_archive_that_cannot_write_one_file_changes_none_and_says_so(tmp_path, monkeypatch, capsys) -> None:
    """Found by review: a file held open left one spec merged, the other not, and the state behind both; and the
    failure reached the person as a traceback under the exit code that means findings."""

    ws = seeded(tmp_path)
    ws.write_specs({"billing": parse_spec(SPEC.replace("# auth", "# billing").replace("REQ-AUTH", "REQ-BILLING"))})
    billing = DELTA.replace("# Delta: auth", "# Delta: billing").replace("REQ-AUTH", "REQ-BILLING")
    write_text(tmp_path / ".spec/changes/passkeys/specs/billing/spec.md", billing)
    served = ("REQ-AUTH-004", "REQ-AUTH-002", "REQ-BILLING-004", "REQ-BILLING-002")
    write_text(tmp_path / ".spec/changes/passkeys/tasks.md", tasks_for(*served))
    approved(tmp_path)
    before = (living_bytes(tmp_path), living_bytes(tmp_path, "billing"), state_of(tmp_path))
    held_open_from(monkeypatch)
    capsys.readouterr()
    assert run(tmp_path, "archive", "passkeys") == 3
    said = capsys.readouterr()
    assert "another process holds the file" in said.err and "Traceback" not in said.err
    assert (living_bytes(tmp_path), living_bytes(tmp_path, "billing"), state_of(tmp_path)) == before


def test_an_account_with_no_name_is_asked_to_name_the_approver(tmp_path, monkeypatch, capsys) -> None:
    def no_name():
        raise OSError("No username set in the environment")

    seeded(tmp_path)
    run(tmp_path, "rebase", "passkeys")
    monkeypatch.setattr("getpass.getuser", no_name)
    capsys.readouterr()
    assert run(tmp_path, "approve", "passkeys") == 2 and "--by" in capsys.readouterr().err
    assert state_of(tmp_path)["approval"] is None


def test_an_unreadable_living_spec_is_named_and_is_not_taken_for_a_missing_one(tmp_path, capsys) -> None:
    """Found by validating by hand: a living spec that did not read was treated as absent, so each change on it was
    reported as creating the capability, and `rebase` recorded no bases and voided the approval."""
    seeded(tmp_path)
    approved(tmp_path)
    spec = tmp_path / ".spec/specs/auth/spec.md"
    write_text(spec, read_text(spec) + "\n" + "`" * 3 + "\nexample\n")
    before = state_of(tmp_path)
    capsys.readouterr()
    assert run(tmp_path, "validate") == 1
    out = capsys.readouterr().out
    assert "ERROR syntax .spec/specs/auth/spec.md" in out and "ERROR delta.living-unreadable" in out
    assert "delta.purpose-missing" not in out and "delta.target-missing" not in out
    assert run(tmp_path, "rebase", "passkeys") == 1
    assert "syntax" in capsys.readouterr().out and state_of(tmp_path) == before, "the bases and the approval stand"
    assert run(tmp_path, "status", "--json") == 0
    assert "fix what `adk-spec validate passkeys` lists" in capsys.readouterr().out


def test_one_unreadable_file_does_not_hide_the_other_changes(tmp_path, capsys) -> None:
    """Deferred by the review: a brief that is not UTF-8 ended `status` and `validate` for every change."""
    ws = seeded(tmp_path)
    ws.new_change("second", "lean")
    (tmp_path / ".spec/changes/passkeys/brief.md").write_bytes("# x\n".encode("utf-16"))
    assert run(tmp_path, "status", "--json") == 0
    assert [row["id"] for row in json.loads(capsys.readouterr().out)["changes"]] == ["passkeys", "second"]
    assert run(tmp_path, "validate") == 1
    out = capsys.readouterr().out
    assert "ERROR syntax .spec/changes/passkeys/brief.md" in out and ".spec/changes/second/" in out


def test_rebase_says_which_base_it_dropped(tmp_path, capsys) -> None:
    """Deferred by the review: a base for an ID the delta no longer touches went without a line."""
    seeded(tmp_path)
    run(tmp_path, "rebase", "passkeys")
    delta = tmp_path / ".spec/changes/passkeys/specs/auth/spec.md"
    write_text(delta, read_text(delta).split("## REMOVED Requirements")[0])
    capsys.readouterr()
    assert run(tmp_path, "rebase", "passkeys") == 0
    assert "REQ-AUTH-001  dropped" in capsys.readouterr().out and "REQ-AUTH-001" not in state_of(tmp_path)["bases"]


def test_ctrl_c_is_one_sentence_and_130(monkeypatch, capsys) -> None:
    """Deferred by the review: the process boundary had no test."""
    from adk_spec.interfaces import cli

    def interrupted(_argv):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "main", interrupted)
    assert cli.run() == 130
    assert "interrupted" in capsys.readouterr().err


def test_the_installed_command_reads_what_a_person_types_as_utf8(monkeypatch) -> None:
    """Found by review: stdout and stderr were set to UTF-8 and stdin was not, so an answer piped in on Windows was
    read in the ANSI code page."""
    import io
    import sys

    from adk_spec.interfaces import cli

    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO("twee\u00ebn\n".encode()), encoding="cp1252"))
    monkeypatch.setattr("sys.argv", ["adk-spec"])
    cli.run()
    assert sys.stdin.readline() == "twee\u00ebn\n"


def test_status_groups_changes_by_who_acts_next(tmp_path, capsys) -> None:
    """Borrowed from an overview that groups work as waiting on you, ready, and done: a list of every change in one
    column makes a person read each line to find the ones that wait on them."""
    ws = seeded(tmp_path)
    tasks = tmp_path / ".spec/changes/passkeys/tasks.md"
    planned = read_text(tasks)
    tasks.unlink()  # `passkeys` has no plan yet, so a command is ready to run
    folder = ws.new_change("needs-you", "lean")
    write_text(
        folder / "brief.md", BRIEF.replace("Browsers in scope support WebAuthn.", "[NEEDS CLARIFICATION: which?]")
    )
    capsys.readouterr()
    assert run(tmp_path, "status") == 0
    out = capsys.readouterr().out
    assert out.index("Waiting on you") < out.index("needs-you") < out.index("Ready to run") < out.index("passkeys  ")
    assert "Done" not in out, "a group with no change is not printed"
    write_text(tasks, planned)
    approved(tmp_path)
    assert run(tmp_path, "archive", "passkeys") == 0
    capsys.readouterr()
    assert run(tmp_path, "status", "--all") == 0
    out = capsys.readouterr().out
    assert out.index("Waiting on you") < out.index("Done") < out.index("passkeys  ") and "Ready to run" not in out


def test_approve_records_a_base_that_is_missing_and_needs_no_rebase(tmp_path) -> None:
    """The simple flow: `rebase` was a command a person ran only because `approve` asked for it. What it records
    is a function of the delta and the living spec, which `approve` has read already."""
    seeded(tmp_path)
    assert state_of(tmp_path)["bases"] == {}
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer") == 0
    state = state_of(tmp_path)
    assert set(state["bases"]) == {"REQ-AUTH-001", "REQ-AUTH-002"}, "what the delta removes and what it modifies"
    assert state["approval"]["bases"] == state["bases"]


def test_approve_never_records_anew_a_base_that_moved(tmp_path, capsys) -> None:
    """A base that is recorded and no longer true is the one guard against two changes to one requirement: the
    person must read what the requirement says now. `approve` fills in what is missing and corrects nothing."""
    seeded(tmp_path)
    assert run(tmp_path, "rebase", "passkeys") == 0
    recorded = state_of(tmp_path)["bases"]
    living = tmp_path / ".spec/specs/auth/spec.md"
    write_text(living, read_text(living).replace("after five failed attempts", "after four failed attempts"))
    capsys.readouterr()
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer") == 1
    assert "delta.base-stale" in capsys.readouterr().out
    assert state_of(tmp_path)["bases"] == recorded and state_of(tmp_path)["approval"] is None


def test_the_help_lists_the_everyday_commands_first_under_three_headings(capsys) -> None:
    """Command-line guidance, and git, gh and cargo: the commands most people need come first in the help, and the
    rest stand apart. One flat list in the order they were written put `propose` eighth."""
    from adk_spec.interfaces import cli

    with pytest.raises(SystemExit):
        cli.main(["--help"])
    out = capsys.readouterr().out
    everyday, again = ("propose", "approve", "verify", "archive", "status", "init"), ("plan", "check", "rebase")
    order = ["Everyday:", *(f"\n  {name} " for name in everyday), "To redo one step:"]
    order += [*(f"\n  {name} " for name in (*again, "validate", "new")), "Setup:", "\n  login "]
    assert [out.index(word) for word in order] == sorted(out.index(word) for word in order)
    assert "--root" in out and "--version" in out, "the options are still listed"


def test_every_command_stands_in_exactly_one_group() -> None:
    from adk_spec.interfaces import cli

    grouped = [name for _heading, names in cli.COMMAND_GROUPS for name in names]
    assert sorted(grouped) == sorted(cli._parser().commands.choices), "a command registered and left out of the help"
    assert len(grouped) == len(set(grouped))


def test_a_base_not_yet_recorded_fails_no_strict_validation(tmp_path, capsys) -> None:
    """Found by the code review: `validate --strict` failed a change written by hand on a base that an approval
    records by itself, while `status` said the change was ready to approve."""
    seeded(tmp_path)
    assert run(tmp_path, "validate", "passkeys", "--strict", "--json") in (0, 1)
    said = json.loads(capsys.readouterr().out)
    missing = [f for f in said["findings"] if f["code"] == "delta.base-missing"]
    assert missing and all(f["severity"] == "INFO" for f in missing)
    assert not any(
        f["severity"] in ("ERROR", "WARNING") and f["code"].startswith("delta.base") for f in said["findings"]
    )


def test_status_reads_no_archived_change_and_validate_computes_no_drift(tmp_path, monkeypatch) -> None:
    """Found by an outside audit: `status` read every archived change in full before passing it over, and `validate`
    ran git for each verified change's drift, which it never reads."""
    from adk_spec.interfaces import cli
    from adk_spec.workspace.layout import Workspace

    ws = seeded(tmp_path)
    ws.save_state(ws.load_change("passkeys").change.state.model_copy(update={"status": "archived"}))
    loaded = []
    load = Workspace.load_change
    monkeypatch.setattr(Workspace, "load_change", lambda self, cid: loaded.append(cid) or load(self, cid))
    assert run(tmp_path, "status") == 0 and loaded == []
    from adk_spec.domain.model import Verification

    held = Verification(at="t", base="abc", diff="sha256:x", verdicts={})
    ws.save_state(ws.state("passkeys").model_copy(update={"status": "verified", "verification": held}))
    monkeypatch.setattr(cli, "_drifted", lambda *_args: (_ for _ in ()).throw(AssertionError("drift computed")))
    assert run(tmp_path, "validate") in (0, 1)


def test_validate_checks_no_archived_change(tmp_path, monkeypatch) -> None:
    """Found by an outside audit: `validate` read and checked every archived change in full, and set what it found
    aside."""
    from adk_spec.interfaces import cli

    ws = seeded(tmp_path)
    ws.save_state(ws.load_change("passkeys").change.state.model_copy(update={"status": "archived"}))
    monkeypatch.setattr(cli, "_assessed", lambda *_args, **_kw: (_ for _ in ()).throw(AssertionError("assessed")))
    assert run(tmp_path, "validate") == 0


def test_yes_takes_the_suggestion_and_is_an_answer_where_none_is_suggested(monkeypatch, capsys) -> None:
    """Phase 15, after the grilling skill: a question is worded so that "yes" accepts its suggestion, as `=` does. An
    empty line still leaves a point open, so a key pressed by habit never accepts a model's answer."""
    import io

    from adk_spec.interfaces import cli

    monkeypatch.setattr(cli.sys, "stdin", io.StringIO("yes\nY\n=\nyes\nyes\n\n"))
    asked = [
        {"question": "Keep sessions to eight hours?", "suggested": "Yes, eight hours."},
        {"question": "Sign out on every device?", "suggested": "yes: every device"},
        {"question": "Log each sign-in?", "suggested": "Each one."},
        {"question": "Is it for staff only?", "suggested": ""},
        {"question": "Should the old endpoint be removed?", "suggested": "No, keep it for one release."},
        {"question": "Which region?", "suggested": "Europe."},
    ]
    # Found by review: "yes" taken for "No, keep it" stored the opposite of the person's yes. An answer reaches the
    # next draft beside its question, so a plain "yes" always says what the person meant.
    assert cli._answered(asked) == ["Yes, eight hours.", "yes: every device", "Each one.", "yes", "yes", ""]
    assert "`yes` or `=` takes the suggestion" in capsys.readouterr().out


def test_one_change_whose_state_does_not_read_stops_no_other(tmp_path, capsys) -> None:
    """Found by the third audit: a `change.json` left with a merge's conflict marks stopped `status`, `validate` and
    `propose` for every change, `propose` before any model call. It is named, and the rest go on; its requirement IDs
    stay spoken for."""
    workspace = seeded(tmp_path)
    other = workspace.new_change("other", "lean")
    write_text(other / "change.json", "<<<<<<< HEAD\n{}\n=======\n{}\n>>>>>>> theirs\n")
    write_text(other / "specs" / "billing" / "spec.md", "### Requirement: REQ-BILLING-001 Invoices\n")
    assert run(tmp_path, "status") == 0
    out = capsys.readouterr().out
    assert "passkeys" in out and "other" in out and "change.json does not read" in out
    assert run(tmp_path, "validate") == 1
    assert "ERROR change.unreadable .spec/changes/other/change.json" in capsys.readouterr().out
    living, _found = workspace.specs()
    assert "REQ-BILLING-001" in workspace.taken(living)
