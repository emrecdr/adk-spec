"""The path policy: where under a root the code may read and write, the same on every system.

A part is refused where any system could not hold it, or would hold it as something else: a name Windows reserves, a
character it forbids, a trailing dot or space, a link that leads out of the root, or a name that differs from a
neighbour only by case, which macOS and Windows read as the same file.
"""

from __future__ import annotations

import ntpath
import os
from pathlib import Path

#: Characters no part may hold: the two separators, a NUL, and what Windows forbids in a name.
FORBIDDEN = frozenset('/\\\x00<>:"|?*')


class PathError(ValueError):
    """A path the policy refuses: the part, and why."""


def inside(root: Path, *parts: str) -> Path:
    """`root` joined with `parts`, each held to the policy. `PathError` names the part and the reason."""
    path = root
    for part in parts:
        _refuse_name(part)
        _refuse_twin(path, part)
        path = path / part
        # Asked of the link itself, before anything is resolved: resolved, a link reads as an ordinary folder.
        if path.is_symlink() or path.is_junction():
            raise PathError(f"`{part}` is a link, which could lead out of {root}. Replace it with a real folder")
    return path


def _refuse_name(part: str) -> None:
    if part in ("", ".", ".."):
        raise PathError(f"`{part}` names no file or folder of its own")
    if held := sorted(FORBIDDEN & set(part)):
        raise PathError(f"`{part}` holds {held[0]!r}, which no file name may hold on every system")
    if ntpath.isreserved(part):  # a device name, or a trailing dot or space; the same answer on every system
        raise PathError(f"`{part}` is a name Windows reserves, or ends in a dot or a space")


def _refuse_twin(parent: Path, part: str) -> None:
    """Refuse `part` where its folder already holds a name equal to it but for case."""
    try:
        neighbours = os.listdir(parent)
    except OSError:  # the folder is not there yet: nothing to collide with
        return
    for name in neighbours:
        if name != part and name.casefold() == part.casefold():
            raise PathError(f"`{part}` differs from `{name}` only by case, and some systems read both as one file")
