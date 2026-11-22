"""The one way adk-spec finds and starts a program: git, and the test command a person wrote.

A program is found on PATH's absolute entries only, never in the current folder, which a repository's own files
could fill. A run is bounded in time, and past it the whole tree of processes it started is stopped: on Windows by
`taskkill`, elsewhere by ending the session it was started in.
"""

from __future__ import annotations

import contextlib
import functools
import os
import shutil
import signal
import subprocess
from collections.abc import Mapping
from pathlib import Path

#: What a run that ended gives back, and what is raised for one past its time: named here for the modules that call
#: `run`, so that none of them imports `subprocess`.
Completed = subprocess.CompletedProcess
TimedOut = subprocess.TimeoutExpired


def on_path(name: str) -> str | None:
    """`name` by its full path, as PATH's absolute entries find it, or nothing: never from the current folder."""
    return _found(name, os.environ.get("PATH", ""))


@functools.cache
def _found(name: str, path: str) -> str | None:
    """Once per PATH: on Windows each lookup tries every PATHEXT. An empty entry or a relative one names the
    current folder, and is left out."""
    os.environ["NoDefaultCurrentDirectoryInExePath"] = "1"  # read by `shutil.which` on Windows, ignored elsewhere
    absolute = os.pathsep.join(entry for entry in path.split(os.pathsep) if os.path.isabs(entry))
    return shutil.which(name, path=absolute)


def run(
    argv: list[str], *, env: Mapping[str, str], timeout: float, cwd: Path | None = None, merged: bool = False
) -> subprocess.CompletedProcess[bytes]:
    """One program, bytes out: standard error apart, or `merged` into standard out. Past `timeout` its whole tree
    is stopped and `subprocess.TimeoutExpired` raised, holding what it had written by then."""
    stderr = subprocess.STDOUT if merged else subprocess.PIPE
    windows = os.name == "nt"
    with subprocess.Popen(
        argv,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=stderr,
        env=dict(env),
        start_new_session=not windows,  # its own session: stopped whole, with what it started
    ) as process:
        try:
            out, err = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            _stopped(process, windows)
            out, err = process.communicate()  # the output to its end, which Windows reads on threads
            raise subprocess.TimeoutExpired(argv, timeout, output=out, stderr=err) from None
    return subprocess.CompletedProcess(argv, process.returncode, out, err)


def _stopped(process: subprocess.Popen[bytes], windows: bool) -> None:
    """A process and every process it started, stopped."""
    if windows:
        taskkill = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "taskkill.exe")
        subprocess.run([taskkill, "/F", "/T", "/PID", str(process.pid)], capture_output=True, check=False)
    else:
        with contextlib.suppress(ProcessLookupError):  # it ended on its own meanwhile
            os.killpg(process.pid, signal.SIGKILL)
    process.kill()
