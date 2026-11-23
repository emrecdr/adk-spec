"""The one way adk-spec finds and starts a program: git, and the test command a person wrote.

A program is found on PATH's absolute entries only, never in the current folder, which a repository's own files
could fill. A run is bounded in time, and past it, or on an interrupt, the whole tree of processes it started is
stopped: on Windows by `taskkill`, elsewhere by ending the session it was started in. A project's tests are run so
that what they leave running is stopped too, and so that only the end of their output is ever held. On Windows, what
an adk-spec process starts is also tied to it by a job object, `tie_children`: it ends when the process ends, killed
or not, as a session's would end elsewhere.
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


#: The job this process and all it starts run in, on Windows: held open for the process's life, and closed by the
#: system as it ends, however it ends.
_TIED: list[int] = []


def tie_children() -> bool:
    """On Windows, every program this process starts, and every one those start, ends when this process ends, killed
    or not: the process is put into a job object that kills what it holds once its last handle closes, which happens
    as the process ends, and what it starts after joins it by itself, with no moment between start and joining. The
    roadmap's Windows job object: a server an editor killed left its command running, spending and holding the lock,
    and a test run left behind what it started. Elsewhere a run is started in a session of its own and stopped whole,
    and this does nothing. Whether the tie is made: where the system refuses it, things go on as before."""
    if not WINDOWS:
        return False
    if not _TIED:
        try:
            _TIED.append(_killed_on_close())
        except OSError:
            return False
    return True


def _killed_on_close() -> int:
    """A job object that kills every process in it once its last handle closes, with this process in it: its
    handle, or `OSError` where the system refuses either step."""
    import ctypes
    from ctypes import wintypes

    class _Limits(ctypes.Structure):
        _fields_ = (
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        )

    class _ExtendedLimits(ctypes.Structure):
        _fields_ = (
            ("BasicLimitInformation", _Limits),
            ("IoInfo", ctypes.c_uint64 * 6),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        )

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)  # pyrefly: ignore[missing-attribute]
    kernel.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
    kernel.SetInformationJobObject.restype = wintypes.BOOL
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL
    job = kernel.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())  # pyrefly: ignore[missing-attribute]
    limits = _ExtendedLimits()
    limits.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    extended = 9  # JobObjectExtendedLimitInformation
    set_up = kernel.SetInformationJobObject(job, extended, ctypes.byref(limits), ctypes.sizeof(limits))
    if not set_up or not kernel.AssignProcessToJobObject(job, kernel.GetCurrentProcess()):
        refused = ctypes.WinError(ctypes.get_last_error())  # pyrefly: ignore[missing-attribute]
        kernel.CloseHandle(job)  # a job this process is not in kills nothing as it closes
        raise refused
    return job


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
