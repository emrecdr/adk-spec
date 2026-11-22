"""The workspace's lock: one writing run at a time, and a lock a run left behind when it ended taken over."""

from __future__ import annotations

import os
import platform
import subprocess
import sys

import pytest

from adk_spec.workspace.layout import Workspace, WorkspaceError
from adk_spec.workspace.lock import LOCK, TAKING, held

#: Each ended process's handle, kept open: Windows gives an ended process's number to another only once no handle
#: holds it, and a test that took a new process for the ended one would fail by chance.
_ENDED: list[subprocess.Popen[bytes]] = []


def ended_pid() -> int:
    """The number of a process that ran and ended."""
    done = subprocess.Popen([sys.executable, "-c", "pass"])
    done.wait()
    _ENDED.append(done)
    return done.pid


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


def test_a_takeover_another_run_is_making_is_not_made_twice(tmp_path) -> None:
    """Found by review: two runs that found the same stale lock could each remove it and both hold the lock."""
    ws = Workspace.init(tmp_path)
    (ws.home / LOCK).write_text(f"{ended_pid()} {platform.node()}", encoding="ascii")
    (ws.home / ".lock.taking").write_text("another run", encoding="ascii")  # a takeover under way
    with pytest.raises(WorkspaceError, match="held by another adk-spec run"), held(ws):
        pass
    assert (ws.home / ".lock.taking").read_text(encoding="ascii") == "another run"


def test_a_lock_an_older_adk_spec_wrote_is_left_alone(tmp_path) -> None:
    """Found by review: such a lock names no machine, and on a shared drive its run may be on another one."""
    ws = Workspace.init(tmp_path)
    (ws.home / LOCK).write_text(str(ended_pid()), encoding="ascii")
    with pytest.raises(WorkspaceError, match="held by another adk-spec run"), held(ws):
        pass


def test_a_run_leaves_the_lock_another_run_now_holds(tmp_path) -> None:
    """Found by an outside audit: where a person removed a running run's lock and another run took it, the first run
    removed the second's lock as it ended."""
    ws = Workspace.init(tmp_path)
    with held(ws):
        (ws.home / LOCK).write_text(f"1 {platform.node()}-another", encoding="ascii")
    assert (ws.home / LOCK).read_text(encoding="ascii") == f"1 {platform.node()}-another"


def test_a_takeover_marker_is_ignored_by_git_and_named_where_it_blocks(tmp_path) -> None:
    """Found by an outside audit: a run stopped in a takeover left its marker, which git listed as new work and the
    refusal never named."""
    ws = Workspace.init(tmp_path)
    assert TAKING in (ws.home / ".gitignore").read_text(encoding="utf-8").split()
    (ws.home / LOCK).write_text(f"{ended_pid()} {platform.node()}", encoding="ascii")
    (ws.home / TAKING).write_text("1 elsewhere", encoding="ascii")
    with pytest.raises(WorkspaceError, match=r"\.lock\.taking"), held(ws):
        pass


def test_a_run_removes_its_lock_though_the_machines_name_changed_meanwhile(tmp_path, monkeypatch) -> None:
    """Found by review: a laptop's name follows its network, and a run that read it again as it ended took its own lock
    for another's and left it, refusing every command after."""
    ws = Workspace.init(tmp_path)
    with held(ws):
        monkeypatch.setattr(platform, "node", lambda: "renamed-on-another-network")
    assert not (ws.home / LOCK).exists()
