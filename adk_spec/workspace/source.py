"""A repository's source, read for a stage that asked for it: through git's own list of files, and within caps.

A model names what it wants to see: files, folders, words to search for. Nothing it names is trusted. A path is
used only where it is, to the letter, one of the paths git lists for the repository, which holds nothing git
ignores, nothing of `.spec/`, and nothing a person excluded. A path is never built from a model's text and then
looked for: it is looked up, and only a path that was found is joined to the root. So no text a file holds, and no
text of a request, can steer a reading to another file.

A file is scrubbed of known secret shapes whole, once, before anything is cut out of it: a range of lines, a line a
search found and a file cut at a cap are all taken from the scrubbed text. A private key's block is known by its
first and last line together, so a piece cut out first would show its middle. Each line keeps its own number, so
that a quote found in the text is found at the line the file has it.

A file that holds a private key is shown in no piece at all, here or in a diff: a key with no last line is hidden by
no scrub, and a diff shows a file in pieces that hold neither line.

What cannot be given is left out and named, and is never an error: a reading goes on without it.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from itertools import zip_longest
from pathlib import Path

from ..domain.secrets import holds_a_key, scrub_lines
from ..domain.text import lines_of, normalise, plain
from ..domain.verify import parts_of_diff
from .files import NotTextError, read_text
from .git import GitError, grep
from .git import files as listed_by_git

#: What one round of reading holds at most. Provisional, as the context limits are, until a live run measures them.
FILES_A_ROUND = 12
FOLDERS_A_ROUND = 4
FOLDER_MAX_PATHS = 200
SEARCHES_A_ROUND = 6
SEARCH_MAX_LINES = 20
LINE_MAX_CHARS = 200
FILE_MAX_CHARS = 12_000
ROUND_MAX_CHARS = 40_000
#: A file past this many bytes is not opened at all, and a word to search for past this many characters is none.
FILE_MAX_BYTES = 2_000_000
TERM_MAX_CHARS = 100
#: Why a file that holds a private key is left out, of a reading and of a diff alike.
HOLDS_A_KEY = "holds a private key, which is never shown"
#: A file asked for with a range of lines: `src/app.py:120-260`.
_RANGE = re.compile(r"(?P<path>.+):(?P<first>[0-9]{1,9})-(?P<last>[0-9]{1,9})")


@dataclass(frozen=True)
class Gathered:
    """What one round of reading found."""

    #: Each file's text as it was shown, by its path: every line at its own number, a line not shown left empty.
    texts: dict[str, str]
    #: What a stage reads: each file, listing and search under a line that names it.
    shown: str
    #: Each file read, with how much of it: `src/app.py (whole)`, `src/app.py (lines 1 to 240 of 612)`.
    read: tuple[str, ...]
    #: What was asked for and not given, each with why.
    left_out: tuple[str, ...]
    #: For each file read, the first and the last line shown and how many lines it has.
    reached: dict[str, tuple[int, int, int]]
    #: What was asked for and left out for room alone, each as it was asked: it may be asked for again.
    deferred: tuple[str, ...] = ()


def merged(one: str, other: str) -> str:
    """Two readings of one file as one text, each line at its own number: a line either of them holds is kept, and
    the longer of the two where both hold it. A search holds the first characters of a long line, and a reading of
    the file the whole of it: both are of one scrubbed text, so the shorter is the start of the longer."""
    return "\n".join(max(a, b, key=len) for a, b in zip_longest(one.split("\n"), other.split("\n"), fillvalue=""))


@dataclass
class _Round:
    room: int
    texts: dict[str, str] = field(default_factory=dict)
    parts: list[str] = field(default_factory=list)
    read: list[str] = field(default_factory=list)
    left_out: list[str] = field(default_factory=list)
    reached: dict[str, tuple[int, int, int]] = field(default_factory=dict)
    deferred: list[str] = field(default_factory=list)

    def shows(self, block: str) -> bool:
        """Whether `block` still fits the round, in which case it is taken."""
        if len(block) > self.room:
            return False
        self.room -= len(block)
        self.parts.append(block)
        return True

    def holds(self, path: str, line: int, text: str) -> None:
        """`text` kept as what `path` holds from `line` on."""
        self.texts[path] = merged(self.texts.get(path, ""), "\n" * (line - 1) + text)


def _named(asked: str, missing: str) -> str:
    """A model's own word for what it asked, as it may be printed."""
    return plain(asked)[:LINE_MAX_CHARS] or missing


def _counted(count: int, one: str, many: str) -> str:
    return f"{count:,} {one if count == 1 else many}"


class Source:
    """The files of one repository that a stage may be shown."""

    def __init__(self, root: Path, paths: Sequence[str], *, exclude: Sequence[str]) -> None:
        self.root = root
        #: Every path git lists, in order, from `root`, with forward slashes.
        self.paths = sorted(paths)
        self._listed = frozenset(paths)
        self._exclude = tuple(exclude)
        #: Each file opened so far: its lines as they may be shown, or why it is not read.
        self._opened: dict[str, list[str] | str] = {}

    @classmethod
    def of(cls, root: Path, *, exclude: Sequence[str]) -> Source:
        """The source of the repository at `root`, as git lists it now, less what a person excluded."""
        return cls(root, listed_by_git(root, exclude=exclude), exclude=exclude)

    def gathered(self, files: Sequence[str], folders: Sequence[str], searches: Sequence[str]) -> Gathered:
        """One round: each file read, each folder listed and each search made, within the caps. What is past a cap
        or cannot be given is named among what was left out, and is no error."""
        got = _Round(ROUND_MAX_CHARS)
        asked = (
            (files, FILES_A_ROUND, self._file, ("file", "files"), "reads"),
            (folders, FOLDERS_A_ROUND, self._folder, ("folder", "folders"), "lists"),
            (searches, SEARCHES_A_ROUND, self._search, ("search", "searches"), "makes"),
        )
        for wanted, cap, give, (one, many), does in asked:
            for item in wanted[:cap]:
                give(item, got)
            if (over := len(wanted) - cap) > 0:
                got.left_out.append(f"{over:,} more {one if over == 1 else many} asked for than a round {does}")
                got.deferred += wanted[cap:]
        if got.parts and got.deferred:  # said where the stage reads: nothing else tells it that asking again helps
            named = ", ".join(_named(item, "(nothing)") for item in got.deferred)
            got.parts.append(f"=== not shown, for room. Ask again for what is still needed: {named}")
        shown = "\n".join(got.parts)
        return Gathered(got.texts, shown, tuple(got.read), tuple(got.left_out), got.reached, tuple(got.deferred))

    def _asked(self, asked: str) -> tuple[str, int | None, int | None]:
        """The path a model asked for, and the lines of it where it named a range. A path git lists is taken as it
        is, a colon in its name too."""
        asked = asked.strip()
        if asked not in self._listed and (ranged := _RANGE.fullmatch(asked)) and ranged["path"] in self._listed:
            return ranged["path"], int(ranged["first"]), int(ranged["last"])
        return asked, None, None

    def _lines(self, path: str) -> list[str] | str:
        """Every line of a file git lists, as it may be shown: scrubbed whole, each line at its own number. Or why
        the file is not read. A file is opened and scrubbed once, however often it is asked for."""
        if path not in self._opened:
            self._opened[path] = self._read(path)
        return self._opened[path]

    def _read(self, path: str) -> list[str] | str:
        target = self.root / path  # joined only here, and only for a path that was found in git's list
        try:
            if self._linked(path):
                return "a symbolic link is not read"
            if not target.is_file():
                return "git lists it, and no file is there"
            if not target.resolve().is_relative_to(self.root.resolve()):
                return "it stands outside the repository"
            if (size := target.stat().st_size) > FILE_MAX_BYTES:
                return f"{size:,} bytes, too large to read"
            text = normalise(read_text(target))
            return HOLDS_A_KEY if holds_a_key(text) else lines_of(scrub_lines(text)[0])
        except NotTextError:
            return "is not text adk-spec reads, which is UTF-8"
        except OSError as exc:
            return f"could not be read: {exc.strerror or exc}"

    def _linked(self, path: str) -> bool:
        """Whether the file at `path`, or a folder on the way to it from the root, is a symbolic link or a
        junction. git lists a tracked file still after its folder was replaced by a link, and read through the
        link the file is another folder's: one git ignores, or one a person excluded."""
        at = self.root
        for part in path.split("/"):
            at = at / part
            if at.is_symlink() or at.is_junction():
                return True
        return False

    def without_keys(self, diff: str) -> tuple[str, tuple[str, ...]]:
        """A unified diff less the part of each file that holds a private key, and those files' names. A file is
        known for one by how it stands in the repository, or by a key's first line among the lines the diff shows
        of it: the first covers a change in a key's middle, the second a key that was deleted or lost its first
        line. What is left is the diff a stage may be shown, and is still scrubbed as every text is."""
        kept: list[str] = []
        held: list[str] = []
        for path, part in parts_of_diff(diff):
            if holds_a_key(part) or (path is not None and self._lines(path) == HOLDS_A_KEY):
                held.append(path or "(a file with no name)")
            else:
                kept.append(part)
        return "".join(kept), tuple(held)

    def _file(self, asked: str, got: _Round) -> None:
        path, first, last = self._asked(asked)
        if path not in self._listed:
            got.left_out.append(f"{_named(asked, '(no path)')}: git lists no such file")
            return
        lines = self._lines(path)
        if isinstance(lines, str):
            got.left_out.append(f"{path}: {lines}")
            return
        total = len(lines)
        first = min(max(first or 1, 1), max(total, 1))
        kept: list[str] = []
        size = 0
        for line in lines[first - 1 : min(last or total, total)]:
            if kept and size + len(line) + 1 > FILE_MAX_CHARS:
                break
            kept.append(line)
            size += len(line) + 1
        upto = first + len(kept) - 1
        said = "whole" if first == 1 and upto >= total else f"lines {first} to {upto} of {total}"
        text = "\n".join(kept)
        if not got.shows(f"=== {path} ({said})\n{text}"):
            got.left_out.append(f"{path}: past what a round reads")
            got.deferred.append(asked)
            return
        got.read.append(f"{path} ({said})")
        got.reached[path] = (first, upto, total)
        got.holds(path, first, text)

    def _folder(self, asked: str, got: _Round) -> None:
        folder = asked.strip().strip("/")
        whole = folder in ("", ".")
        under = self.paths if whole else [path for path in self.paths if path.startswith(f"{folder}/")]
        if not under:
            got.left_out.append(f"{_named(asked, '(no folder)')}/: git lists nothing under it")
            return
        listed = under[:FOLDER_MAX_PATHS]
        note = _counted(len(under), "file", "files")
        note += f", the first {len(listed)} listed" if len(listed) < len(under) else ""
        if not got.shows("\n".join([f"=== {'.' if whole else folder}/ ({note})", *listed])):
            got.left_out.append(f"{folder or '.'}/: past what a round reads")
            got.deferred.append(asked)

    def _search(self, asked: str, got: _Round) -> None:
        term = asked.strip()
        if not term or not term.isprintable() or len(term) > TERM_MAX_CHARS:
            got.left_out.append(f"{_named(asked, '(no word)')}: no search adk-spec makes")
            return
        try:
            found = grep(self.root, term, exclude=self._exclude)
        except GitError as exc:
            got.left_out.append(f"search for {term}: {exc}")
            return
        # git read each file as it stands, and a stage is shown it scrubbed. A hit counts only where the line a
        # stage is shown still holds the word: one on a hidden value, counted or numbered, would say that the value
        # holds the word, and asked often enough, the value. A line is opened only until enough are shown.
        wanted = term.casefold()
        rows: list[tuple[str, int, str]] = []
        more = False
        for line in found:
            path, _, rest = line.partition(":")
            number = rest.partition(":")[0]
            lines = self._lines(path) if path in self._listed and number.isascii() and number.isdecimal() else ""
            at = int(number) if isinstance(lines, list) else 0
            if not 1 <= at <= len(lines) or wanted not in lines[at - 1].casefold():
                continue
            if len(rows) == SEARCH_MAX_LINES:
                more = True
                break
            rows.append((path, at, lines[at - 1][:LINE_MAX_CHARS].rstrip()))
        note = _counted(len(rows), "line", "lines")
        note = f"more than {SEARCH_MAX_LINES} lines, the first {SEARCH_MAX_LINES} shown" if more else note
        shown = [f"{path}:{number}:{text}" for path, number, text in rows]
        if not got.shows("\n".join([f"=== search: {term} ({note})", *shown])):
            got.left_out.append(f"search for {term}: past what a round reads")
            got.deferred.append(asked)
            return
        for path, number, text in rows:
            got.holds(path, number, text)
