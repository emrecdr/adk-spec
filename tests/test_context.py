"""What a stage is given to read: the capabilities by name and purpose, each living spec whole, the constitution."""

from __future__ import annotations

import pytest
from conftest import seeded

from adk_spec.domain.text import lines_of
from adk_spec.interfaces.cli import main
from adk_spec.orchestration.stages import BOUNDARY
from adk_spec.workspace import context
from adk_spec.workspace.context import (
    ContextTooLargeError,
    capability_index,
    constitution_text,
    living_text,
    profile_text,
)
from adk_spec.workspace.files import write_text
from adk_spec.workspace.layout import PROFILE, Workspace


def test_the_index_gives_each_capability_its_purpose(tmp_path) -> None:
    assert capability_index(seeded(tmp_path / "one").specs()[0]) == "auth: Sign-in and session handling."
    assert capability_index(Workspace.init(tmp_path / "empty").specs()[0]) == ""


def test_living_text_is_each_named_spec_whole_and_skips_one_not_there_yet(tmp_path) -> None:
    specs = seeded(tmp_path).specs()[0]
    text = living_text(specs, ["auth", "search"])
    assert text.startswith("=== auth\n# auth\n") and "REQ-AUTH-002" in text and "search" not in text
    assert living_text(specs, ["search"]) == ""


def test_a_context_past_the_limit_is_refused_by_name_and_never_cut(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(context, "CONTEXT_MAX_CHARS", 100)
    with pytest.raises(ContextTooLargeError, match="auth"):
        living_text(seeded(tmp_path).specs()[0], ["auth"])


def test_the_constitution_is_read_as_it_stands(tmp_path) -> None:
    assert constitution_text(Workspace.init(tmp_path)).startswith("# Constitution\n")


def test_a_long_constitution_is_a_warning(tmp_path, capsys) -> None:
    Workspace.init(tmp_path)
    write_text(tmp_path / ".spec/constitution.md", "# Constitution\n\n" + "x" * 16_001)
    assert main(["--root", str(tmp_path), "validate"]) == 0
    assert "WARNING constitution.long .spec/constitution.md" in capsys.readouterr().out


def test_smoke_tells_triage_the_capabilities_the_workspace_holds(tmp_path, monkeypatch, fake_provider) -> None:
    monkeypatch.setenv("SPEC_PROVIDER", "gemini")
    monkeypatch.setenv("SPEC_MODEL", "fake")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    seeded(tmp_path)
    assert main(["--root", str(tmp_path), "smoke"]) == 0
    sent = str(fake_provider.requests[0].config.system_instruction)
    assert f"<<< capabilities {BOUNDARY}\nauth: Sign-in and session handling.\n>>> capabilities {BOUNDARY}" in sent


def test_the_index_breaks_a_purpose_at_a_newline_alone(tmp_path) -> None:
    """Found by review: `str.splitlines` was used, which also breaks at a form feed and at U+2028."""
    from samples import SPEC

    ws = seeded(tmp_path)
    odd = "Sign-in" + chr(0x2028) + "and sessions."
    write_text(tmp_path / ".spec/specs/auth/spec.md", SPEC.replace("Sign-in and session handling.", odd))
    assert capability_index(ws.specs()[0]) == f"auth: {odd}"


def test_a_tree_within_the_limit_is_every_path_and_past_it_folders_with_counts() -> None:
    from adk_spec.workspace.context import TREE_MAX_PATHS, tree_text

    assert tree_text([]) == ""
    assert tree_text(["src/app.py", "README.md"]) == "src/app.py\nREADME.md"
    paths = [f"src/pkg{n % 4}/mod{n}.py" for n in range(TREE_MAX_PATHS + 1)] + ["README.md", "docs/guide/a/b.md"]
    lines = lines_of(tree_text(paths))
    assert lines[0].startswith("303 files: too many to list")
    assert "src/pkg0/ (76 files)" in lines and "./ (1 file)" in lines and "docs/guide/ (1 file)" in lines
    assert len(lines) == 7, "the first line, then one a folder"


def test_the_profile_is_read_as_it_stands_and_cut_past_its_cap(tmp_path, monkeypatch) -> None:
    ws = Workspace.init(tmp_path)
    assert profile_text(ws) == ""
    write_text(ws.home / PROFILE, "# This repository\n\nA profile a person edited.\n")
    assert profile_text(ws) == "# This repository\n\nA profile a person edited."
    monkeypatch.setattr(context, "PROFILE_MAX_CHARS", 10)
    assert profile_text(ws).startswith("# This rep\n(cut here: profile.md is longer than a stage is given)")
