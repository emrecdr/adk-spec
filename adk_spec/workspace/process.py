"""The one way adk-spec finds and starts a program: git, and the test command a person wrote.

A program is found on PATH's absolute entries only, never in the current folder, which a repository's own files
could fill. A run is bounded in time, and past it, or on an interrupt, the whole tree of processes it started is
stopped: on Windows by `taskkill`, elsewhere by ending the session it was started in. A project's tests are run so
that what they leave running is stopped too, and so that only the end of their output is ever held.
"""

from __future__ import annotations

import contextlib
import functools
import os
import shutil
import signal
import subprocess
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import IO

#: How long a stopped run's last output is waited for. A process it started in a session of its own, a server a
#: test left running, can hold the output open as long as it lives.
DRAIN_S = 5.0
#: What a run that ended gives back, and what is raised for one past its time: named here for the modules that call
#: `run`, so that none of them imports `subprocess`.
Completed = subprocess.CompletedProcess
TimedOut = subprocess.TimeoutExpired


#: Whether this is Windows, where a process tree is stopped by its root with taskkill.
WINDOWS = os.name == "nt"


def on_path(name: str, path: str | None = None) -> str | None:
    """`name` by its full path, as the absolute entries of `path`, PATH where none is given, find it, or nothing:
    never from the current folder."""
    return _found(name, os.environ.get("PATH", "") if path is None else path)


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
    with started(argv, env=env, cwd=cwd, merged=merged) as process:
        return waited(process, timeout)


#: A program `started` returns, as one outside this module names it.
type Started = subprocess.Popen[bytes]


def started(argv: list[str], *, env: Mapping[str, str], cwd: Path | None = None, merged: bool = False) -> Started:
    """One program started, in a session of its own so that its whole tree can be stopped, for a caller that waits on
    it with `waited`, and may `stop` it first: a call an assistant cancelled, say."""
    return subprocess.Popen(
        argv,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT if merged else subprocess.PIPE,
        env=dict(env),
        start_new_session=not WINDOWS,  # its own session: stopped whole, with what it started
    )


def waited(process: subprocess.Popen[bytes], timeout: float) -> subprocess.CompletedProcess[bytes]:
    """A started program's output once it ends. Past `timeout` its whole tree is stopped and
    `subprocess.TimeoutExpired` raised, holding what it had written by then."""
    argv = process.args if isinstance(process.args, list) else [str(process.args)]
    try:
        out, err = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _stopped(process, WINDOWS)
        try:  # the output to its end, which Windows reads on threads, for as long as a stopped tree takes
            out, err = process.communicate(timeout=DRAIN_S)
        except subprocess.TimeoutExpired as late:  # a process that left the session holds it: what came is kept
            out, err = late.output or b"", late.stderr or b""
        raise subprocess.TimeoutExpired(argv, timeout, output=out, stderr=err) from None
    except BaseException:  # an interrupt: a session of its own hears none, so it is stopped here
        _stopped(process, WINDOWS)
        raise
    return subprocess.CompletedProcess(argv, process.returncode, out, err)


def stop(process: subprocess.Popen[bytes]) -> None:
    """A started program and every process it started, stopped. One that ended and was waited for is not: its number
    may already be another process's."""
    if process.poll() is None:
        _stopped(process, WINDOWS)


@dataclass(frozen=True)
class Kept:
    """What a run kept of itself: its exit code, nothing where it was stopped; the end of its output; whether that
    end is cut from a longer one."""

    code: int | None
    output: bytes
    cut: bool


def run_kept(argv: list[str], *, env: Mapping[str, str], timeout: float, keep: int, cwd: Path | None = None) -> Kept:
    """One program, judged by its own exit, its standard error with its standard out, of which only the last `keep`
    bytes are ever held. Past `timeout`, or on an interrupt, every process it started is stopped; once it ends, what it
    left running, a server say, is stopped too, outside Windows, where a tree is found by its root alone."""
    process = subprocess.Popen(
        argv,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=dict(env),
        start_new_session=not WINDOWS,
    )
    tail = _Tail(keep)
    reader = threading.Thread(target=tail.read, args=(process.stdout,), daemon=True)
    reader.start()
    try:
        code: int | None = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        code = None
    except BaseException:
        _stopped(process, WINDOWS)
        raise
    # What it left running, also where it passed: its session outlives it while something in it runs. Not on Windows,
    # where taskkill finds a tree by its root, which has ended: what it left there runs on, until a job object holds
    # the tree, which waits for a Windows machine to test it on.
    if code is None or not WINDOWS:
        _stopped(process, WINDOWS)
    with contextlib.suppress(subprocess.TimeoutExpired):
        process.wait(timeout=DRAIN_S)
    reader.join(DRAIN_S)  # a process that left the session may hold the output: it is waited for no longer
    if not reader.is_alive() and process.stdout:
        process.stdout.close()
    return Kept(code, *tail.held())


class _Tail:
    """The last bytes of a stream, as it is read: never more than twice `keep` held."""

    def __init__(self, keep: int) -> None:
        self.keep = keep
        self._buffer = bytearray()
        self._cut = False
        self._lock = threading.Lock()

    def read(self, stream: IO[bytes] | None) -> None:
        if stream is None:
            return
        with contextlib.suppress(OSError, ValueError):
            while chunk := stream.read1(65_536):  # pyrefly: ignore[missing-attribute]
                with self._lock:
                    self._buffer += chunk
                    if len(self._buffer) > 2 * self.keep:
                        del self._buffer[: -self.keep]
                        self._cut = True

    def held(self) -> tuple[bytes, bool]:
        with self._lock:
            return bytes(self._buffer[-self.keep :]), self._cut or len(self._buffer) > self.keep


def _stopped(process: subprocess.Popen[bytes], windows: bool) -> None:
    """A process and every process it started, stopped: where it ended already, what it left in its session."""
    if windows:
        taskkill = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "taskkill.exe")
        subprocess.run([taskkill, "/F", "/T", "/PID", str(process.pid)], capture_output=True, check=False)
    else:
        with contextlib.suppress(ProcessLookupError):  # it ended on its own meanwhile
            os.killpg(process.pid, signal.SIGKILL)  # pyrefly: ignore[missing-attribute] - not on Windows, nor run there
    process.kill()
