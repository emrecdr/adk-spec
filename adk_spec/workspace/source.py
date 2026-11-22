"""A repository's source, read for a stage that asked for it: through git's own list of files, and within caps.

A model names what it wants to see: files, folders, words to search for. Nothing it names is trusted. A path is
used only where it is, to the letter, one of the paths git lists for the repository, which holds nothing git
ignores, nothing of `.spec/`, and nothing a person excluded. A path is never built from a model's text and then
looked for: it is looked up, and only a path that was found is joined to the root. So no text a file holds, and no
text of a request, can steer a reading to another file.

A file's text is kept as it was shown, each line at its own number, so that a quote found in it is found at the
line it has in the file.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from itertools import zip_longest
from pathlib import Path

from ..domain.text import lines_of, normalise, plain
from .files import NotTextError, read_text
from .git import files as listed_by_git
from .git import grep

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
#: A file asked for with a range of lines: `src/app.py:120-260`.
_RANGE = re.compile(r"(?P<path>.+):(?P<first>\d+)-(?P<last>\d+)")


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


def merged(one: str, other: str) -> str:
    """Two readings of one file as one text, each line at its own number: a line either of them holds is kept."""
    return "\n".join(a or b for a, b in zip_longest(one.split("\n"), other.split("\n"), fillvalue=""))


@dataclass
class _Round:
    room: int
    texts: dict[str, str] = field(default_factory=dict)
    parts: list[str] = field(default_factory=list)
    read: list[str] = field(default_factory=list)
    left_out: list[str] = field(default_factory=list)

    def shows(self, block: str) -> bool:
        """Whether `block` still fits the round, in which case it is taken."""
        if len(block) > self.room:
            return False
        self.room -= len(block)
        self.parts.append(block)
        return True

    def holds(self, path: str, line: int, text: str) -> None:
        """`text` kept as what `path` holds from `line` on."""
        padded = "\n" * (line - 1) + text
        self.texts[path] = merged(self.texts[path], padded) if path in self.texts else padded


def _named(asked: str, missing: str) -> str:
    """A model's own word for what it asked, as it may be printed."""
    return plain(asked)[:LINE_MAX_CHARS] or missing


def _counted(count: int, one: str, many: str) -> str:
    return f"{count:,} {one if count == 1 else many}"


class Source:
    """The files of one repository that a stage may be shown."""

    def __init__(self, root: Path, paths: Sequence[str], *, exclude: Sequence[str] = ()) -> None:
        self.root = root
        #: Every path git lists, in order, from `root`, with forward slashes.
        self.paths = sorted(paths)
        self._listed = frozenset(paths)
        self._exclude = tuple(exclude)

    @classmethod
    def of(cls, root: Path, *, exclude: Sequence[str] = ()) -> Source:
        """The source of the repository at `root`, as git lists it now."""
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
            for item in list(wanted)[:cap]:
                give(item, got)
            if (over := len(wanted) - cap) > 0:
                got.left_out.append(f"{over:,} more {one if over == 1 else many} asked for than a round {does}")
        return Gathered(got.texts, "\n".join(got.parts), tuple(got.read), tuple(got.left_out))

    def _asked(self, asked: str) -> tuple[str, int | None, int | None]:
        """The path a model asked for, and the lines of it where it named a range. A path git lists is taken as it
        is, a colon in its name too."""
        asked = asked.strip()
        if asked not in self._listed and (ranged := _RANGE.fullmatch(asked)) and ranged["path"] in self._listed:
            return ranged["path"], int(ranged["first"]), int(ranged["last"])
        return asked, None, None

    def _unreadable(self, path: str) -> str | None:
        """Why `path` is not read, or nothing where it is."""
        if path not in self._listed:
            return "git lists no such file"
        target = self.root / path  # joined only now, and only a path that was found in the list
        if target.is_symlink():
            return "a symbolic link is not read"
        if not target.is_file():
            return "git lists it, and no file is there"
        if not target.resolve().is_relative_to(self.root.resolve()):
            return "it stands outside the repository"
        if (size := target.stat().st_size) > FILE_MAX_BYTES:
            return f"{size:,} bytes, too large to read"
        return None

    def _file(self, asked: str, got: _Round) -> None:
        path, first, last = self._asked(asked)
        if why := self._unreadable(path):
            got.left_out.append(f"{_named(asked, '(no path)')}: {why}")
            return
        try:
            lines = lines_of(normalise(read_text(self.root / path)))
        except NotTextError:
            got.left_out.append(f"{path}: is not text adk-spec reads, which is UTF-8")
            return
        total = len(lines)
        first = min(max(first or 1, 1), max(total, 1))
        kept: list[str] = []
        for line in lines[first - 1 : min(last or total, total)]:
            if kept and sum(map(len, kept)) + len(kept) + len(line) > FILE_MAX_CHARS:
                break
            kept.append(line)
        upto = first + len(kept) - 1
        said = "whole" if first == 1 and upto >= total else f"lines {first} to {upto} of {total}"
        text = "\n".join(kept)
        if not got.shows(f"=== {path} ({said})\n{text}"):
            got.left_out.append(f"{path}: past what a round reads")
            return
        got.read.append(f"{path} ({said})")
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

    def _search(self, asked: str, got: _Round) -> None:
        term = asked.strip()
        if not term or not term.isprintable() or len(term) > TERM_MAX_CHARS:
            got.left_out.append(f"{_named(asked, '(no word)')}: no search adk-spec makes")
            return
        hits: list[tuple[str, int, str]] = []
        for line in grep(self.root, term, exclude=self._exclude):
            path, _, rest = line.partition(":")
            number, _, text = rest.partition(":")
            if path in self._listed and number.isdigit() and not (self.root / path).is_symlink():
                hits.append((path, int(number), text[:LINE_MAX_CHARS].rstrip()))
        shown = hits[:SEARCH_MAX_LINES]
        note = _counted(len(hits), "line", "lines")
        note += f", the first {len(shown)} shown" if len(shown) < len(hits) else ""
        rows = [f"{path}:{number}:{text}" for path, number, text in shown]
        if not got.shows("\n".join([f"=== search: {term} ({note})", *rows])):
            got.left_out.append(f"search for {term}: past what a round reads")
            return
        for path, number, text in shown:
            got.holds(path, number, text)
