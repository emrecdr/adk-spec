"""The project's installed libraries as a reading may see them: its Python environment and its `node_modules`, read
offline at the versions it runs, by the rules a repository's files are read by."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from conftest import python_environment, repository

from adk_spec.workspace.installed import environments
from adk_spec.workspace.source import Source

KEY = "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQ\n"


def _repository(root: Path) -> Path:
    repository(root, {".gitignore": ".venv/\nvenv/\nnode_modules/\n", "src/app.py": "import httpx\n"})
    return root


def _node(root: Path, name: str = "react", files: dict[str, str] | None = None) -> Path:
    package = root / "node_modules" / name
    package.mkdir(parents=True, exist_ok=True)
    (package / "package.json").write_text(json.dumps({"name": name, "version": "19.2.0"}), encoding="utf-8")
    for path, text in (files or {"index.js": "export function useState(initial) {}\n"}).items():
        (package / path).parent.mkdir(parents=True, exist_ok=True)
        (package / path).write_text(text, encoding="utf-8", newline="\n")
    return package


def test_a_python_environments_library_is_read_by_its_import_path(tmp_path) -> None:
    root = _repository(tmp_path)
    python_environment(root)
    source = Source.of(root, exclude=(), installed=True)
    got = source.gathered(["python:httpx/_client.py"], [], [])
    assert "def send(self, request, *, timeout=5.0):" in got.shown and got.read == ("python:httpx/_client.py (whole)",)
    assert "httpx 0.28.1" in source.tree()
    assert source.within("python:httpx/_client.py", 3) == "def send(self, request, *, timeout=5.0):"


def test_a_windows_environment_is_found_as_well(tmp_path) -> None:
    root = _repository(tmp_path)
    python_environment(root, windows=True)
    (found,) = environments(root)
    assert (found.scheme, found.where) == ("python", ".venv") and "httpx/_client.py" in found.paths


def test_a_node_package_is_listed_and_read(tmp_path) -> None:
    root = _repository(tmp_path)
    _node(root)
    _node(root, "@scope/kit", {"lib/index.js": "export const kit = 1\n", "node_modules/inner/x.js": "nested\n"})
    source = Source.of(root, exclude=(), installed=True)
    got = source.gathered(["node:react/index.js"], ["node:react", "node:@scope/kit"], [])
    assert "export function useState" in got.shown and "node:react/index.js" in got.shown
    assert "node:@scope/kit/lib/index.js" in got.shown and "inner" not in got.shown, "a nested node_modules is skipped"
    assert "react 19.2.0" in source.tree() and "@scope/kit 19.2.0" in source.tree()


def test_a_record_line_outside_site_packages_is_never_listed(tmp_path) -> None:
    root = _repository(tmp_path)
    python_environment(root)
    (found,) = environments(root)
    assert not [path for path in found.paths if path.startswith("..") or "__pycache__" in path or "dist-info" in path]


@pytest.mark.skipif(os.name == "nt", reason="a link needs a privilege on Windows that a test run does not hold")
def test_a_linked_package_is_not_read(tmp_path) -> None:
    root = _repository(tmp_path)
    elsewhere = tmp_path.parent / f"{tmp_path.name}-elsewhere"
    elsewhere.mkdir()
    (elsewhere / "package.json").write_text(json.dumps({"name": "linked", "version": "1.0.0"}), encoding="utf-8")
    (elsewhere / "index.js").write_text("secret = 1\n", encoding="utf-8")
    (root / "node_modules").mkdir()
    (root / "node_modules" / "linked").symlink_to(elsewhere, target_is_directory=True)
    source = Source.of(root, exclude=(), installed=True)
    got = source.gathered(["node:linked/index.js"], [], [])
    assert "secret = 1" not in got.shown


def test_a_library_holding_a_key_is_withheld(tmp_path) -> None:
    root = _repository(tmp_path)
    python_environment(root, files={"httpx/__init__.py": "x = 1\n", "httpx/fixture.py": KEY})
    source = Source.of(root, exclude=(), installed=True)
    got = source.gathered(["python:httpx/fixture.py"], [], [])
    assert "b3BlbnNzaC1rZXk" not in got.shown and any("private key" in line for line in got.left_out)


def test_libraries_are_not_searched_and_name_no_repository(tmp_path) -> None:
    root = _repository(tmp_path)
    python_environment(root)
    source = Source.of(root, exclude=(), installed=True)
    got = source.gathered([], [], ["httpx"])
    assert "src/app.py" in got.shown and "python:" not in got.shown
    assert source.names == () and source.commits() == {}


def test_no_library_is_read_unless_asked_for(tmp_path) -> None:
    root = _repository(tmp_path)
    python_environment(root)
    source = Source.of(root, exclude=())
    got = source.gathered(["python:httpx/_client.py"], [], [])
    assert "def send" not in got.shown and "httpx 0.28.1" not in source.tree()


def test_an_excluded_environment_or_package_is_never_read(tmp_path) -> None:
    """Found by review: `[repository] exclude` kept a private package out of the repository's files, and not out of
    the libraries a reading opens."""
    root = _repository(tmp_path)
    python_environment(root, {"httpx/__init__.py": "x = 1\n", "httpx/secret_keys.py": "token = 1\n"})
    _node(root)
    _node(root, "@corp/sdk", {"index.js": "internal = 1\n"})
    source = Source.of(root, exclude=("@corp", "secret_*.py"), installed=True)
    got = source.gathered(["node:@corp/sdk/index.js", "python:httpx/secret_keys.py", "node:react/index.js"], [], [])
    assert "internal = 1" not in got.shown and "token = 1" not in got.shown and "useState" in got.shown
    assert "@corp/sdk" not in source.tree()
    assert "node (node_modules)" not in Source.of(root, exclude=("node_modules",), installed=True).tree()


@pytest.mark.skipif(os.name == "nt", reason="a folder's permissions do not shut a reader out on Windows")
def test_an_unreadable_package_is_left_out_and_named_and_stops_nothing(tmp_path) -> None:
    """Found by review: one folder a reader may not open stopped the whole propose, after triage was paid for."""
    root = _repository(tmp_path)
    _node(root)
    locked = _node(root, "locked")
    (locked / "lib").mkdir()
    (locked / "lib").chmod(0)
    try:
        source = Source.of(root, exclude=(), installed=True)
        assert "react 19.2.0" in source.tree() and "not read: locked" in source.tree()
    finally:
        (locked / "lib").chmod(0o755)


def test_a_record_csv_cannot_read_leaves_its_distribution_out(tmp_path) -> None:
    root = _repository(tmp_path)
    site = python_environment(root)
    (site / "httpx-0.28.1.dist-info" / "RECORD").write_text('"' + "x" * 200_000 + "\n", encoding="utf-8")
    (found,) = environments(root)
    assert not found.packages and "httpx" in " ".join(found.unread)


def test_a_library_past_the_cap_is_named_as_not_read_and_not_listed(tmp_path, monkeypatch) -> None:
    """Found by review: libraries past the cap stayed listed with their version, and every file asked of them was
    said to be no file."""
    from adk_spec.workspace import installed

    root = _repository(tmp_path)
    _node(root, "alpha", {"a.js": "1\n", "b.js": "2\n"})
    _node(root, "zeta", {"z.js": "3\n", "y.js": "4\n"})
    monkeypatch.setattr(installed, "LIBRARY_MAX_PATHS", 4)
    (found,) = environments(root)
    assert [name for name, _version, _tops in found.packages] == ["alpha"] and "zeta" in " ".join(found.unread)


def test_only_modules_are_shown_as_a_distributions_imports(tmp_path) -> None:
    root = _repository(tmp_path)
    files = {"yaml/__init__.py": "x = 1\n", "README.md": "# r\n", "_yaml.pyi": "y: int\n"}
    python_environment(root, files)
    (found,) = environments(root)
    ((_name, _version, tops),) = found.packages
    assert tops == ("_yaml", "yaml")
