"""The source a stage may be shown, read when a stage asks: through git's own list of files, and within caps.

A model names what it wants to see: files, folders, words to search for. Nothing it names is trusted. A path is
used only where it is, to the letter, one of the paths git lists for the repository, which holds nothing git
ignores, nothing of `.spec/`, and nothing a person excluded. A path is never built from a model's text and then
looked for: it is looked up, and only a path that was found is joined to the root. So no text a file holds, and no
text of a request, can steer a reading to another file.

The other repositories a change names are read by the same rules, each under its name: `api/src/routes.py` is
`src/routes.py` of the repository named `api`, looked up in the list git gives for that repository, with that
repository's own exclusions. A round's caps are shared by them all: they bound what one model call is shown.

A file is scrubbed of known secret shapes whole, once, before anything is cut out of it: a range of lines, a line a
search found and a file cut at a cap are all taken from the scrubbed text. A private key's block is known by its
first and last line together, so a piece cut out first would show its middle. Each line keeps its own number, so
that a quote found in the text is found at the line the file has it.

A file that holds a private key is shown in no piece at all, here or in a diff: a key with no last line is hidden by
no scrub, and a diff shows a file in pieces that hold neither line.

The project's installed libraries may be read too, where a reading asks for them: its Python environment and its
`node_modules`, found by `installed.py`, each under its scheme, `python:httpx/_client.py` or `node:react/index.js`. A
library's path is looked up in the list its environment's own records give, and read by the same rules. Libraries are
never searched, diffed or tested, and are no repository a change spans.

What cannot be given is left out and named, and is never an error: a reading goes on without it.
"""

from __future__ import annotations

import mmap
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from itertools import zip_longest
from pathlib import Path
from typing import NamedTuple

from ..domain.secrets import KEY_WORDS, holds_a_key, scrub_lines
from ..domain.text import lines_of, normalise, plain, sha256_of
from ..domain.verify import parts_of_diff
from .config import ConfigError, load_config
from .context import tree_text
from .files import NotTextError, read_text
from .git import GitError, diffs, grep, head, is_repository, top
from .git import files as listed_by_git
from .installed import Environment, environments
from .layout import CONFIG, ROOT_NAME

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
#: Past this a changed file that holds a key's first words is not read to tell, and its part of a diff is withheld.
KEY_SEARCH_MAX_BYTES = 64_000_000
TERM_MAX_CHARS = 100
#: Why a file that holds a private key is left out, of a reading and of a diff alike.
HOLDS_A_KEY = "holds a private key, which is never shown"
#: A file asked for with a range of lines: `src/app.py:120-260`.
_RANGE = re.compile(r"(?P<path>.+):(?P<first>[0-9]{1,9})-(?P<last>[0-9]{1,9})")
#: How much of the line that opens a statement's block is kept.
WITHIN_MAX_CHARS = 120
#: The name of another repository, which prefixes its paths: a short word.
NAME = re.compile(r"[a-z][a-z0-9-]{0,30}")
#: The most libraries the tree names in each environment: a stage is told how many more there are.
LIBRARIES_SHOWN = 120
#: Where an environment's own folder ends, in a library's path a model names through it.
_THROUGH = {"python": "site-packages/", "node": "node_modules/"}


class SourceError(Exception):
    """A repository a change names that cannot stand beside this one, for a reason the person must fix: it is this
    repository by another path, or its name is no name, or is a folder here, so that its paths would mean two files."""


class Work(NamedTuple):
    """The work since a change began: its diff as a stage is shown it, the files left out of that for holding a
    private key, and the fingerprint a verification records, which git's index does not move."""

    text: str
    held: tuple[str, ...]
    fingerprint: str


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


def _indent(line: str) -> int:
    expanded = line.expandtabs()
    return len(expanded) - len(expanded.lstrip(" "))


class _Repository:
    """One repository's files as a reading may give them: git's own list, each file opened and scrubbed once."""

    def __init__(
        self, name: str, root: Path, paths: Sequence[str], exclude: Sequence[str], *, scheme: str = ""
    ) -> None:
        #: The name its paths are shown under; the workspace's own has none, and is the one git is told to trust.
        self.name = name
        #: An installed library's environment, `python` or `node`, whose paths are shown after it and a colon.
        self.scheme = scheme
        self.trust = not name
        self.root = root
        #: Every path git lists, in order, from `root`, with forward slashes.
        self.paths = sorted(paths)
        self.listed = frozenset(paths)
        self.exclude = tuple(exclude)
        #: The command its own config runs its tests with, and for how long: none where it names none.
        self.test: tuple[str, ...] = ()
        self.test_timeout = 0
        #: Each file opened so far: its lines as they may be shown, or why it is not read.
        self._opened: dict[str, list[str] | str] = {}

    def full(self, path: str) -> str:
        """`path` as a stage is shown it: under the repository's name, where it has one, or its library's scheme."""
        if self.scheme:
            return f"{self.scheme}:{path}"
        return f"{self.name}/{path}" if self.name else path

    def lines(self, path: str) -> list[str] | str:
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

    def keyed(self, path: str) -> bool:
        """Whether a file git lists holds a private key, as `lines` would find: asked of a diff's files, which are
        not shown, so none is scrubbed for it. Scrubbed whole and thrown away, a large working tree cost a second on
        every status of a verified change."""
        opened = self._opened.get(path)
        if opened == HOLDS_A_KEY or isinstance(opened, list):  # read whole already: its answer stands
            return opened == HOLDS_A_KEY
        target = self.root / path
        try:
            if self._linked(path) or not target.is_file() or not target.resolve().is_relative_to(self.root.resolve()):
                return False
            if (size := target.stat().st_size) == 0:
                return False
            # Scanned in place for words every key's first line holds, in ASCII whatever the file's encoding: a file
            # that holds none is never read into memory. Found by the third audit: a file past the read cap, or one
            # saved as Latin-1, was taken to hold no key, and a hunk from a key's middle reached the diff.
            with target.open("rb") as handle, mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as held:
                if all(held.find(word) < 0 for word in KEY_WORDS):
                    return False
                if size > KEY_SEARCH_MAX_BYTES:  # key words in a file too large to read whole: withheld, as a key is
                    return True
                data = held[:]
        except OSError, ValueError:
            return False
        return holds_a_key(normalise(data.decode("utf-8", errors="replace")))

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

    def hits(self, term: str, room: int) -> tuple[list[tuple[str, int, str]], bool]:
        """The lines `term` is on, each by its path as a stage is shown it, its number and its scrubbed text: at
        most `room`, and whether there were more. `GitError` where git could not search.

        git reads each file as it stands, and a stage is shown it scrubbed. A hit counts only where the line a
        stage is shown still holds the word: one on a hidden value, counted or numbered, would say that the value
        holds the word, and asked often enough, the value. A line is opened only until enough are shown."""
        wanted = term.casefold()
        rows: list[tuple[str, int, str]] = []
        for line in grep(self.root, term, exclude=self.exclude, trust=self.trust):
            path, _, rest = line.partition(":")
            number = rest.partition(":")[0]
            lines = self.lines(path) if path in self.listed and number.isascii() and number.isdecimal() else ""
            at = int(number) if isinstance(lines, list) else 0
            if not 1 <= at <= len(lines) or wanted not in lines[at - 1].casefold():
                continue
            if len(rows) == room:
                return rows, True
            rows.append((self.full(path), at, lines[at - 1][:LINE_MAX_CHARS].rstrip()))
        return rows, False


def _libraries_shown(installed: Sequence[Environment]) -> str:
    """The installed libraries as a stage is told of them: each environment's, by name and version, and how to read
    one. A library a distribution names apart from its import, as PyYAML's `yaml`, says the import too."""
    lines = [
        "=== installed libraries, read offline: name a file as python:<path> or node:<path>, its path inside the "
        "environment as the example shows, or a library to list it"
    ]
    for one in installed:
        named = []
        for name, version, tops in one.packages[:LIBRARIES_SHOWN]:
            same = name.replace("_", "-").casefold()
            imports = [top for top in tops if top.replace("_", "-").casefold() != same]
            named.append(f"{name} {version}".strip() + (f" ({', '.join(imports)})" if imports else ""))
        more = len(one.packages) - LIBRARIES_SHOWN
        # A real path of the environment's: found live, `<path>` alone was read as the environment's path on disk.
        example = next(
            (path for path in one.paths if path.endswith(("/__init__.py", "/index.js"))), next(iter(one.paths), "")
        )
        such = f", a file named such as {one.scheme}:{example}" if example else ""
        said = f"{one.scheme} ({one.where}){such}: {', '.join(named)}" + (f", and {more:,} more" if more > 0 else "")
        unread = [line.split(":", 1)[0] for line in one.unread]
        lines.append(said + (f"; not read: {', '.join(unread[:10])}" if unread else ""))
    return "\n".join(lines)


def repositories_named(given: Sequence[str], held: Mapping[str, str]) -> dict[str, str]:
    """A change's repositories, `held`, with each one a person names added: `PATH`, named after its folder, or
    `NAME=PATH`, with forward slashes. A name given again takes its new path. `SourceError` for a name that cannot be
    made, or one named twice at once."""
    named = dict(held)
    this_time: set[str] = set()
    for one in given:
        name, sep, path = one.partition("=")
        if not sep or "/" in name or "\\" in name:  # a path alone, which may hold an `=` of its own
            name, path = "", one
        path = path.strip().replace("\\", "/")
        name = name.strip() or re.sub(r"[^a-z0-9-]+", "-", path.rstrip("/").rpartition("/")[2].lower()).strip("-")
        if not path or not NAME.fullmatch(name):
            raise SourceError(
                f"`--with {one}` names no repository adk-spec can name: a to z, digits and `-`, from a letter on. "
                "Name it as --with NAME=PATH"
            )
        if name in this_time:
            raise SourceError(f"`{name}` is named twice: name each repository once")
        this_time.add(name)
        named[name] = path
    return named


def _other(root: Path, name: str, given: str, folders: set[str], tops: dict[str, Path]) -> _Repository | str:
    """Another repository a change names, read as git lists it with its own exclusions, and given no trust of its
    own; or why it is left out, where it is not on this machine, cannot be read, or belongs to another account.
    `SourceError` where it can never stand beside this one: this repository, or one already named, by another
    spelling; a name that is a folder here; or a folder inside another adk-spec project, whose exclusions would not
    hold. `tops` holds the top of each repository taken so far, by name, this one's under the empty name."""
    if not NAME.fullmatch(name):
        raise SourceError(f"`{name}` is no name for a repository: a to z, digits and `-`, from a letter on")
    if name in folders:
        raise SourceError(
            f"`{name}` is also a folder of this repository, so `{name}/…` would mean two files. "
            "Give the repository another name, as --with NAME=PATH"
        )
    path = Path(given) if Path(given).is_absolute() else root / given
    try:
        if not path.is_dir() or not is_repository(path, trust=False):
            return f"{name}: no git repository at {given}"
    except GitError as exc:  # another account's, say: git will not open it untrusted
        return f"{name}: {exc}"
    its_top = top(path.resolve())
    for taken, held in tops.items():  # compared as the disk compares them, letter case and links included
        if its_top.samefile(held):
            raise SourceError(
                f"{name}: {given} is " + (f"the same repository as `{taken}`" if taken else "this repository itself")
            )
    project = next((folder for folder in path.resolve().parents if (folder / ROOT_NAME / CONFIG).is_file()), None)
    if project is not None and project.is_relative_to(its_top):
        shown = Path(given).parent if not Path(given).is_absolute() else project
        raise SourceError(
            f"{name}: {given} is inside the adk-spec project at {shown.as_posix()}, whose exclusions are written "
            "from there. Name that folder"
        )
    tops[name] = its_top
    own = path / ROOT_NAME / CONFIG  # its exclusions and its test command are its own, where it is an adk-spec project
    try:
        held = load_config(own) if own.is_file() else None
        exclude = held.exclude if held else ()
        found = _Repository(name, path, listed_by_git(path, exclude=exclude, trust=False), exclude)
        found.test, found.test_timeout = (held.test, held.test_timeout) if held else ((), 0)
        return found
    except (ConfigError, NotTextError, GitError, OSError) as exc:
        return f"{name}: {exc}"


class Source:
    """The files a stage may be shown: those of the repository that holds `.spec/`, and those of each other
    repository a change names, under its name."""

    def __init__(
        self, repositories: Sequence[_Repository], missing: Sequence[str] = (), installed: Sequence[Environment] = ()
    ) -> None:
        here, *others = repositories
        self._here = here
        self._others = {one.name: one for one in others}
        #: The installed libraries, an environment a scheme, kept apart: no search, diff, test or commit is theirs.
        self._installed = tuple(installed)
        self._libraries = {
            one.scheme: _Repository(one.scheme, one.root, one.paths, (), scheme=one.scheme) for one in installed
        }
        #: Every path a stage may name: this repository's, then each other's under its name, then each library's.
        self.paths = [one.full(path) for one in (*repositories, *self._libraries.values()) for path in one.paths]
        self._listed = frozenset(self.paths)
        #: The other repositories that were read, and a line for each one that was not.
        self.names = tuple(self._others)
        self.missing = tuple(missing)

    @classmethod
    def of(
        cls, root: Path, *, exclude: Sequence[str], others: Mapping[str, str] | None = None, installed: bool = False
    ) -> Source:
        """The source of the repository at `root`, as git lists it now, less what a person excluded; and of each of
        `others`, by its name a path from `root` or an absolute one. `SourceError` for one that can never be read
        beside this one; one that is not here now is named in `missing`. With `installed`, the project's installed
        libraries too, for a reading of the code."""
        here = _Repository("", root, listed_by_git(root, exclude=exclude), exclude)
        folders = {path.split("/", 1)[0] for path in here.paths if "/" in path}
        repositories, missing = [here], []
        tops = {"": top(root.resolve())}
        for name, given in (others or {}).items():
            found = _other(root, name, given, folders, tops)
            if isinstance(found, str):
                missing.append(found)
            else:
                repositories.append(found)
        return cls(repositories, missing, environments(root, exclude) if installed else ())

    def tree(self) -> str:
        """The files for a stage to name real paths by: this repository's, then each other's under a line that names
        it. Each is folded to its folders on its own, so a large repository does not crowd a small one out."""
        blocks = [tree_text(self._here.paths)]
        for one in self._others.values():
            listed = tree_text([one.full(path) for path in one.paths])
            blocks.append(f"=== {one.name} ({_counted(len(one.paths), 'file', 'files')})\n{listed}")
        if libraries := self.libraries():
            blocks.append(libraries)
        return "\n".join(blocks)

    def libraries(self) -> str:
        """The installed libraries as a stage is told of them, and how to read one: nothing where none are read."""
        return _libraries_shown(self._installed) if self._installed else ""

    def root_of(self, name: str) -> Path | None:
        """Another repository's root, or nothing where it was not read."""
        one = self._others.get(name)
        return None if one is None else one.root

    def why_not(self, name: str) -> str:
        """Why another repository was not read, as `missing` says it."""
        return next((line for line in self.missing if line.startswith(f"{name}: ")), f"{name}: it was not read")

    def work(self, base: str, bases: Mapping[str, str]) -> Work:
        """The work from `base` here and from each of `bases` in the repository it names, under its name.
        `SourceError` for a repository that was not read: the work is never judged on part of it."""
        made = [diffs(self._here.root, base, exclude=self._here.exclude)]
        for name, commit in bases.items():
            if (one := self._others.get(name)) is None:
                raise SourceError(f"{self.why_not(name)}: the work cannot be judged on part of it")
            made.append(diffs(one.root, commit, exclude=one.exclude, prefix=one.full(""), trust=False))
        text, held = self.without_keys("".join(shown for shown, _settled in made))
        return Work(text, held, sha256_of("".join(settled for _shown, settled in made)))

    def tests(self) -> list[tuple[str, Path, tuple[str, ...], int]]:
        """Each other repository's own test command, by its name, in its folder, with its timeout: the command
        each one's own `.spec/config.toml` names, read with its exclusions."""
        return [(one.name, one.root, one.test, one.test_timeout) for one in self._others.values() if one.test]

    def commits(self) -> dict[str, str | None]:
        """The commit each other repository has checked out, or nothing where git cannot say."""
        held: dict[str, str | None] = {}
        for name, one in self._others.items():
            try:
                held[name] = head(one.root, trust=False)
            except GitError:
                held[name] = None
        return held

    def gathered(self, files: Sequence[str], folders: Sequence[str], searches: Sequence[str]) -> Gathered:
        """One round: each file read, each folder listed and each search made, within the caps. What is past a cap
        or cannot be given is named among what was left out, and is no error."""
        got = _Round(ROUND_MAX_CHARS)
        # Searches first, then folders, then files: a search is small and aimed, a whole file large and often a
        # guess. Measured live, files taken first filled a round and left every search out.
        asked = (
            (searches, SEARCHES_A_ROUND, self._search, ("search", "searches"), "makes"),
            (folders, FOLDERS_A_ROUND, self._folder, ("folder", "folders"), "lists"),
            (files, FILES_A_ROUND, self._file, ("file", "files"), "reads"),
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

    def without_keys(self, diff: str) -> tuple[str, tuple[str, ...]]:
        """A unified diff less the part of each file that holds a private key, and those files' names. A file is
        known for one by how it stands in its repository, or by a key's first line among the lines the diff shows
        of it: the first covers a change in a key's middle, the second a key that was deleted or lost its first
        line. What is left is the diff a stage may be shown, and is still scrubbed as every text is."""
        kept: list[str] = []
        held: list[str] = []
        for path, part in parts_of_diff(diff):
            if holds_a_key(part) or (path is not None and self._keyed(path)):
                held.append(path or "(a file with no name)")
            else:
                kept.append(part)
        return "".join(kept), tuple(held)

    def within(self, path: str, line: int) -> str:
        """The line that opens the block `line` of `path` stands in: the nearest line above it, in the file as it
        stands, scrubbed, that is indented less than it. Nothing at the top level, or where the file is not read.
        Measured live: a real quote from `_approve` was kept under a note about `propose`, and only the block a line
        stands in shows that."""
        lines = self._lines(path) if path in self._listed else ""
        if not isinstance(lines, list) or not 1 <= line <= len(lines):
            return ""
        indent = _indent(lines[line - 1])
        for above in reversed(lines[: line - 1]):
            # A line of brackets alone, a C# or Java `{`, opens no block a person would name.
            if any(char.isalnum() for char in above) and _indent(above) < indent:
                return above.strip()[:WITHIN_MAX_CHARS]
        return ""

    def _where(self, path: str) -> tuple[_Repository, str]:
        """The repository a path a stage names is in, and the path within it: an installed library's by its scheme."""
        scheme, colon, inner = path.partition(":")
        if colon and inner and (library := self._libraries.get(scheme)) is not None:
            return library, inner
        name, _, rest = path.partition("/")
        other = self._others.get(name)
        return (other, rest) if other is not None and rest else (self._here, path)

    def _lines(self, path: str) -> list[str] | str:
        where, inner = self._where(path)
        return where.lines(inner)

    def _keyed(self, path: str) -> bool:
        where, inner = self._where(path)
        return where.keyed(inner)

    def _asked(self, asked: str) -> tuple[str, int | None, int | None]:
        """The path a model asked for, and the lines of it where it named a range. A path git lists is taken as it
        is, a colon in its name too."""
        asked = self._canonical(asked.strip())
        if asked not in self._listed and (ranged := _RANGE.fullmatch(asked)) and ranged["path"] in self._listed:
            return ranged["path"], int(ranged["first"]), int(ranged["last"])
        return asked, None, None

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

    def _canonical(self, asked: str) -> str:
        """A library's path as its environment lists it, where a model named it through the environment's folder:
        `python:.venv/lib/python3.11/site-packages/httpx/_client.py` is `python:httpx/_client.py`. Found live: named
        so, a library's file was said to be no file. Looked up in the list after, as any path is."""
        scheme, colon, inner = asked.partition(":")
        marker = _THROUGH.get(scheme) if colon and scheme in self._libraries else None
        return f"{scheme}:{inner.rpartition(marker)[2]}" if marker and marker in inner else asked

    def _folder(self, asked: str, got: _Round) -> None:
        folder = self._canonical(asked.strip()).strip("/")
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
        rows: list[tuple[str, int, str]] = []
        more = searched = False
        for one in (self._here, *self._others.values()):  # one search, in every repository, one block of lines
            try:
                found, more = one.hits(term, SEARCH_MAX_LINES - len(rows))
            except GitError as exc:
                got.left_out.append(f"search for {term}{f' in {one.name}' if one.name else ''}: {exc}")
                continue
            searched, rows = True, rows + found
            if more:
                break
        if not searched:  # a search git refused everywhere is said among what was left out, and shows nothing
            return
        note = _counted(len(rows), "line", "lines")
        note = f"more than {SEARCH_MAX_LINES} lines, the first {SEARCH_MAX_LINES} shown" if more else note
        shown = [f"{path}:{number}:{text}" for path, number, text in rows]
        if not got.shows("\n".join([f"=== search: {term} ({note})", *shown])):
            got.left_out.append(f"search for {term}: past what a round reads")
            got.deferred.append(asked)
            return
        for path, number, text in rows:
            got.holds(path, number, text)
