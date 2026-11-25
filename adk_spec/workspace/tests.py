"""A project's own tests, run by the command a person wrote in `.spec/config.toml`: the strongest evidence `verify`
has that the work does what it says.

Only a command a person wrote is run, as the list of words they wrote, with no shell to read it. Its program is
found on PATH's absolute entries, or named by its absolute path: never in a folder relative to where it runs, which
a repository's own files could fill. The end of its output is kept, scrubbed of secret shapes before anything
shows it.
"""

from __future__ import annotations

import os
import sys
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


def run_tests(
    root: Path, argv: Sequence[str], *, timeout: int, name: str = "", without: frozenset[str] = frozenset()
) -> TestRun:
    """The tests run in `root` by `argv`, judged by their own exit and stopped past `timeout` seconds, given the
    person's environment less the names in `without`: what adk-spec's own `.env` added, a provider's key among them,
    is adk-spec's, not the project's. Found by the third audit: the tests, code an agent may just have written, were
    handed the key. Never an error: a program that cannot be found or started is a run that did not pass, and says
    why."""
    words = tuple(argv)
    env = {key: value for key, value in _environment(root).items() if key not in without}
    program, why = _program(words[0], env.get("PATH", ""))
    if program is None:
        return TestRun(name, words, f"not run: {words[0]}: {why}", "", None)
    began = time.monotonic()
    try:
        kept = run_kept([program, *words[1:]], env=env, timeout=timeout, keep=WINDOW_BYTES, cwd=root)
    except OSError as exc:
        return TestRun(name, words, f"not run: {words[0]} could not start: {exc.strerror or exc}", "", None)
    if kept.code is None:
        outcome = f"timed out after {timeout} s"
    else:
        outcome = PASSED if kept.code == 0 else f"failed (exit {kept.code})"
    return TestRun(name, words, outcome, _tail(kept.output, cut=kept.cut), time.monotonic() - began)


def _environment(root: Path) -> dict[str, str]:
    """The person's environment, less adk-spec's own virtual environment. Run from its checkout by `uv run`, or as an
    installed tool, adk-spec's interpreter stands first on PATH and in VIRTUAL_ENV, and a plain `pytest` in a test
    command would be adk-spec's own, not the project's. A virtual environment whose folder holds the project, its
    own `.venv` or one at the top of a monorepo, is the project's, adk-spec installed in it, and stays."""
    env = dict(os.environ)
    own = Path(sys.prefix).resolve()
    if sys.prefix == sys.base_prefix or root.resolve().is_relative_to(own.parent):
        return env
    if env.get("VIRTUAL_ENV") and Path(env["VIRTUAL_ENV"]).resolve() == own:
        del env["VIRTUAL_ENV"]
    entries = env.get("PATH", "").split(os.pathsep)
    env["PATH"] = os.pathsep.join(entry for entry in entries if _not_own(entry, own))
    return env


def _not_own(entry: str, own: Path) -> bool:
    """Whether a PATH entry is not in adk-spec's own virtual environment. One that cannot be resolved, as an
    unmounted drive on Windows, is kept as it was given: it is no folder of adk-spec's."""
    try:
        return Path(entry).resolve().parent != own
    except OSError, ValueError:
        return True


def _program(word: str, path: str) -> tuple[str | None, str]:
    """A program by its absolute path, or found on PATH, and why where it is none: a relative path names nothing,
    and a batch file is read again by cmd.exe."""
    if os.path.isabs(word):
        found = word if Path(word).is_file() else None
    elif "/" in word or "\\" in word:
        found = None
    else:
        found = on_path(word, path)
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
    return _end(scrub(text, cut=True)[0], TAIL_MAX_CHARS, cut=cut)


def _from_a_line(text: str, *, cut: bool) -> str:
    """`text` from its first whole line where it was cut from a longer one: the piece before is half of something."""
    return (text.partition("\n")[2] or text) if cut else text


#: The line before an output whose start is not shown: phase 18, `verify` was given the end with no mark of the cut.
CUT_MARK = "(the start of the output is not shown: only its end fits)"


def _end(text: str, most: int, *, cut: bool = False) -> str:
    """The end of `text`, at most `most` characters, cut at a line where it can be, and opening on `CUT_MARK` where
    its start is not shown: cut here, or already, `cut`, by the window a run's output is held in."""
    if len(text) <= most and not cut:
        return text
    room = most - len(CUT_MARK) - 1
    end = text[-room:]
    end = (end.partition("\n")[2] or end) if len(text) > room else end
    return f"{CUT_MARK}\n{end}"
