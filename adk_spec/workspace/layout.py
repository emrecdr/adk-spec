"""The `.spec` tree: where each file is, and each file read into the domain's types or written from them.

    .spec/
      config.toml                       the workspace's settings
      constitution.md                   the rules every change follows
      specs/<capability>/spec.md        the living spec of one capability
      changes/<id>/change.json          a change's state
      changes/<id>/brief.md, design.md, tasks.md
      changes/<id>/specs/<capability>/spec.md   the change's delta for one capability

A file off its grammar is a finding with its path and line, never an exception: one bad file does not hide what the
others show. The state file is the code's own, so one that does not read as it was written is refused by name.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from ..domain.brief_md import parse_brief
from ..domain.check import coverage_of
from ..domain.delta_md import parse_delta
from ..domain.ids import REQ_ID, slug_problem
from ..domain.model import Change, ChangeState, Finding, GrammarError, Spec, Tier
from ..domain.spec_md import parse_spec, render_spec
from ..domain.tasks_md import parse_tasks
from ..domain.validate import finding, validate_change
from .config import DEFAULT, Config, load_config
from .files import NotTextError, read_text, write_all, write_text
from .paths import PathError, inside

ROOT_NAME = ".spec"
CONFIG, CONSTITUTION, SPECS, CHANGES = "config.toml", "constitution.md", "specs", "changes"
#: A repository's profile, written by `init` from a reading of its code: no part of any approval.
PROFILE = "profile.md"
STATE, BRIEF, DESIGN, TASKS, SPEC_FILE = "change.json", "brief.md", "design.md", "tasks.md", "spec.md"
#: The folder of a change's generated reports, which no approval fingerprints.
REPORTS = "reports"
#: What a reading of the repository's code found for a change. Supporting material: no approval covers it.
CONTEXT = "context.md"
#: What `adk-spec init` writes: the sections teams have found a constitution useful for.
CONSTITUTION_TEXT = """\
# Constitution

Version: 1

The rules every change in this repository follows. Keep it short, and give each rule its reason.

## Scope

## Domain context

## Technology and versions

## Coding standards

## Repository structure
"""
#: A finding that says a file is missing, and the file whose own fault makes it untrue.
_MISSING = {"change.missing-brief": BRIEF, "change.missing-tasks": TASKS, "change.no-deltas": SPECS}


class WorkspaceError(ValueError):
    """The workspace cannot do what was asked: one sentence for the person."""


@dataclass(frozen=True)
class LoadedChange:
    """A change read from its folder, and the faults of the files that did not read, their paths relative to it."""

    change: Change
    problems: list[Finding]


def findings_of(loaded: LoadedChange, living: Mapping[str, Spec], unreadable: Collection[str] = ()) -> list[Finding]:
    """Everything a change shows: the faults of its files, then what the validator finds in the ones that read. A
    file that did not read is not also reported as missing. `unreadable` names the capabilities whose living spec is
    there and does not read: a delta on one cannot be checked, and is said so once, never taken for a delta that
    creates the capability."""
    unread = {problem.path or "" for problem in loaded.problems}
    blind = {
        f"{SPECS}/{capability}/{SPEC_FILE}": capability
        for capability in unreadable
        if capability in loaded.change.deltas
    }
    found = list(loaded.problems)
    found += [
        finding(
            "delta.living-unreadable",
            f"The living spec of `{capability}` does not read, so this delta cannot be checked. Fix that spec first: "
            "`adk-spec validate` names its fault.",
            path=path,
        )
        for path, capability in sorted(blind.items())
    ]
    for held in validate_change(loaded.change, living):
        if held.path in blind:
            continue
        file = _MISSING.get(held.code)
        if file and any(path == file or path.startswith(f"{file}/") for path in unread):
            continue
        found.append(held)
    # With any living spec or one of the change's own deltas unread, what a task may name is unknown: a task may
    # serve a requirement of a capability the change does not touch.
    if not unreadable and not any(path.startswith(f"{SPECS}/") for path in unread):
        found += coverage_of(loaded.change, living)
    return found


class Workspace:
    """One repository's `.spec` tree."""

    def __init__(self, root: Path) -> None:
        #: The folder that holds `.spec`.
        self.root = root

    @property
    def home(self) -> Path:
        return self.root / ROOT_NAME

    @classmethod
    def find(cls, start: Path) -> Workspace:
        """The workspace `start` is in: the nearest folder at or above it that holds `.spec`."""
        for folder in (start, *start.parents):
            if (folder / ROOT_NAME).is_dir():
                return cls(folder)
        raise WorkspaceError(f"no {ROOT_NAME} folder at or above {start}. Run `adk-spec init` in the repository's root")

    @classmethod
    def init(cls, repo: Path) -> Workspace:
        """The tree made under `repo`, which must hold none yet."""
        workspace = cls(repo)
        if workspace.home.exists():
            raise WorkspaceError(f"{workspace.home} is already there. Nothing was changed")
        made = {CONFIG: DEFAULT, CONSTITUTION: CONSTITUTION_TEXT, ".gitignore": ".lock\n"}  # the lock is a run's own
        write_all({workspace.home / name: text for name, text in made.items()})
        for folder in (SPECS, CHANGES):
            (workspace.home / folder).mkdir()
        return workspace

    def shown(self, path: Path) -> str:
        """`path` as a person reads it: from the repository's root, with forward slashes on every system."""
        return path.relative_to(self.root).as_posix()

    def config(self) -> Config:
        return load_config(self.home / CONFIG)

    def _holding(self, folder: Path, file: str) -> list[str]:
        """The sorted names of the folders in `folder` that hold `file`."""
        if not folder.is_dir():
            return []
        return sorted(entry.name for entry in folder.iterdir() if (entry / file).is_file())

    def capabilities(self) -> list[str]:
        return self._holding(self.home / SPECS, SPEC_FILE)

    def changes(self) -> list[str]:
        return self._holding(self.home / CHANGES, STATE)

    def specs(self) -> tuple[dict[str, Spec], list[Finding]]:
        """Every living spec that reads, by capability, and the faults of the rest, their paths from the root."""
        specs: dict[str, Spec] = {}
        problems: list[Finding] = []
        for capability in self.capabilities():
            path = self.home / SPECS / capability / SPEC_FILE
            if why := slug_problem(capability):
                problems.append(_misnamed(why, self.shown(path)))
                continue
            spec = _read(path, parse_spec, self.shown(path), problems)
            if spec is None:
                continue
            if spec.capability != capability:
                problems.append(_misplaced(spec.capability, capability, self.shown(path)))
            else:
                specs[capability] = spec
        return specs, problems

    def write_specs(self, specs: Mapping[str, Spec], *, state: ChangeState | None = None) -> None:
        """Each spec written in its canonical form and, where given, a change's state beside them: every file, or
        none, as far as the file system allows."""
        files = {
            inside(self.home, SPECS, capability, SPEC_FILE): render_spec(spec) for capability, spec in specs.items()
        }
        if state is not None:
            files[inside(self.home, CHANGES, state.id, STATE)] = state.model_dump_json(indent=2)
        write_all(files)

    def _folder(self, change_id: str) -> Path:
        """The folder of an existing change."""
        try:
            folder = inside(self.home, CHANGES, change_id)
        except PathError as exc:
            raise WorkspaceError(f"there is no change `{change_id}`: {exc}") from exc
        if not (folder / STATE).is_file():
            raise WorkspaceError(f"there is no change `{change_id}`. `adk-spec status --all` lists every change")
        return folder

    def free(self, change_id: str) -> Path:
        """The folder a new change of this name would take. `WorkspaceError` where the name cannot be a change's, or
        something holds it already: a change, or a folder that is none."""
        if why := slug_problem(change_id):
            raise WorkspaceError(f"a change cannot be named so: {why}")
        try:
            folder = inside(self.home, CHANGES, change_id)
        except PathError as exc:
            raise WorkspaceError(f"a change cannot be named so: {exc}") from exc
        if folder.exists():
            raise WorkspaceError(f"the change `{change_id}` exists already")
        return folder

    def names_held(self) -> list[str]:
        """Every name under `changes/`, a change's or not: none of them is free for a new change."""
        folder = self.home / CHANGES
        return sorted(entry.name for entry in folder.iterdir()) if folder.is_dir() else []

    def new_change(self, change_id: str, tier: Tier) -> Path:
        """A new draft change's folder, holding its state file."""
        return self.write_change(ChangeState(id=change_id, tier=tier), {})

    def taken(self, specs: Mapping[str, Spec]) -> set[str]:
        """Every requirement ID that is spoken for: in a living spec of `specs`, retired there, or spelled in a
        delta of an open change. A new requirement is numbered past all of its capability's, so two open changes
        never share one, in a capability a spec holds or in one they both create.

        A delta is read as text, not parsed: one that is off its grammar, mid-edit, still holds the IDs it adds."""
        taken = {held.id for spec in specs.values() for held in (*spec.requirements, *spec.retired)}
        for change_id in self.changes():
            folder = self._folder(change_id)
            if self._state(folder, change_id).status == "archived":  # history grows, and is not read
                continue
            for capability in self._holding(folder / SPECS, SPEC_FILE):
                text = _text_or_bytes(folder / SPECS / capability / SPEC_FILE)
                taken.update(spelled.group(0) for spelled in REQ_ID.finditer(text))
        return taken

    def _placed(self, folder: Path, files: Mapping[str, str]) -> dict[Path, str]:
        """Each of `files` by the path it takes in `folder`. `WorkspaceError` for a path that leaves it."""
        try:
            return {inside(folder, *path.split("/")): text for path, text in files.items()}
        except PathError as exc:
            raise WorkspaceError(f"the change cannot be written: {exc}") from exc

    def write_change(self, state: ChangeState, files: Mapping[str, str]) -> Path:
        """A new change made whole: its folder, each of `files` by its path in the folder, and its state, written
        as one set. Where the write fails the folder is removed again, so no half-made change is left."""
        folder = self.free(state.id)
        texts = self._placed(folder, files)
        texts[folder / STATE] = state.model_dump_json(indent=2)
        try:
            write_all(texts)
        except BaseException:
            shutil.rmtree(folder, ignore_errors=True)
            raise
        return folder

    def write_into(self, change_id: str, files: Mapping[str, str]) -> list[Path]:
        """Each of `files` written into an existing change's folder, by its path there, as one set."""
        texts = self._placed(self._folder(change_id), files)
        write_all(texts)
        return list(texts)

    def write_report(self, change_id: str, name: str, text: str) -> Path:
        """A generated report of a change, under its `reports/` folder: written whole, replacing the one before."""
        return self.write_into(change_id, {f"{REPORTS}/{name}": text})[0]

    def save_state(self, state: ChangeState) -> None:
        write_text(inside(self.home, CHANGES, state.id, STATE), state.model_dump_json(indent=2))

    def _state(self, folder: Path, change_id: str) -> ChangeState:
        """A change's state file alone. `WorkspaceError` where it does not read, or names another change."""
        try:
            state = ChangeState.model_validate_json(read_text(folder / STATE))
        except ValidationError as exc:
            first = exc.errors()[0]
            where = ".".join(str(part) for part in first["loc"]) or "the file"
            raise WorkspaceError(f"{self.shown(folder / STATE)} does not read: `{where}`: {first['msg']}") from exc
        if state.id != change_id:  # a renamed or copied folder: each save would go to the other change's file
            raise WorkspaceError(
                f"{self.shown(folder / STATE)} names the change `{state.id}`, and its folder is `{change_id}`. "
                "Make the two the same"
            )
        return state

    def load_change(self, change_id: str) -> LoadedChange:
        """The change read from its folder. `WorkspaceError` where there is none, or its state file does not read."""
        folder = self._folder(change_id)
        state = self._state(folder, change_id)
        problems: list[Finding] = []
        raw = _read(folder / BRIEF, str, BRIEF, problems) if (folder / BRIEF).is_file() else None
        brief = _parsed(raw, parse_brief, BRIEF, problems) if raw is not None else None
        tasks = _read(folder / TASKS, parse_tasks, TASKS, problems) if (folder / TASKS).is_file() else None
        deltas = {}
        for capability in self._holding(folder / SPECS, SPEC_FILE):
            shown = f"{SPECS}/{capability}/{SPEC_FILE}"
            if why := slug_problem(capability):
                problems.append(_misnamed(why, shown))
                continue
            delta = _read(folder / SPECS / capability / SPEC_FILE, parse_delta, shown, problems)
            if delta is None:
                continue
            if delta.capability != capability:
                problems.append(_misplaced(delta.capability, capability, shown))
            else:
                deltas[capability] = delta
        design = _read(folder / DESIGN, str, DESIGN, problems) if (folder / DESIGN).is_file() else None
        change = Change(state=state, brief=brief, brief_raw=raw, deltas=deltas, tasks=tasks, design=design)
        return LoadedChange(change, problems)

    def approval_texts(self, change_id: str) -> dict[str, str]:
        """The text of each file an approval covers, by its path in the change's folder."""
        folder = self._folder(change_id)
        paths = [BRIEF, DESIGN, TASKS]
        paths += [f"{SPECS}/{capability}/{SPEC_FILE}" for capability in self._holding(folder / SPECS, SPEC_FILE)]
        return {path: _text_or_bytes(folder / path) for path in paths if (folder / path).is_file()}


def _text_or_bytes(path: Path) -> str:
    """A file's text for a fingerprint. One that is not UTF-8 is read with its bad bytes replaced: the loader names
    its fault as a finding, and its fingerprint must not stop every other change from being read."""
    try:
        return read_text(path)
    except NotTextError:
        return path.read_bytes().decode("utf-8", errors="replace")


def _misnamed(why: str, shown: str) -> Finding:
    return finding("spec.folder-bad-name", f"The folder cannot name a capability: {why}. Rename it.", path=shown)


def _misplaced(titled: str, folder: str, shown: str) -> Finding:
    return finding(
        "spec.folder-mismatch",
        f"The file is titled for `{titled}` and stands in the folder `{folder}`. Make the two the same.",
        path=shown,
    )


def _read[T](path: Path, parse: Callable[[str], T], shown: str, problems: list[Finding]) -> T | None:
    """`path` read and parsed, or None with its fault added to `problems`."""
    try:
        text = read_text(path)
    except NotTextError as exc:
        problems.append(finding("syntax", str(exc), path=shown))
        return None
    return _parsed(text, parse, shown, problems)


def _parsed[T](text: str, parse: Callable[[str], T], shown: str, problems: list[Finding]) -> T | None:
    try:
        return parse(text)
    except GrammarError as exc:
        problems.append(finding("syntax", f"{exc.message}.", path=shown, line=exc.line))
        return None
