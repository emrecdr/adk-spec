"""A project's own tests, run by the command a person wrote in `.spec/config.toml`: the strongest evidence `verify`
has that the work does what it says.

Only a command a person wrote is run, as the list of words they wrote, with no shell to read it. Its program is
found on PATH's absolute entries, or named by its absolute path: never in a folder relative to where it runs, which
a repository's own files could fill. The end of its output is kept, scrubbed of secret shapes before anything
shows it.
"""

from __future__ import annotations

import os
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from ..domain.secrets import scrub, scrub_lines
from .process import TimedOut, on_path, run

#: How much of a run's output, its end, a model and the report are shown.
TAIL_MAX_CHARS = 6_000
#: How much of a run's output is scrubbed to find that end: a run that writes more is cut first, at a line.
OUTPUT_MAX_CHARS = 1_000_000


@dataclass(frozen=True)
class TestRun:
    """What one run of a project's tests came to."""

    #: The repository it ran in: empty for the workspace's own.
    name: str
    argv: tuple[str, ...]
    #: `passed`, `failed (exit N)`, `timed out after N s`, or `not run: <why>`.
    outcome: str
    #: The end of its output, scrubbed.
    tail: str
    seconds: float

    @property
    def passed(self) -> bool:
        return self.outcome == "passed"

    @property
    def command(self) -> str:
        """The command as it is shown, scrubbed: a test command may carry a token of its own."""
        return scrub(" ".join(self.argv))[0]


def run_tests(root: Path, argv: Sequence[str], *, timeout: int, name: str = "") -> TestRun:
    """The tests run in `root` by `argv`, stopped past `timeout` seconds. Never an error: a program that cannot be
    found or started is a run that did not pass, and says why."""
    words = tuple(argv)
    program = _program(words[0]) if words else None
    if program is None:
        why = "a program is named by its name on PATH or by its absolute path, and this one is neither found"
        return TestRun(name, words, f"not run: {words[0] if words else '(nothing)'}: {why}", "", 0.0)
    began = time.monotonic()
    try:
        done = run([program, *words[1:]], env=os.environ, timeout=timeout, cwd=root, merged=True)
    except TimedOut as exc:
        output, outcome = exc.output or b"", f"timed out after {timeout} s"
    except OSError as exc:
        return TestRun(name, words, f"not run: {words[0]} could not start: {exc.strerror or exc}", "", 0.0)
    else:
        output = done.stdout or b""
        outcome = "passed" if done.returncode == 0 else f"failed (exit {done.returncode})"
    return TestRun(name, words, outcome, _tail(output), time.monotonic() - began)


def _program(word: str) -> str | None:
    """A program by its absolute path, or found on PATH: a relative path names nothing."""
    if os.path.isabs(word):
        return word if Path(word).is_file() else None
    if "/" in word or "\\" in word:
        return None
    return on_path(word)


def _tail(output: bytes) -> str:
    """The end of a run's output, scrubbed whole before it is cut, at a line where it can be."""
    text = output.decode("utf-8", "replace").replace("\r\n", "\n")
    if len(text) > OUTPUT_MAX_CHARS:
        text = text[-OUTPUT_MAX_CHARS:].partition("\n")[2]
    text = scrub_lines(text)[0]
    if len(text) <= TAIL_MAX_CHARS:
        return text
    cut = text[-TAIL_MAX_CHARS:]
    return cut.partition("\n")[2] or cut
