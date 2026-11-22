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
from ..domain.secrets import mentions_a_key, scrub
from ..domain.text import normalise
from ..domain.verify import TestRun
from .process import on_path, run_kept

#: How much of a run's output, its end, a model and the report are shown.
TAIL_MAX_CHARS = 6_000
#: How much of a run's output, its last bytes, is scrubbed to find that end: some forty times what is shown, and far
#: wider than any secret shape, the longest of which, a private key, is some three thousand characters.
WINDOW_BYTES = 256_000


#: What is shown of a run whose output names a private key.
WITHHELD = "(the output names a private key, so none of it is shown)"
#: Programs Windows runs through cmd.exe, which reads their words again: `&`, `|` and `%VAR%` in one would act.
_BATCH = (".bat", ".cmd")


def run_tests(root: Path, argv: Sequence[str], *, timeout: int, name: str = "") -> TestRun:
    """The tests run in `root` by `argv`, judged by their own exit and stopped past `timeout` seconds. Never an
    error: a program that cannot be found or started is a run that did not pass, and says why."""
    words = tuple(argv)
    program, why = _program(words[0])
    if program is None:
        return TestRun(name, words, f"not run: {words[0]}: {why}", "", None)
    began = time.monotonic()
    try:
        kept = run_kept([program, *words[1:]], env=os.environ, timeout=timeout, keep=WINDOW_BYTES, cwd=root)
    except OSError as exc:
        return TestRun(name, words, f"not run: {words[0]} could not start: {exc.strerror or exc}", "", None)
    if kept.code is None:
        outcome = f"timed out after {timeout} s"
    else:
        outcome = PASSED if kept.code == 0 else f"failed (exit {kept.code})"
    return TestRun(name, words, outcome, _tail(kept.output, cut=kept.cut), time.monotonic() - began)


def _program(word: str) -> tuple[str | None, str]:
    """A program by its absolute path, or found on PATH, and why where it is none: a relative path names nothing,
    and a batch file is read again by cmd.exe."""
    if os.path.isabs(word):
        found = word if Path(word).is_file() else None
    elif "/" in word or "\\" in word:
        found = None
    else:
        found = on_path(word)
    if found is None:
        return None, "a program is named by its name on PATH or by its absolute path, and this one is neither found"
    if Path(found).suffix.lower() in _BATCH:
        return None, (
            f"{Path(found).name} is a batch file, which Windows runs through cmd.exe, reading its words again. "
            "Name the program it runs, such as node and the script's path"
        )
    return found, ""


def _tail(output: bytes, *, cut: bool) -> str:
    """The end of a run's output as it may be shown: from a whole line, withheld whole where it names a private key,
    scrubbed as a text cut off where it ends, a value the stop broke off included."""
    # Without the final line end the text is given, so that a value running to the stop is one that runs to its end.
    text = _from_a_line(normalise(output.decode("utf-8", "replace")), cut=cut).rstrip("\n")
    if mentions_a_key(text):
        return WITHHELD
    return _end(scrub(text, cut=True)[0], TAIL_MAX_CHARS)


def _from_a_line(text: str, *, cut: bool) -> str:
    """`text` from its first whole line where it was cut from a longer one: the piece before is half of something."""
    return (text.partition("\n")[2] or text) if cut else text


def _end(text: str, most: int) -> str:
    """The end of `text`, at most `most` characters, cut at a line where it can be."""
    if len(text) <= most:
        return text
    cut = text[-most:]
    return cut.partition("\n")[2] or cut
