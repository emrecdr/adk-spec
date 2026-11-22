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
    text = diff(tmp_path, base, exclude=())
    assert "+    return passkey()" in text and "-    return password()" in text and ".spec/" not in text
    assert "+++ b/src/app.py" in text


def test_a_file_git_does_not_track_yet_reads_as_added(tmp_path) -> None:
    """New work is new files, and a person may not have added them yet: left out, the diff would hide the change."""
    base = repository(tmp_path)
    (tmp_path / "src/new.py").write_text("def passkey():\n    return True\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("build/\n", encoding="utf-8")
    (tmp_path / "build").mkdir()
    (tmp_path / "build/out.txt").write_text("generated\n", encoding="utf-8")
    text = diff(tmp_path, base, exclude=())
    assert "+++ b/src/new.py" in text and "+def passkey():" in text and "generated" not in text
    assert files(tmp_path, exclude=()) == [".gitignore", "src/app.py", "src/new.py"], (
        "what git tracks or would: nothing ignored"
    )


def test_a_diff_of_a_subfolder_names_paths_from_that_folder(tmp_path) -> None:
    base = repository(tmp_path, {"service/src/app.py": "a = 1\n", "other/x.py": "x = 1\n"})
    (tmp_path / "service/src/app.py").write_text("a = 2\n", encoding="utf-8")
    (tmp_path / "other/x.py").write_text("x = 2\n", encoding="utf-8")
    text = diff(tmp_path / "service", base, exclude=())
    assert "+++ b/src/app.py" in text and "other/" not in text
    assert files(tmp_path / "service", exclude=()) == ["src/app.py"]


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
    plain = diff(tmp_path / "one", base, exclude=())
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "other/.git"))
    monkeypatch.setenv("GIT_EXTERNAL_DIFF", "a-program-that-must-not-run")
    monkeypatch.setenv("GIT_DIFF_OPTS", "-u0")
    assert diff(tmp_path / "one", base, exclude=()) == plain and "def login():" in plain, (
        "the context line is still there"
    )


def test_a_folder_that_is_no_repository_and_a_ref_that_is_none(tmp_path) -> None:
    assert not is_repository(tmp_path) and head(tmp_path) is None
    sha = repository(tmp_path / "repo")
    assert is_repository(tmp_path / "repo") and head(tmp_path / "repo") == sha and len(sha) == 40
    assert resolves(tmp_path / "repo", "main") == sha and resolves(tmp_path / "repo", "no-such") is None
    assert resolves(tmp_path / "repo", "--version") is None, "an option is no revision"
    with pytest.raises(GitError, match="no-such"):
        diff(tmp_path / "repo", "no-such", exclude=())
    with pytest.raises(GitError):
        diff(tmp_path, "HEAD", exclude=())


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


def test_what_a_person_ignores_everywhere_is_no_new_work(tmp_path, monkeypatch) -> None:
    """Found by the code review: with a person's own git config left unread, the files they ignore in every
    repository, a `.env` among them, were read as new work, sent to the model and kept in the recording."""
    home = tmp_path / "home"
    home.mkdir()
    (home / ".gitignore_global").write_text(".env\n.idea/\n", encoding="utf-8")
    (home / ".gitconfig").write_text("[core]\n\texcludesfile = ~/.gitignore_global\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    base = repository(tmp_path / "repo")
    (tmp_path / "repo/.env").write_text("API_KEY=supersecret-value\n", encoding="utf-8")
    (tmp_path / "repo/.idea").mkdir()
    (tmp_path / "repo/.idea/ws.xml").write_text("<x/>\n", encoding="utf-8")
    changed(tmp_path / "repo")
    text = diff(tmp_path / "repo", base, exclude=())
    assert "supersecret-value" not in text and ".idea" not in text and "+    return passkey()" in text
    assert files(tmp_path / "repo", exclude=()) == ["src/app.py"]


def test_a_subfolder_of_a_repository_another_account_owns_is_still_a_repository(tmp_path, monkeypatch) -> None:
    """Found by the code review: the folder named was trusted where git asks about the repository's top, so a
    workspace in a subfolder of a bind mount or a shared folder was told it is in no git repository."""
    sha = repository(tmp_path / "repo", {"service/src/app.py": "a = 1\n"})
    own = layer._environment
    monkeypatch.setattr(layer, "_environment", lambda root: {**own(root), "GIT_TEST_ASSUME_DIFFERENT_OWNER": "1"})
    assert is_repository(tmp_path / "repo/service") and head(tmp_path / "repo/service") == sha


def test_a_refusal_of_gits_that_is_no_missing_repository_is_said_and_never_read_as_none(tmp_path, monkeypatch) -> None:
    repository(tmp_path / "repo")
    own = layer._environment

    def distrusted(root):
        env = {**own(root), "GIT_TEST_ASSUME_DIFFERENT_OWNER": "1"}
        return {name: value for name, value in env.items() if not name.startswith("GIT_CONFIG_")}

    monkeypatch.setattr(layer, "_environment", distrusted)
    with pytest.raises(GitError, match="dubious ownership"):
        is_repository(tmp_path / "repo")
    with pytest.raises(GitError, match="dubious ownership"):
        head(tmp_path / "repo")


def test_a_repositorys_own_diff_settings_change_no_path(tmp_path) -> None:
    from conftest import _git

    base = repository(tmp_path)
    _git(tmp_path, "config", "diff.noprefix", "true")
    _git(tmp_path, "config", "diff.mnemonicPrefix", "true")
    changed(tmp_path)
    assert "+++ b/src/app.py" in diff(tmp_path, base, exclude=())


# Paths a person keeps out of every command: `[repository] exclude`.


def test_an_excluded_path_is_never_listed(tmp_path) -> None:
    repository(tmp_path, {"src/app.py": "x = 1\n", "vendor/lib.py": "y = 2\n", "keys/prod.pem": "k\n"})
    (tmp_path / "vendor/untracked.py").write_text("z = 3\n", encoding="utf-8")
    assert files(tmp_path, exclude=()) == ["keys/prod.pem", "src/app.py", "vendor/lib.py", "vendor/untracked.py"]
    assert files(tmp_path, exclude=("vendor/**", "**/*.pem")) == ["src/app.py"]


def test_an_excluded_path_is_no_part_of_the_diff_tracked_or_not(tmp_path) -> None:
    commit = repository(tmp_path, {"src/app.py": "x = 1\n", "vendor/lib.py": "y = 2\n"})
    for path, text in {
        "src/app.py": "x = 2\n",
        "vendor/lib.py": "y = 3\n",
        "vendor/new.py": "n = 1\n",
        "src/new.py": "m = 1\n",
    }.items():
        (tmp_path / path).write_text(text, encoding="utf-8")
    whole, kept = diff(tmp_path, commit, exclude=()), diff(tmp_path, commit, exclude=("vendor/**",))
    assert "vendor/lib.py" in whole and "vendor/new.py" in whole
    assert "src/app.py" in kept and "src/new.py" in kept and "vendor" not in kept
