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
from pathlib import Path

from ..domain.model import PASSED
from ..domain.secrets import scrub
from ..domain.text import normalise
from ..domain.verify import TestRun
from .process import TimedOut, on_path, run

#: How much of a run's output, its end, a model and the report are shown.
TAIL_MAX_CHARS = 6_000
#: How much of a run's output, its last bytes, is scrubbed to find that end: some forty times what is shown, and far
#: wider than any secret shape, the longest of which, a private key, is some three thousand characters.
WINDOW_BYTES = 256_000


def run_tests(root: Path, argv: Sequence[str], *, timeout: int, name: str = "") -> TestRun:
    """The tests run in `root` by `argv`, stopped past `timeout` seconds. Never an error: a program that cannot be
    found or started is a run that did not pass, and says why."""
    words = tuple(argv)
    if (program := _program(words[0])) is None:
        why = "a program is named by its name on PATH or by its absolute path, and this one is neither found"
        return TestRun(name, words, f"not run: {words[0]}: {why}", "", None)
    began = time.monotonic()
    try:
        done = run([program, *words[1:]], env=os.environ, timeout=timeout, cwd=root, merged=True)
    except TimedOut as exc:
        output, outcome = exc.output or b"", f"timed out after {timeout} s"
    except OSError as exc:
        return TestRun(name, words, f"not run: {words[0]} could not start: {exc.strerror or exc}", "", None)
    else:
        output = done.stdout or b""
        outcome = PASSED if done.returncode == 0 else f"failed (exit {done.returncode})"
    return TestRun(name, words, outcome, _tail(output), time.monotonic() - began)


def _program(word: str) -> str | None:
    """A program by its absolute path, or found on PATH: a relative path names nothing."""
    if os.path.isabs(word):
        return word if Path(word).is_file() else None
    if "/" in word or "\\" in word:
        return None
    return on_path(word)


def _tail(output: bytes) -> str:
    """The end of a run's output, scrubbed. Its last bytes are cut first, at a line, far wider than any secret
    shape, then scrubbed, then cut to what is shown: no quote is ever looked for in it, so no line need keep its
    number, and a test runner that writes megabytes is never scrubbed whole."""
    text = normalise(_end(output[-WINDOW_BYTES:].decode("utf-8", "replace"), WINDOW_BYTES))
    return _end(scrub(text)[0], TAIL_MAX_CHARS)


def _end(text: str, most: int) -> str:
    """The end of `text`, at most `most` characters, cut at a line where it can be."""
    if len(text) <= most:
        return text
    cut = text[-most:]
    return cut.partition("\n")[2] or cut
