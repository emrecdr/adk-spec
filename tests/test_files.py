"""Writing a change's files as one set: on Windows, a file another program holds a moment is written all the same."""

from __future__ import annotations

import os

import pytest

from adk_spec.workspace import files


def test_on_windows_a_file_held_a_moment_by_another_program_is_written_all_the_same(tmp_path, monkeypatch) -> None:
    """Found by an outside audit: on Windows an antivirus or an indexer holds a file a moment, and replacing it fails
    with PermissionError where it would succeed a moment later."""
    real, failed = os.replace, []

    def held_twice(source, target):
        if len(failed) < 2:
            failed.append(target)
            raise PermissionError("held by another program")
        real(source, target)

    monkeypatch.setattr(files, "WINDOWS", True)
    monkeypatch.setattr(files.os, "replace", held_twice)
    files.write_all({tmp_path / "a.md": "text\n"})
    assert (tmp_path / "a.md").read_text(encoding="utf-8") == "text\n" and len(failed) == 2


def test_elsewhere_a_permission_error_is_not_retried(tmp_path, monkeypatch) -> None:
    """Outside Windows a PermissionError is a real refusal: it is said at once."""
    calls = []

    def refused(_source, target):
        calls.append(target)
        raise PermissionError("not allowed")

    monkeypatch.setattr(files, "WINDOWS", False)
    monkeypatch.setattr(files.os, "replace", refused)
    with pytest.raises(PermissionError):
        files.write_all({tmp_path / "a.md": "text\n"})
    assert len(calls) == 1
