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
from dataclasses import dataclass
from pathlib import Path

from .files import NotTextError, read_text

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
    #: Each package's name, version and top-level names, by name.
    packages: tuple[tuple[str, str, tuple[str, ...]], ...]
    #: Every path a stage may read, from `root`, with forward slashes.
    paths: tuple[str, ...]


def environments(root: Path) -> list[Environment]:
    """The installed libraries of the project at `root`: its Python environment, then its `node_modules`."""
    return [found for found in (_python(root), _node(root)) if found is not None]


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


def _python(root: Path) -> Environment | None:
    found = _site(root)
    if found is None:
        return None
    where, site = found
    packages: list[tuple[str, str, tuple[str, ...]]] = []
    paths: set[str] = set()
    for info in sorted(site.glob("*.dist-info")):
        name, version = _metadata(info / "METADATA")
        if not name:
            continue
        files = [path for path in _record(info / "RECORD") if Path(path).suffix in PYTHON_SUFFIXES]
        tops = tuple(sorted({path.split("/", 1)[0].removesuffix(".py") for path in files}))
        packages.append((name, version, tops))
        paths.update(files)
    return Environment("python", where, site, tuple(packages), tuple(sorted(paths)[:LIBRARY_MAX_PATHS]))


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
    out of it, as a script in `bin` does, none that is compiled, and none of the record's own folder."""
    try:
        rows = csv.reader(io.StringIO(read_text(path)))
    except NotTextError, OSError:
        return []
    kept = []
    for row in rows:
        listed = row[0].replace("\\", "/") if row else ""
        parts = listed.split("/")
        if not listed or listed.startswith("/") or ":" in listed or ".." in parts or "__pycache__" in parts:
            continue
        if not parts[0].endswith(".dist-info"):
            kept.append(listed)
    return kept


def _node(root: Path) -> Environment | None:
    modules = root / "node_modules"
    if not _folder(modules):
        return None
    packages: list[tuple[str, str, tuple[str, ...]]] = []
    paths: list[str] = []
    for name, folder in _packages(modules):
        version = _version(folder / "package.json")
        packages.append((name, version, ()))  # imported by its own name
        paths += [f"{name}/{path}" for path in _walked(folder)]
        if len(paths) >= LIBRARY_MAX_PATHS:
            break
    return Environment("node", "node_modules", modules, tuple(packages), tuple(sorted(paths)[:LIBRARY_MAX_PATHS]))


def _packages(modules: Path) -> list[tuple[str, Path]]:
    """Each package `node_modules` holds, `react` or `@scope/kit`, as a folder of its own with a `package.json`. A
    linked package, as pnpm makes them, is not one: its files are another folder's."""
    found: list[tuple[str, Path]] = []
    for entry in sorted(modules.iterdir()):
        if entry.name.startswith(".") or not _folder(entry):
            continue
        inside = sorted(entry.iterdir()) if entry.name.startswith("@") else [entry]
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
