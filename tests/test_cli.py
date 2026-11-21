"""The `adk-spec` command, run in process: what it prints, what it writes and how it exits."""

from __future__ import annotations

import json

import pytest
from conftest import seeded
from samples import SPEC

from adk_spec.interfaces.cli import main
from adk_spec.workspace.files import write_text
from adk_spec.workspace.layout import Workspace


def test_version_names_the_package_and_its_version(capsys) -> None:
    with pytest.raises(SystemExit) as stopped:
        main(["--version"])
    assert stopped.value.code == 0 and capsys.readouterr().out.strip() == "adk-spec 0.1.0"


def test_a_usage_error_ends_by_naming_help(capsys) -> None:
    with pytest.raises(SystemExit) as stopped:
        main(["--no-such-flag"])
    assert stopped.value.code == 2 and "--help lists every" in capsys.readouterr().err


def run(tmp_path, *argv: str) -> int:
    return main(["--root", str(tmp_path), *argv])


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
    row = {"id": "passkeys", "tier": "lean", "status": "draft", "next": "run `adk-spec rebase passkeys`"}
    assert json.loads(capsys.readouterr().out) == {"changes": [row]}
    assert run(tmp_path, "status") == 0
    assert "passkeys" in (line := capsys.readouterr().out.strip()) and "run `adk-spec rebase passkeys`" in line


def test_outside_a_workspace_is_a_sentence_and_exit_2(tmp_path, capsys) -> None:
    assert run(tmp_path, "status") == 2
    out = capsys.readouterr()
    assert "adk-spec init" in out.err and "Traceback" not in out.err


def test_a_change_that_is_not_there_is_a_sentence_and_exit_2(tmp_path, capsys) -> None:
    seeded(tmp_path)
    assert run(tmp_path, "validate", "no-such") == 2
    assert "no change `no-such`" in capsys.readouterr().err
