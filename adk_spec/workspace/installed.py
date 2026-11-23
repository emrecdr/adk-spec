"""The libraries a repository's project has installed, as a reading may see them, offline and at the versions it runs.

Found at the repository's root: its Python environment, `.venv` or else `venv`, and its `node_modules`. Never the
environment adk-spec itself runs in, which is another project's. A Python distribution's files are those its own
`RECORD` lists, a Node package's those under its folder; each kept only where it is text a stage can use, under its
root, and reached through no link. What is listed here is read as a repository's files are, by `Source`: looked up in
this list, joined to the root only then, scrubbed whole, and withheld where it holds a private key.
"""

from __future__ import annotations

import csv
import io
import json
import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .files import NotTextError, read_text
from .git import as_globs

#: The folders a Python environment is looked for in, at the repository's root, in this order.
ENVIRONMENTS = (".venv", "venv")
PYTHON_SUFFIXES = frozenset({".py", ".pyi", ".md", ".rst", ".txt", ".json", ".toml", ".cfg"})
NODE_SUFFIXES = frozenset({".js", ".mjs", ".cjs", ".ts", ".mts", ".cts", ".json", ".md"})
#: The most paths an environment lists: a large one is read in part, never walked for minutes.
LIBRARY_MAX_PATHS = 50_000


@dataclass(frozen=True)
class Environment:
    """One environment's libraries: `python`, rooted at its `site-packages`, or `node`, at `node_modules`."""

    scheme: str
    #: The folder it was found in, from the repository's root: `.venv`, `venv` or `node_modules`.
    where: str
    root: Path
    #: Each package's name, version and import names apart from its own, by name.
    packages: tuple[tuple[str, str, tuple[str, ...]], ...]
    #: Every path a stage may read, from `root`, with forward slashes.
    paths: tuple[str, ...]
    #: Each package not read, with why: one a reader may not open, or past the cap.
    unread: tuple[str, ...] = ()


def environments(root: Path, exclude: Sequence[str] = ()) -> list[Environment]:
    """The installed libraries of the project at `root`: its Python environment, then its `node_modules`, less every
    path `exclude` keeps out of the repository's own files. One that cannot be opened at all is passed over: a reading
    never stops for it."""
    globs = tuple(glob.casefold() for glob in as_globs(exclude))
    found = []
    for build in (_python, _node):
        try:
            held = build(root, globs)
        except OSError:
            continue
        if held is not None:
            found.append(held)
    return found


def _excluded(path: str, globs: Sequence[str]) -> bool:
    """Whether `path`, from the repository's root, is one a person excluded, read as git reads the patterns."""
    held = PurePosixPath(path.casefold())
    return any(held.full_match(glob) for glob in globs)


def _folder(path: Path) -> bool:
    """Whether `path` is a folder reached through no link."""
    return path.is_dir() and not path.is_symlink() and not path.is_junction()


def _site(root: Path) -> tuple[str, Path] | None:
    """Where a Python environment at `root` keeps its libraries: Windows' layout, then POSIX's."""
    for where in ENVIRONMENTS:
        venv = root / where
        if not _folder(venv):
            continue
        if _folder(windows := venv / "Lib" / "site-packages"):
            return where, windows
        for site in sorted((venv / "lib").glob("python3*/site-packages")):
            if _folder(site):
                return where, site
    return None


class _Gathering:
    """An environment's packages as they are found: each listed with its files, or named as not read, and the cap
    kept by whole packages, so that no package is listed whose files were cut."""

    def __init__(self, base: str, globs: Sequence[str]) -> None:
        self.base, self.globs = base, globs
        self.packages: list[tuple[str, str, tuple[str, ...]]] = []
        self.paths: list[str] = []
        self.unread: list[str] = []
        #: The packages found once the cap was full: counted, never read, and not named, as one excluded is not.
        self.past = 0
        self._turned_away = False

    @property
    def full(self) -> bool:
        """Whether the cap is spent: filled, or a package turned away for it. Found by the code review: filled
        exactly alone, the walk went on past every package that overflowed it."""
        return self._turned_away or len(self.paths) >= LIBRARY_MAX_PATHS

    def add(self, name: str, version: str, tops: tuple[str, ...], files: Sequence[str]) -> None:
        kept = [path for path in files if not _excluded(f"{self.base}/{path}", self.globs)]
        if not kept and files:
            return  # excluded whole: not even named
        if len(self.paths) + len(kept) > LIBRARY_MAX_PATHS:
            self.unread.append(f"{name}: {_past_the_cap()}")
            self._turned_away = True
            return
        self.packages.append((name, version, tops))
        self.paths += kept

    def made(self, scheme: str, where: str, root: Path) -> Environment:
        if self.past:
            self.unread.append(f"{self.past} more package{'' if self.past == 1 else 's'}: {_past_the_cap()}")
        return Environment(
            scheme, where, root, tuple(self.packages), tuple(sorted(set(self.paths))), tuple(self.unread)
        )


def _past_the_cap() -> str:
    return f"past the {LIBRARY_MAX_PATHS:,} files an environment lists"


def _python(root: Path, globs: Sequence[str]) -> Environment | None:
    found = _site(root)
    if found is None or _excluded(found[0], globs):
        return None
    where, site = found
    held = _Gathering(site.relative_to(root).as_posix(), globs)
    for info in sorted(site.glob("*.dist-info")):
        name, version = _metadata(info / "METADATA")
        if not name:
            continue
        try:
            files = [path for path in _record(info / "RECORD") if Path(path).suffix in PYTHON_SUFFIXES]
        except csv.Error as exc:
            held.unread.append(f"{name}: its RECORD does not read: {exc}")
            continue
        held.add(name, version, _imports(files), files)
    return held.made("python", where, site)


def _imports(files: Sequence[str]) -> tuple[str, ...]:
    """What a distribution's files make importable at the top: each package folder, and each module or stub."""
    tops = {path.split("/", 1)[0] for path in files if "/" in path}
    tops |= {path.rsplit(".", 1)[0] for path in files if "/" not in path and path.endswith((".py", ".pyi"))}
    return tuple(sorted(tops))


def _metadata(path: Path) -> tuple[str, str]:
    """A distribution's name and version, from the header of its `METADATA`: nothing where it cannot be read."""
    try:
        header = read_text(path).split("\n\n", 1)[0]
    except NotTextError, OSError:
        return "", ""
    fields = dict(line.split(": ", 1) for line in header.splitlines() if ": " in line)
    return fields.get("Name", "").strip(), fields.get("Version", "").strip()


def _record(path: Path) -> list[str]:
    """The files a distribution's `RECORD` lists, kept only where they stay under `site-packages`: none that climbs
    out of it, as a script in `bin` does, none that is compiled, and none of the record's own folder. `csv.Error`
    where the record is no CSV the reader takes."""
    try:
        text = read_text(path)
    except NotTextError, OSError:
        return []
    kept = []
    for row in csv.reader(io.StringIO(text)):
        listed = row[0].replace("\\", "/") if row else ""
        parts = listed.split("/")
        if not listed or listed.startswith("/") or ":" in listed or ".." in parts or "__pycache__" in parts:
            continue
        if not parts[0].endswith(".dist-info"):
            kept.append(listed)
    return kept


def _node(root: Path, globs: Sequence[str]) -> Environment | None:
    modules = root / "node_modules"
    if not _folder(modules) or _excluded("node_modules", globs):
        return None
    held = _Gathering("node_modules", globs)
    for name, folder in _packages(modules):
        if held.full:  # found by the third audit: each package after the cap was walked whole, for nothing
            excluded = _excluded(f"node_modules/{name}", globs) or _excluded(f"node_modules/{name}/package.json", globs)
            held.past += not excluded
            continue
        try:
            files = [f"{name}/{path}" for path in _walked(folder)]
        except OSError as exc:
            held.unread.append(f"{name}: {exc.strerror or exc}")
            continue
        held.add(name, _version(folder / "package.json"), (), files)  # imported by its own name
    return held.made("node", "node_modules", modules)


def _packages(modules: Path) -> list[tuple[str, Path]]:
    """Each package `node_modules` holds, `react` or `@scope/kit`, as a folder of its own with a `package.json`. A
    linked package, as pnpm makes them, is not one: its files are another folder's. A scope a reader may not open is
    passed over."""
    found: list[tuple[str, Path]] = []
    for entry in sorted(modules.iterdir()):
        if entry.name.startswith(".") or not _folder(entry):
            continue
        try:
            inside = sorted(entry.iterdir()) if entry.name.startswith("@") else [entry]
        except OSError:
            continue
        found += [
            (folder.relative_to(modules).as_posix(), folder)
            for folder in inside
            if _folder(folder) and (folder / "package.json").is_file()
        ]
    return found


def _version(path: Path) -> str:
    try:
        held = json.loads(read_text(path))
    except NotTextError, OSError, ValueError:
        return ""
    return str(held.get("version", "")) if isinstance(held, dict) else ""


def _walked(folder: Path) -> list[str]:
    """A package's text files, from its folder: no link followed, no nested `node_modules` and no hidden folder. Walked
    with the system's own folder entries: measured by review, paths built for each file took a large `node_modules`
    1.4 s to list, and these 0.4 s."""
    found: list[str] = []
    pending = [("", os.fspath(folder))]
    while pending:
        inside, at = pending.pop()
        with os.scandir(at) as entries:
            for entry in entries:
                if entry.is_symlink() or entry.is_junction():
                    continue
                named = f"{inside}{entry.name}"
                if entry.is_dir(follow_symlinks=False):
                    if entry.name != "node_modules" and not entry.name.startswith("."):
                        pending.append((f"{named}/", entry.path))
                elif os.path.splitext(entry.name)[1] in NODE_SUFFIXES:
                    found.append(named)
    return sorted(found)
