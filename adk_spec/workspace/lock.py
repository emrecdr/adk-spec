"""One writer at a time: a lock file a writing command holds for its whole run.

A command reads the workspace, may spend minutes with a model, and then writes. Two at once could each number a new
requirement the same, or fold two changes into one spec in turn. The lock is a file made exclusively, which fails
on every system where another run made it first.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from contextlib import contextmanager

from .layout import Workspace, WorkspaceError

LOCK = ".lock"


@contextmanager
def held(workspace: Workspace) -> Generator[None]:
    """The workspace's lock, for the block. `WorkspaceError` names the file where another run holds it; that run's
    lock is left alone."""
    path = workspace.home / LOCK
    try:
        with path.open("xb") as lock:  # made exclusively: it fails where the file is there
            lock.write(str(os.getpid()).encode("ascii"))
    except FileExistsError as exc:
        raise WorkspaceError(
            f"{workspace.shown(path)} is held by another adk-spec run. Wait for it; or, where none is running, remove "
            "the file"
        ) from exc
    try:
        yield
    finally:
        path.unlink(missing_ok=True)
