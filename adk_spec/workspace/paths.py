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


def refuse_links(top: Path) -> None:
    """`PathError` naming the first link or junction at or under `top`, said from the folder that holds `top`.
    Found by the audit of 25 November: a link under `.spec` had a command read a file from anywhere and send it to a
    model, or remove files from another folder; refused once, where the tree is opened, rather than at each of the
    reads and writes."""
    for found in (top, *_under(top)):
        if found.is_symlink() or found.is_junction():
            shown = found.relative_to(top.parent).as_posix()
            raise PathError(
                f"`{shown}` is a link, which could lead out of {top.parent}. Replace it with a real file or folder"
            )


def _under(top: Path):
    """Every file and folder under `top`, a folder's own before what is in its folders; a link is never followed."""
    for folder, folders, files in os.walk(top):
        yield from (Path(folder, name) for name in sorted([*folders, *files]))


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
        neighbours = _folded(str(parent))
    except OSError:  # the folder is not there yet: nothing to collide with
        return
    for name in neighbours.get(part.casefold(), ()):
        if name != part:
            raise PathError(f"`{part}` differs from `{name}` only by case, and some systems read both as one file")


#: Each folder's names by their case-folded form, beside what it said of itself when it was listed.
_LISTED: dict[str, tuple[tuple[int, int, int], dict[str, list[str]]]] = {}


def _folded(parent: str) -> dict[str, list[str]]:
    """The names a folder holds, by their case-folded form: listed once while it does not change, and again once it
    does. Found by the third audit: listed for each lookup, reading 1,000 changes listed `changes/` 1,000 times."""
    held_by = os.stat(parent)
    # Its time of last change, and its size and links, which move with what it holds where a coarse file system's
    # stamp did not: found by the code review, a name made in the same tick as the listing went unseen.
    stamp = (held_by.st_mtime_ns, held_by.st_size, held_by.st_nlink)
    held = _LISTED.get(parent)
    if held is None or held[0] != stamp:
        folded: dict[str, list[str]] = {}
        for name in os.listdir(parent):
            folded.setdefault(name.casefold(), []).append(name)
        held = _LISTED[parent] = (stamp, folded)
    return held[1]
