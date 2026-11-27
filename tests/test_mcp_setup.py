"""The MCP server's entry `init` writes into the repository's `.mcp.json`, which GitHub Copilot in VS Code and Claude
Code read: the owner's choice of 27 November 2026, so that no one writes its JSON by hand, on Windows least of all."""

from __future__ import annotations

import json
import os

import pytest
from conftest import run

from adk_spec.interfaces import cli

ENTRY = {"type": "stdio", "command": "adk-spec-mcp"}


def _initialised(root, capsys) -> str:
    capsys.readouterr()
    assert run(root, "init", "--no-explore") == 0
    return capsys.readouterr().out


def _held(root) -> dict:
    return json.loads((root / ".mcp.json").read_text(encoding="utf-8"))


def test_init_adds_adk_spec_to_the_repositorys_mcp_json(tmp_path, capsys) -> None:
    out = _initialised(tmp_path, capsys)
    assert _held(tmp_path) == {"mcpServers": {"adk-spec": ENTRY}}
    assert "wrote     .mcp.json" in out
    capsys.readouterr()
    assert run(tmp_path, "init", "--refresh", "--no-explore") == 0
    assert ".mcp.json" not in capsys.readouterr().out, "an entry that holds already is not said again"


def test_the_servers_an_mcp_json_holds_are_kept_beside_adk_spec(tmp_path, capsys) -> None:
    other = {"command": "npx", "args": ["-y", "some-server"]}
    (tmp_path / ".mcp.json").write_text(json.dumps({"mcpServers": {"other": other}, "note": 1}), encoding="utf-8")
    out = _initialised(tmp_path, capsys)
    assert _held(tmp_path) == {"mcpServers": {"other": other, "adk-spec": ENTRY}, "note": 1}
    assert "added     .mcp.json" in out


def test_an_adk_spec_entry_a_person_wrote_is_theirs(tmp_path, capsys) -> None:
    theirs = {"mcpServers": {"adk-spec": {"command": "uv", "args": ["run", "adk-spec-mcp"]}}}
    (tmp_path / ".mcp.json").write_text(json.dumps(theirs), encoding="utf-8")
    out = _initialised(tmp_path, capsys)
    assert _held(tmp_path) == theirs
    assert "kept      .mcp.json" in out


def test_an_mcp_json_that_does_not_read_is_left_as_it_is(tmp_path, capsys) -> None:
    (tmp_path / ".mcp.json").write_text("{ // a comment\n}", encoding="utf-8")
    out = _initialised(tmp_path, capsys)
    assert (tmp_path / ".mcp.json").read_text(encoding="utf-8") == "{ // a comment\n}"
    assert "skipped   .mcp.json: " in out and "by hand" in out


def test_a_vscode_setup_that_starts_adk_spec_already_is_not_doubled(tmp_path, capsys) -> None:
    """The README's earlier way: VS Code would start the server twice, from both files."""
    (tmp_path / ".vscode").mkdir()
    (tmp_path / ".vscode/mcp.json").write_text('{"servers": {"a": {"command": "adk-spec-mcp"}}}', encoding="utf-8")
    out = _initialised(tmp_path, capsys)
    assert not (tmp_path / ".mcp.json").exists()
    assert "kept      .vscode/mcp.json: it starts adk-spec already" in out


def test_init_names_the_install_where_adk_spec_mcp_is_not_on_path(tmp_path, capsys, monkeypatch) -> None:
    monkeypatch.setattr(cli.shutil, "which", lambda _name: None)
    out = _initialised(tmp_path / "missing", capsys)
    assert "adk-spec-mcp is not on PATH" in out and "uv tool install --editable " in out
    monkeypatch.setattr(cli.shutil, "which", lambda name: f"/bin/{name}")
    assert "not on PATH" not in _initialised(tmp_path / "found", capsys)


@pytest.mark.skipif(os.name == "nt", reason="a link needs a privilege on Windows that a test run does not hold")
def test_an_mcp_json_that_is_a_link_is_not_written_through(tmp_path, capsys) -> None:
    elsewhere = tmp_path / "elsewhere.json"
    elsewhere.write_text("{}", encoding="utf-8")
    (tmp_path / "repo").mkdir()
    (tmp_path / "repo/.mcp.json").symlink_to(elsewhere)
    out = _initialised(tmp_path / "repo", capsys)
    assert elsewhere.read_text(encoding="utf-8") == "{}" and "skipped   .mcp.json: " in out
