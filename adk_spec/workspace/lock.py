"""One writer at a time: a lock file a writing command holds for its whole run.

A command reads the workspace, may spend minutes with a model, and then writes. Two at once could each number a new
requirement the same, or fold two changes into one spec in turn. The lock is a file made exclusively, which fails
on every system where another run made it first.

The file names the process that holds it and its machine. A lock whose process ended on this machine, killed by the
system or by a closed terminal before it could let go, is taken over; one held by a running process, or by another
machine on a shared drive, is left alone.
"""

from __future__ import annotations

import os
import platform
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from .layout import LOCK, TAKING, Workspace, WorkspaceError

#: What Windows says of a process that has not ended, asked for its exit code.
_STILL_ACTIVE = 259


@contextmanager
def held(workspace: Workspace) -> Generator[None]:
    """The workspace's lock, for the block. `WorkspaceError` names the file where another run holds it; that run's
    lock is left alone. A lock a process on this machine left when it ended is taken over."""
    path, mine = workspace.home / LOCK, _mark()
    if not _taken(path, mine) and not _taken_over(path, mine):
        raise WorkspaceError(_refusal(workspace, path))
    try:
        yield
    finally:
        # Removed while it says what this run wrote: a lock a person removed, and another run then took, is that
        # run's. Not the machine's name read again: found by review, a laptop's follows its network.
        if _said(path) == mine:
            path.unlink(missing_ok=True)


def _mark() -> str:
    """What a lock, or a takeover's marker, says of the run that made it: its process and its machine."""
    return f"{os.getpid()} {platform.node()}"


def _said(path: Path) -> str:
    """What a lock, or a marker, says of its run: nothing where it cannot be read."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _refusal(workspace: Workspace, path: Path) -> str:
    marker = path.with_name(TAKING)  # where a run stopped part way through a takeover left it
    also = f", and {workspace.shown(marker)}, which a takeover stopped part way left" if marker.exists() else ""
    return (
        f"{workspace.shown(path)} is held by another adk-spec run. Wait for it; or, where none is running, remove the "
        f"file{also}"
    )


def _taken(path: Path, mine: str) -> bool:
    """Whether the file was made, a lock or a marker, saying `mine`. Where another run made it first, it is not."""
    try:
        with path.open("xb") as made:  # made exclusively: it fails where the file is there
            made.write(mine.encode())
    except FileExistsError:
        return False
    return True


def _taken_over(path: Path, mine: str) -> bool:
    """Whether a lock left by an ended process of this machine was removed and the lock made anew. One run at a time
    takes over, under a marker it makes exclusively, and reads the lock again inside it: two runs that found the same
    lock left behind cannot both remove it, nor remove the one a run made after it."""
    marker = path.with_name(TAKING)
    if not _taken(marker, mine):  # another run is taking it over
        return False
    try:
        if not _left(path):
            return False
        path.unlink(missing_ok=True)
        return _taken(path, mine)
    finally:
        marker.unlink(missing_ok=True)


def _left(path: Path) -> bool:
    """Whether the lock was left by a process of this machine that has ended. A lock that names no machine, as an
    older adk-spec's, or names another machine, or a running process, is not: on a shared drive its run may be on
    another machine."""
    words = _said(path).split()
    if len(words) < 2 or not words[0].isdigit():
        return False
    return words[1] == platform.node() and not _alive(int(words[0]))


def _alive(pid: int) -> bool:
    """Whether process `pid` runs. Where that cannot be told, it is taken to run: a lock is never taken from a run."""
    if os.name == "nt":
        return _alive_on_windows(pid)
    try:
        os.kill(pid, 0)  # no signal: whether the process is there
    except ProcessLookupError:
        return False
    except OSError:  # there, and another user's
        return True
    return True


def _alive_on_windows(pid: int) -> bool:
    """On Windows `os.kill` would end the process: the system is asked for its exit code instead."""
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)  # pyrefly: ignore[missing-attribute]
    # Each call's types declared: ctypes takes a result for a C int by default, and a handle is a pointer's width.
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    kernel.GetExitCodeProcess.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        # ERROR_INVALID_PARAMETER: no such process; anything else, it runs
        return ctypes.get_last_error() != 87  # pyrefly: ignore[missing-attribute]
    try:
        code = wintypes.DWORD()
        return not kernel.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value == _STILL_ACTIVE
    finally:
        kernel.CloseHandle(handle)
