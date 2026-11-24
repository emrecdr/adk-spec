"""What a stage is given to read: the capabilities by name and purpose, each living spec whole, the constitution."""

from __future__ import annotations

import pytest
from conftest import seeded

from adk_spec.domain.text import lines_of
from adk_spec.interfaces.cli import main
from adk_spec.orchestration.stages import BOUNDARY
from adk_spec.workspace import context
from adk_spec.workspace.context import (
    NEW_CAPABILITY,
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


def test_living_text_is_each_named_spec_whole_and_names_one_not_there_yet_as_new(tmp_path) -> None:
    """Found by the third audit: a capability with no living spec was left out without a word, and the deltas stage,
    told to give a purpose only to a new one, was never told which were new: `delta.purpose-missing` was the send-back
    met most."""
    specs = seeded(tmp_path).specs()[0]
    text = living_text(specs, ["auth", "search"])
    assert text.startswith("=== auth\n# auth\n") and "REQ-AUTH-002" in text
    assert text.endswith(f"=== search\n{NEW_CAPABILITY}")
    assert living_text(specs, ["search"]) == f"=== search\n{NEW_CAPABILITY}"


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


def test_a_tree_of_more_folders_than_the_limit_is_folded_again_and_cut_with_a_count() -> None:
    """Found by the fourth audit: a monorepo of 3,000 packages gave 3,000 folder lines to every stage told the tree."""
    from adk_spec.workspace.context import TREE_MAX_PATHS, tree_text

    paths = [f"packages/p{n}/src/a.py" for n in range(TREE_MAX_PATHS * 2)] + [f"apps/a{n}/x.py" for n in range(3)]
    lines = lines_of(tree_text(paths))
    assert lines[0].startswith(f"{len(paths):,} files: too many to list") and "one level deep" in lines[0]
    assert lines[1:] == ["apps/ (3 files)", f"packages/ ({TREE_MAX_PATHS * 2:,} files)"]
    many = [f"p{n}/src/a.py" for n in range(TREE_MAX_PATHS + 5)]
    lines = lines_of(tree_text(many))
    assert len(lines) == TREE_MAX_PATHS + 2 and lines[-1] == "and 5 more folders"


def test_the_profile_is_read_as_it_stands_and_cut_past_its_cap(tmp_path, monkeypatch) -> None:
    ws = Workspace.init(tmp_path)
    assert profile_text(ws) == ""
    write_text(ws.home / PROFILE, "# This repository\n\nA profile a person edited.\n")
    assert profile_text(ws) == "# This repository\n\nA profile a person edited."
    monkeypatch.setattr(context, "PROFILE_MAX_CHARS", 10)
    assert profile_text(ws).startswith("# This rep\n(cut here: profile.md is longer than a stage is given)")


def test_a_full_profile_reaches_a_stage_with_its_risks_and_unknowns(tmp_path) -> None:
    """A reading keeps at most 40 statements. Rendered, such a profile ran past the cap a stage was given, and the
    risks and unknowns, which come last, were cut."""
    from adk_spec.domain.context_md import PROFILE_HEADING, PROFILE_SECTIONS, render_context
    from adk_spec.domain.model import Statement

    kinds = ["exists"] * 14 + ["touches"] * 10 + ["convention"] * 10 + ["risk"] * 6
    held = [
        Statement(kind=kind, path=f"src/m{n}.py", line=n + 1, quote="q" * 120, note="n" * 160, within="def f():")
        for n, kind in enumerate(kinds)
    ]
    text = render_context(
        PROFILE_HEADING,
        at="2026-11-22T10:00:00+00:00",
        commit=None,
        statements=held,
        read=[f"src/m{n}.py (whole)" for n in range(40)],
        unknown=[("Who owns sessions?", "")],
        sections=PROFILE_SECTIONS,
    )
    ws = Workspace.init(tmp_path)
    write_text(ws.home / PROFILE, text)
    shown = profile_text(ws)
    assert "## Risks and what is unclear" in shown and "- Who owns sessions?" in shown


def test_a_readings_text_given_to_the_brief_is_cut_as_context_md_would_be() -> None:
    """Found by review of phase 15: the reading before the brief handed its text on whole, past the cap every stage
    is held to through this module."""
    from adk_spec.workspace.context import CONTEXT_FILE_MAX_CHARS, context_of

    held = context_of("# Context\n\n" + "x" * (CONTEXT_FILE_MAX_CHARS * 2))
    assert len(held) < CONTEXT_FILE_MAX_CHARS + 100 and held.endswith("is longer than a stage is given)")
