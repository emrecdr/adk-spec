"""The `.spec` tree on disk: made, found, read strictly, and written in the canonical form."""

from __future__ import annotations

import pytest
from conftest import seeded
from samples import BRIEF, DELTA, SPEC, TASKS

from adk_spec.domain.brief_md import parse_brief
from adk_spec.domain.delta_md import parse_delta
from adk_spec.domain.model import ChangeState
from adk_spec.domain.spec_md import parse_spec
from adk_spec.domain.tasks_md import parse_tasks
from adk_spec.workspace.config import Config, ConfigError
from adk_spec.workspace.files import write_text
from adk_spec.workspace.layout import Workspace, WorkspaceError, findings_of


def test_init_makes_the_tree_and_refuses_a_second_time(tmp_path) -> None:
    ws = Workspace.init(tmp_path)
    assert sorted(p.name for p in (tmp_path / ".spec").iterdir()) == [
        "changes",
        "config.toml",
        "constitution.md",
        "specs",
    ]
    assert ws.config() == Config(default_tier="standard") and ws.capabilities() == [] and ws.changes() == []
    with pytest.raises(WorkspaceError, match="already"):
        Workspace.init(tmp_path)


def test_the_workspace_is_found_from_any_folder_below_it(tmp_path) -> None:
    Workspace.init(tmp_path)
    (tmp_path / "src" / "deep").mkdir(parents=True)
    assert Workspace.find(tmp_path / "src" / "deep").root == tmp_path
    with pytest.raises(WorkspaceError, match="adk-spec init"):
        Workspace.find(tmp_path.parent)


@pytest.mark.parametrize(
    ("text", "named"),
    [
        ('[project]\ndefault_teir = "lean"\n', "default_teir"),
        ('[project]\ndefault_tier = "huge"\n', "huge"),
        ("[projct]\n", "projct"),
        ("", "default_tier"),
        ("[project\n", "TOML"),
    ],
)
def test_a_config_that_is_not_what_the_code_reads_is_named(tmp_path, text: str, named: str) -> None:
    ws = Workspace.init(tmp_path)
    write_text(tmp_path / ".spec" / "config.toml", text)
    with pytest.raises(ConfigError, match=named):
        ws.config()


def test_specs_are_written_in_the_canonical_form_and_read_back(tmp_path) -> None:
    ws = Workspace.init(tmp_path)
    ws.write_specs({"auth": parse_spec(SPEC)})
    assert (tmp_path / ".spec" / "specs" / "auth" / "spec.md").read_bytes() == SPEC.encode()
    assert ws.specs() == ({"auth": parse_spec(SPEC)}, []) and ws.capabilities() == ["auth"]


def test_a_change_round_trips_through_its_folder(tmp_path) -> None:
    ws = seeded(tmp_path)
    loaded = ws.load_change("passkeys")
    assert loaded.problems == [] and loaded.change.state == ChangeState(id="passkeys", tier="lean")
    assert loaded.change.deltas == {"auth": parse_delta(DELTA)} and loaded.change.brief == parse_brief(BRIEF)
    assert loaded.change.tasks == parse_tasks(TASKS) and loaded.change.design is None
    assert ws.changes() == ["passkeys"]


def test_a_file_off_its_grammar_is_a_finding_with_its_path_and_line(tmp_path) -> None:
    ws = seeded(tmp_path)
    delta = tmp_path / ".spec" / "changes" / "passkeys" / "specs" / "auth" / "spec.md"
    write_text(delta, DELTA.replace("## REMOVED", "## RENAMED"))
    loaded = ws.load_change("passkeys")
    (problem,) = loaded.problems
    assert (problem.severity, problem.code, problem.path, problem.line) == ("ERROR", "syntax", "specs/auth/spec.md", 25)
    codes = [f.code for f in findings_of(loaded, ws.specs()[0])]
    assert codes == ["syntax"], "a file that did not parse is not also reported as missing"


def test_a_file_that_is_not_utf8_is_a_finding_and_no_crash(tmp_path) -> None:
    ws = seeded(tmp_path)
    (tmp_path / ".spec" / "changes" / "passkeys" / "brief.md").write_bytes("# x\n".encode("utf-16"))
    (problem,) = ws.load_change("passkeys").problems
    assert (problem.code, problem.path) == ("syntax", "brief.md") and "UTF-8" in problem.message


def test_a_living_spec_titled_for_another_folder_is_a_finding(tmp_path) -> None:
    ws = Workspace.init(tmp_path)
    write_text(tmp_path / ".spec" / "specs" / "billing" / "spec.md", SPEC)
    specs, problems = ws.specs()
    assert specs == {}
    assert [(p.code, p.path) for p in problems] == [("spec.folder-mismatch", ".spec/specs/billing/spec.md")]


def test_a_delta_titled_for_another_folder_is_a_finding(tmp_path) -> None:
    ws = seeded(tmp_path)
    write_text(tmp_path / ".spec" / "changes" / "passkeys" / "specs" / "billing" / "spec.md", DELTA)
    problems = ws.load_change("passkeys").problems
    assert [(p.code, p.path) for p in problems] == [("spec.folder-mismatch", "specs/billing/spec.md")]


def test_a_state_file_with_a_key_nobody_wrote_is_refused_by_name(tmp_path) -> None:
    ws = seeded(tmp_path)
    state = tmp_path / ".spec" / "changes" / "passkeys" / "change.json"
    write_text(state, '{"id": "passkeys", "tier": "lean", "aproved": true}')
    with pytest.raises(WorkspaceError, match="aproved"):
        ws.load_change("passkeys")


def test_a_change_id_is_held_to_the_slug_grammar_and_to_what_exists(tmp_path) -> None:
    ws = seeded(tmp_path)
    for bad in ("Passkeys", "con", "a/b"):
        with pytest.raises(WorkspaceError):
            ws.new_change(bad, "lean")
    with pytest.raises(WorkspaceError, match="exists"):
        ws.new_change("passkeys", "lean")
    with pytest.raises(WorkspaceError, match="no change"):
        ws.load_change("no-such")


def test_approval_texts_are_the_files_an_approval_covers(tmp_path) -> None:
    ws = seeded(tmp_path)
    assert ws.approval_texts("passkeys") == {"brief.md": BRIEF, "tasks.md": TASKS, "specs/auth/spec.md": DELTA}
    write_text(tmp_path / ".spec" / "changes" / "passkeys" / "design.md", "# Design\n")
    assert ws.approval_texts("passkeys")["design.md"] == "# Design\n"


def test_a_path_is_shown_from_the_root_with_forward_slashes(tmp_path) -> None:
    ws = Workspace.init(tmp_path)
    assert ws.shown(tmp_path / ".spec" / "specs" / "auth" / "spec.md") == ".spec/specs/auth/spec.md"
