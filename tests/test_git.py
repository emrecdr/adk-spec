"""Read-only git: started by its full path, under an environment of this package's own, and stopped past its time."""

from __future__ import annotations

import os
import stat

import pytest
from conftest import repository

from adk_spec.workspace import git as layer
from adk_spec.workspace.git import GitError, diff, files, git, head, is_repository, on_path, resolves


def changed(root) -> None:
    (root / "src/app.py").write_text("def login():\n    return passkey()\n", encoding="utf-8")


def test_a_diff_is_the_base_against_the_working_tree_without_the_spec_tree(tmp_path) -> None:
    base = repository(tmp_path, {"src/app.py": "def login():\n    return password()\n", ".spec/config.toml": "# a\n"})
    changed(tmp_path)
    (tmp_path / ".spec/config.toml").write_text("# changed\n", encoding="utf-8")
    text = diff(tmp_path, base)
    assert "+    return passkey()" in text and "-    return password()" in text and ".spec/" not in text
    assert "+++ b/src/app.py" in text


def test_a_file_git_does_not_track_yet_reads_as_added(tmp_path) -> None:
    """New work is new files, and a person may not have added them yet: left out, the diff would hide the change."""
    base = repository(tmp_path)
    (tmp_path / "src/new.py").write_text("def passkey():\n    return True\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("build/\n", encoding="utf-8")
    (tmp_path / "build").mkdir()
    (tmp_path / "build/out.txt").write_text("generated\n", encoding="utf-8")
    text = diff(tmp_path, base)
    assert "+++ b/src/new.py" in text and "+def passkey():" in text and "generated" not in text
    assert files(tmp_path) == [".gitignore", "src/app.py", "src/new.py"], "what git tracks or would: nothing ignored"


def test_a_diff_of_a_subfolder_names_paths_from_that_folder(tmp_path) -> None:
    base = repository(tmp_path, {"service/src/app.py": "a = 1\n", "other/x.py": "x = 1\n"})
    (tmp_path / "service/src/app.py").write_text("a = 2\n", encoding="utf-8")
    (tmp_path / "other/x.py").write_text("x = 2\n", encoding="utf-8")
    text = diff(tmp_path / "service", base)
    assert "+++ b/src/app.py" in text and "other/" not in text
    assert files(tmp_path / "service") == ["src/app.py"]


def test_git_is_never_started_from_the_current_folder(tmp_path, monkeypatch) -> None:
    repository(tmp_path)
    monkeypatch.setenv("PATH", f".{os.pathsep}relative/bin")
    monkeypatch.chdir(tmp_path)
    assert on_path("git") is None
    with pytest.raises(GitError, match="PATH"):
        git(tmp_path, "status")


def test_a_persons_own_git_settings_change_nothing(tmp_path, monkeypatch) -> None:
    base = repository(tmp_path / "one")
    repository(tmp_path / "other", {"else.py": "x = 1\n"})
    changed(tmp_path / "one")
    plain = diff(tmp_path / "one", base)
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "other/.git"))
    monkeypatch.setenv("GIT_EXTERNAL_DIFF", "a-program-that-must-not-run")
    monkeypatch.setenv("GIT_DIFF_OPTS", "-u0")
    assert diff(tmp_path / "one", base) == plain and "def login():" in plain, "the context line is still there"


def test_a_folder_that_is_no_repository_and_a_ref_that_is_none(tmp_path) -> None:
    assert not is_repository(tmp_path) and head(tmp_path) is None
    sha = repository(tmp_path / "repo")
    assert is_repository(tmp_path / "repo") and head(tmp_path / "repo") == sha and len(sha) == 40
    assert resolves(tmp_path / "repo", "main") == sha and resolves(tmp_path / "repo", "no-such") is None
    assert resolves(tmp_path / "repo", "--version") is None, "an option is no revision"
    with pytest.raises(GitError, match="no-such"):
        diff(tmp_path / "repo", "no-such")
    with pytest.raises(GitError):
        diff(tmp_path, "HEAD")


def test_a_repository_with_no_commit_has_no_head(tmp_path) -> None:
    repository(tmp_path / "full")
    git(tmp_path, "init", "-q", str(tmp_path / "empty"))
    assert is_repository(tmp_path / "empty") and head(tmp_path / "empty") is None


@pytest.mark.skipif(os.name == "nt", reason="the stand-in is a shell script")
def test_a_command_past_its_time_is_stopped(tmp_path, monkeypatch) -> None:
    stand_in = tmp_path / "bin/git"
    stand_in.parent.mkdir()
    stand_in.write_text("#!/bin/sh\nexec /bin/sleep 5\n", encoding="utf-8")  # PATH holds this folder alone
    stand_in.chmod(stand_in.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", str(stand_in.parent))
    monkeypatch.setattr(layer, "GIT_TIMEOUT_S", 0.2)
    with pytest.raises(GitError, match=r"did not answer within 0\.2 s"):
        git(tmp_path, "status")


def test_a_failure_is_gits_own_first_line_and_never_an_empty_answer(tmp_path) -> None:
    repository(tmp_path)
    with pytest.raises(GitError, match="git cat-file failed"):
        git(tmp_path, "cat-file", "-p", "0" * 40)
