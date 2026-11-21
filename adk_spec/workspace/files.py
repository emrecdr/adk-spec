"""Text files as the workspace reads and writes them: UTF-8, LF, one final newline, and written whole or not at all.

A file a Windows editor saved with a byte-order mark and CRLF line ends reads as its LF twin. A write goes to a
temporary file in the same folder, which is closed and then moved over the target: Windows moves no open file, and a
reader never sees half a file.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Mapping
from pathlib import Path

from ..domain.text import normalise


class NotTextError(ValueError):
    """A file that is not UTF-8 text."""


def read_text(path: Path) -> str:
    """The text of `path`, its byte-order mark dropped and its line ends as LF."""
    try:
        text = path.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise NotTextError(
            f"{path} is not UTF-8. Save it as UTF-8: Windows PowerShell 5.1's `>` writes UTF-16"
        ) from exc
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _staged(path: Path, text: str) -> Path:
    """`text`, normalised, in a closed temporary file beside `path`, whose folders are made."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    staged = Path(name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as out:
            out.write(normalise(text))
    except BaseException:
        staged.unlink(missing_ok=True)
        raise
    return staged


def write_text(path: Path, text: str) -> None:
    """`text` written to `path`: normalised, and moved into place whole. A write that fails leaves the old file and
    no temporary one."""
    write_all({path: text})


def write_all(files: Mapping[Path, str]) -> None:
    """Every text written to its path, none moved into place until all are on disk: a text that cannot be written
    leaves every target as it was."""
    staged: list[tuple[Path, Path]] = []
    try:
        for path, text in files.items():
            staged.append((_staged(path, text), path))
        for temporary, path in staged:
            os.replace(temporary, path)
    except BaseException:
        for temporary, _path in staged:
            temporary.unlink(missing_ok=True)
        raise
