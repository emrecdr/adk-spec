"""What a stage is given to read: the capabilities by name and purpose, each living spec whole, the constitution."""

from __future__ import annotations

import pytest
from conftest import seeded

from adk_spec.interfaces.cli import main
from adk_spec.workspace import context
from adk_spec.workspace.context import ContextTooLargeError, capability_index, constitution_text, living_text
from adk_spec.workspace.files import write_text
from adk_spec.workspace.layout import Workspace


def test_the_index_gives_each_capability_its_purpose(tmp_path) -> None:
    assert capability_index(seeded(tmp_path / "one")) == "auth: Sign-in and session handling."
    assert capability_index(Workspace.init(tmp_path / "empty")) == ""


def test_living_text_is_each_named_spec_whole_and_skips_one_not_there_yet(tmp_path) -> None:
    text = living_text(seeded(tmp_path), ["auth", "search"])
    assert text.startswith("=== auth\n# auth\n") and "REQ-AUTH-002" in text and "search" not in text
    assert living_text(seeded(tmp_path / "other"), ["search"]) == ""


def test_a_context_past_the_limit_is_refused_by_name_and_never_cut(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(context, "CONTEXT_MAX_CHARS", 100)
    with pytest.raises(ContextTooLargeError, match="auth"):
        living_text(seeded(tmp_path), ["auth"])


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
    assert "Known capabilities: auth: Sign-in and session handling." in sent
