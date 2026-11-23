"""The project's installed libraries as a reading may see them: its Python environment and its `node_modules`, read
offline at the versions it runs, by the rules a repository's files are read by."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from conftest import repository

from adk_spec.workspace.installed import environments
from adk_spec.workspace.source import Source

CLIENT = 'class Client:\n    def send(self, request, *, timeout=5.0):\n        """Send one request."""\n'
KEY = "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQ\n"


def _repository(root: Path) -> Path:
    repository(root, {".gitignore": ".venv/\nvenv/\nnode_modules/\n", "src/app.py": "import httpx\n"})
    return root


def _python(root: Path, *, windows: bool = False, files: dict[str, str] | None = None) -> Path:
    """A `.venv` holding httpx 0.28.1: its files, its `METADATA` and the `RECORD` listing them."""
    site = root / ".venv" / ("Lib" if windows else "lib/python3.14") / "site-packages"
    held = files or {"httpx/__init__.py": "from ._client import Client\n", "httpx/_client.py": CLIENT}
    for path, text in held.items():
        (site / path).parent.mkdir(parents=True, exist_ok=True)
        (site / path).write_text(text, encoding="utf-8", newline="\n")
    info = site / "httpx-0.28.1.dist-info"
    info.mkdir(parents=True, exist_ok=True)
    (info / "METADATA").write_text("Metadata-Version: 2.4\nName: httpx\nVersion: 0.28.1\n", encoding="utf-8")
    listed = [*held, "httpx-0.28.1.dist-info/METADATA", "httpx/__pycache__/x.cpython-314.pyc", "../../bin/httpx"]
    (info / "RECORD").write_text("".join(f"{path},sha256=x,1\n" for path in listed), encoding="utf-8")
    return site


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
    _python(root)
    source = Source.of(root, exclude=(), installed=True)
    got = source.gathered(["python:httpx/_client.py"], [], [])
    assert "def send(self, request, *, timeout=5.0):" in got.shown and got.read == ("python:httpx/_client.py (whole)",)
    assert "httpx 0.28.1" in source.tree()
    assert source.within("python:httpx/_client.py", 3) == "def send(self, request, *, timeout=5.0):"


def test_a_windows_environment_is_found_as_well(tmp_path) -> None:
    root = _repository(tmp_path)
    _python(root, windows=True)
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
    _python(root)
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
    _python(root, files={"httpx/__init__.py": "x = 1\n", "httpx/fixture.py": KEY})
    source = Source.of(root, exclude=(), installed=True)
    got = source.gathered(["python:httpx/fixture.py"], [], [])
    assert "b3BlbnNzaC1rZXk" not in got.shown and any("private key" in line for line in got.left_out)


def test_libraries_are_not_searched_and_name_no_repository(tmp_path) -> None:
    root = _repository(tmp_path)
    _python(root)
    source = Source.of(root, exclude=(), installed=True)
    got = source.gathered([], [], ["httpx"])
    assert "src/app.py" in got.shown and "python:" not in got.shown
    assert source.names == () and source.commits() == {}


def test_no_library_is_read_unless_asked_for(tmp_path) -> None:
    root = _repository(tmp_path)
    _python(root)
    source = Source.of(root, exclude=())
    got = source.gathered(["python:httpx/_client.py"], [], [])
    assert "def send" not in got.shown and "httpx 0.28.1" not in source.tree()
