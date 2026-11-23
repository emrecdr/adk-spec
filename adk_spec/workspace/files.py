"""Text files as the workspace reads and writes them: UTF-8, LF, one final newline, and written whole or not at all.

A file a Windows editor saved with a byte-order mark and CRLF line ends reads as its LF twin. A write goes to a
temporary file in the same folder, which is closed and then moved over the target: Windows moves no open file, and a
reader never sees half a file.
"""

from __future__ import annotations

import contextlib
import os
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path

from ..domain.text import normalise


class NotTextError(ValueError):
    """A file that is not UTF-8 text."""


#: Whether this is Windows, where another program, an antivirus or an indexer, holds a file a moment.
WINDOWS = os.name == "nt"
#: How often a move is tried there, and how long the first wait is: each wait doubles, a third of a second in all.
REPLACE_TRIES = 5
REPLACE_WAIT_S = 0.02


def read_text(path: Path) -> str:
    """The text of `path`, its byte-order mark dropped and its line ends as LF."""
    try:
        text = path.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise NotTextError(
            f"{path} is not UTF-8. Save it as UTF-8: Windows PowerShell 5.1's `>` writes UTF-16"
        ) from exc
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _mode_for(path: Path) -> int:
    """The mode a file written to `path` should have: the one it has, or the one this account gives a new file.
    A temporary file is made owner-only, and moved into place it would narrow what it replaced."""
    if path.exists():
        return path.stat().st_mode & 0o777
    mask = os.umask(0)
    os.umask(mask)
    return 0o666 & ~mask


def _staged(path: Path, text: str) -> Path:
    """`text`, normalised, in a closed temporary file beside `path`, whose folders are made."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    staged = Path(name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as out:
            out.write(normalise(text))
            out.flush()
            os.fsync(out.fileno())  # on disk before it replaces the file: a crash leaves the old text or the new
        if os.name != "nt":  # a Windows file has no owner, group and other modes
            staged.chmod(_mode_for(path))
    except BaseException:
        staged.unlink(missing_ok=True)
        raise
    return staged


def write_text(path: Path, text: str) -> None:
    """`text` written to `path`: normalised, and moved into place whole. A write that fails leaves the old file and
    no temporary one."""
    write_all({path: text})


def write_all(files: Mapping[Path, str]) -> None:
    """Every text written to its path, none moved into place until all are on disk. Where a move fails part way, as
    on a file another process holds open, each file already replaced is put back and each new one removed, so the
    set is written whole or not at all as far as the file system allows."""
    staged: list[tuple[Path, Path]] = []
    replaced: list[tuple[Path, bytes | None]] = []
    try:
        for path, text in files.items():
            staged.append((_staged(path, text), path))
        for temporary, path in staged:
            before = path.read_bytes() if path.is_file() else None
            _replace(temporary, path)
            replaced.append((path, before))
    except BaseException:
        for temporary, _path in staged:
            temporary.unlink(missing_ok=True)
        for path, before in reversed(replaced):
            with contextlib.suppress(OSError):
                if before is None:
                    path.unlink(missing_ok=True)
                else:
                    path.write_bytes(before)
        raise


def _replace(temporary: Path, path: Path) -> None:
    """`temporary` moved over `path`. On Windows a PermissionError is tried again a few times, briefly: a file another
    program holds a moment is free a moment later. Elsewhere it is a refusal, said at once."""
    for attempt in range(REPLACE_TRIES if WINDOWS else 1):
        try:
            os.replace(temporary, path)
            return
        except PermissionError:
            if attempt == REPLACE_TRIES - 1 or not WINDOWS:
                raise
            time.sleep(REPLACE_WAIT_S * 2**attempt)
