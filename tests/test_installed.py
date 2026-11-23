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


def test_a_library_path_named_through_its_environment_is_read_by_its_own_name(tmp_path) -> None:
    """Found live, phase 15: a survey asked for python:.venv/lib/python3.11/site-packages/httpx/_client.py, the
    environment's path with a version of its own making, and was told there was no such file."""
    root = _repository(tmp_path)
    python_environment(root)
    _node(root)
    source = Source.of(root, exclude=(), installed=True)
    asked = ["python:.venv/lib/python3.11/site-packages/httpx/_client.py", "node:node_modules/react/index.js"]
    got = source.gathered(asked, ["python:/anywhere/site-packages/httpx"], [])
    assert "def send(self, request" in got.shown and "export function useState" in got.shown
    assert got.read == ("python:httpx/_client.py (whole)", "node:react/index.js (whole)")
    assert "=== python:httpx/ (" in got.shown, "a folder named so is listed as well"


def test_the_library_list_shows_a_real_path_to_name_a_file_by(tmp_path) -> None:
    root = _repository(tmp_path)
    python_environment(root)
    assert "such as python:httpx/__init__.py" in Source.of(root, exclude=(), installed=True).tree()


def test_a_folder_pattern_keeps_a_librarys_files_out_as_it_does_the_repositorys(tmp_path) -> None:
    """Found by the third audit: a pattern naming a folder kept nothing of an installed library out, since a
    library's file was matched against the pattern whole."""
    root = _repository(tmp_path)
    _node(root, "leftpad", {"index.js": "module.exports = 1\n"})
    _node(root)
    for pattern in ("node_modules/leftpad", "node_modules/leftpad/", "leftpad/"):
        source = Source.of(root, exclude=(pattern,), installed=True)
        assert "leftpad" not in source.tree() and "react 19.2.0" in source.tree(), pattern


def test_once_the_cap_is_full_no_further_package_is_walked(tmp_path, monkeypatch) -> None:
    """Found by the third audit: every package of a large `node_modules` was walked whole after the cap was full,
    for nothing. They are counted, not walked, and not named: a name could be one an exclusion keeps out."""
    from adk_spec.workspace import installed

    root = _repository(tmp_path)
    _node(root, "alpha", {"a.js": "1\n", "b.js": "2\n", "c.js": "3\n"})  # with its package.json: four files
    for name in ("beta", "gamma"):
        _node(root, name, {"x.js": "4\n"})
    monkeypatch.setattr(installed, "LIBRARY_MAX_PATHS", 4)
    walked: list[str] = []
    real = installed._walked
    monkeypatch.setattr(installed, "_walked", lambda folder: walked.append(folder.name) or real(folder))
    (found,) = environments(root)
    assert walked == ["alpha"] and [name for name, _version, _tops in found.packages] == ["alpha"]
    assert found.unread == ("2 more packages: past the 4 files an environment lists",)


def test_once_a_package_overflows_the_cap_no_further_one_is_walked(tmp_path, monkeypatch) -> None:
    """Found by the code review: the walk stopped only where the packages filled the cap exactly; one that overflowed
    it was turned away, and every package after it was walked whole as before."""
    from adk_spec.workspace import installed

    root = _repository(tmp_path)
    _node(root, "alpha", {"a.js": "1\n"})  # with its package.json: two files
    _node(root, "beta", {"x.js": "2\n", "y.js": "3\n", "z.js": "4\n"})  # four: past the cap of three
    _node(root, "gamma", {"x.js": "5\n"})
    monkeypatch.setattr(installed, "LIBRARY_MAX_PATHS", 3)
    walked: list[str] = []
    real = installed._walked
    monkeypatch.setattr(installed, "_walked", lambda folder: walked.append(folder.name) or real(folder))
    (found,) = environments(root)
    assert walked == ["alpha", "beta"]
    assert found.unread == (
        "beta: past the 3 files an environment lists",
        "1 more package: past the 3 files an environment lists",
    )


def test_an_excluded_package_is_not_even_counted_past_the_cap(tmp_path, monkeypatch) -> None:
    from adk_spec.workspace import installed

    root = _repository(tmp_path)
    _node(root, "alpha", {"a.js": "1\n", "b.js": "2\n"})
    _node(root, "zcorp-sdk", {"x.js": "3\n"})  # found after the cap is full
    monkeypatch.setattr(installed, "LIBRARY_MAX_PATHS", 3)
    (found,) = environments(root, exclude=("node_modules/zcorp-sdk/**",))
    assert not found.unread, "its existence is no part of what a stage is told"


def test_a_pattern_in_capitals_keeps_a_librarys_files_out_as_it_keeps_the_repositorys(tmp_path) -> None:
    """Found by the code review: a pattern's letters matched in either case for git, and only in lower case for an
    installed library."""
    root = _repository(tmp_path)
    _node(root, "leftpad", {"index.js": "1\n", "KEY.PEM": "k\n"})
    _node(root)
    source = Source.of(root, exclude=("Leftpad/",), installed=True)
    assert "leftpad" not in source.tree() and "react 19.2.0" in source.tree()
    (found,) = environments(root, exclude=("*.PEM",))
    assert "leftpad/KEY.PEM" not in found.paths and "leftpad/index.js" in found.paths
