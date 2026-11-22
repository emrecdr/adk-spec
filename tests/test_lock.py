"""The workspace's lock: one writing run at a time, and a lock a run left behind when it ended taken over."""

from __future__ import annotations

import os
import platform
import subprocess
import sys

import pytest

from adk_spec.workspace.layout import Workspace, WorkspaceError
from adk_spec.workspace.lock import LOCK, held


def ended_pid() -> int:
    """The number of a process that ran and ended."""
    done = subprocess.Popen([sys.executable, "-c", "pass"])
    done.wait()
    return done.pid


@pytest.mark.skipif(os.name == "nt", reason="the ended process is told apart by the system's own means on Windows")
def test_a_lock_a_run_left_when_it_ended_is_taken_over(tmp_path) -> None:
    """Found by an outside audit: a run killed by the system left its lock, and every command after it was refused
    until a person removed the file by hand."""
    ws = Workspace.init(tmp_path)
    (ws.home / LOCK).write_text(f"{ended_pid()} {platform.node()}", encoding="ascii")
    with held(ws):
        assert (ws.home / LOCK).read_text(encoding="ascii").split()[0] == str(os.getpid())
    assert not (ws.home / LOCK).exists()


@pytest.mark.parametrize("holder", ["alive", "other host"])
def test_a_lock_a_running_process_or_another_machine_holds_is_refused(tmp_path, holder) -> None:
    ws = Workspace.init(tmp_path)
    line = f"{os.getpid()} {platform.node()}" if holder == "alive" else f"{ended_pid()} another-machine"
    (ws.home / LOCK).write_text(line, encoding="ascii")
    with pytest.raises(WorkspaceError, match="held by another adk-spec run"), held(ws):
        pass
    assert (ws.home / LOCK).read_text(encoding="ascii") == line, "another run's lock is left alone"
