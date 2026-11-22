"""The workspace's settings, `.spec/config.toml`, read whole: a table or key the code does not know, a missing key
or a wrong value is refused by name, never passed over in silence."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import get_args

from ..domain.model import BUILT_TIERS, Tier
from .files import read_text

TIERS = get_args(Tier)
#: What `adk-spec init` writes.
DEFAULT = """\
# adk-spec's settings for this repository. Read whole: a key the code does not know is refused by name.
[project]
# The tier a new change gets where none is named: lean, standard or strict.
default_tier = "standard"
"""


class ConfigError(ValueError):
    """A config file that is not what the code reads."""


@dataclass(frozen=True)
class Config:
    default_tier: Tier
    #: The tokens one command may spend, every stage of it. 0 means no ceiling.
    max_tokens: int = 0
    #: How many commands' model calls are kept under `.spec/runs/`, the newest ones. 0 keeps none.
    keep_runs: int = 20
    #: Paths no command lists, reads or sends: each a pattern git reads as a path from the workspace's root, such
    #: as `vendor/**` or `**/*.pem`.
    exclude: tuple[str, ...] = ()
    #: The command `verify` runs the project's tests with, as the words a person wrote: none where it is not set.
    test: tuple[str, ...] = ()
    #: How long a test run may take, in seconds, before it is stopped and counts as failed.
    test_timeout: int = 900


#: Each table the code reads, and the keys it reads there.
KNOWN = {
    "project": ("default_tier",),
    "limits": ("max_tokens", "keep_runs"),
    "repository": ("exclude",),
    "verify": ("test", "timeout"),
}


def load_config(path: Path) -> Config:
    """The settings `path` holds. `ConfigError` names what is unknown, missing or wrong."""
    try:
        held = tomllib.loads(read_text(path))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path} is not valid TOML: {exc}") from exc
    for table, keys in held.items():
        if table not in KNOWN:
            raise ConfigError(
                f"{path} holds `{table}`, which adk-spec does not read. Its tables are {', '.join(KNOWN)}"
            )
        if not isinstance(keys, dict):  # read as no table, `repository = [...]` would keep nothing out
            raise ConfigError(
                f"{path} sets `{table}` to a value, and `{table}` is a table: write `[{table}]` on a line of its "
                "own, and its keys under it"
            )
        for key in keys:
            if key not in KNOWN[table]:
                raise ConfigError(f"{path} holds `{key}` under [{table}], which adk-spec does not read")
    project = held.get("project", {})
    if not isinstance(project, dict) or "default_tier" not in project:
        raise ConfigError(f"{path} lacks `default_tier` under [project]: one of {', '.join(BUILT_TIERS)}")
    tier = project["default_tier"]
    if tier not in BUILT_TIERS:
        raise ConfigError(f"{path} sets default_tier to `{tier}`, which is none of {', '.join(BUILT_TIERS)}")
    limits = held.get("limits", {})
    ceiling = _whole(path, limits, "max_tokens", Config.max_tokens, "a whole number of tokens, 0 for no ceiling")
    keep = _whole(path, limits, "keep_runs", Config.keep_runs, "a whole number of recordings, 0 to keep none")
    test, timeout = _verifying(path, held.get("verify", {}))
    return Config(
        default_tier=tier,
        max_tokens=ceiling,
        keep_runs=keep,
        exclude=_excluded(path, held),
        test=test,
        test_timeout=timeout,
    )


def _verifying(path: Path, verify: object) -> tuple[tuple[str, ...], int]:
    """The test command under `[verify]`, as a list of words, and its timeout in seconds. A string is refused: no
    shell reads the command, and splitting a string into words is a guess on Windows."""
    held = verify if isinstance(verify, dict) else {}
    test = held.get("test", [])
    words = isinstance(test, list) and all(isinstance(one, str) and one.strip() and one.isprintable() for one in test)
    if not words or ("test" in held and not test):
        raise ConfigError(
            f"{path} sets test to `{test}`: a list of words, the program first, such as "
            '["uv", "run", "pytest", "-q"]. No shell reads it'
        )
    what = "a whole number of seconds, from 1 to 86400, a day"
    timeout = _whole(path, held, "timeout", Config.test_timeout, what, least=1, most=86_400)
    return tuple(test), timeout


def _pattern(one: str) -> bool:
    """Whether `one` is a pattern git takes for a path under the workspace's root: some text on one line, with no
    colon at its start, which git reads as an instruction of its own, and no way out of the root, which git refuses,
    so that every file would then be listed and read with nothing said."""
    inside = not one.startswith(("/", ":")) and ".." not in one.split("/")
    return bool(one.strip()) and one.isprintable() and one == one.strip() and inside


def _excluded(path: Path, held: dict[str, object]) -> tuple[str, ...]:
    """The patterns under `[repository] exclude`, or none. Each is handed to git as a path to leave out, so one
    that opens with `:` is refused: git would read it as an instruction of its own."""
    repository = held.get("repository", {})
    value = repository.get("exclude", []) if isinstance(repository, dict) else []
    good = isinstance(value, list) and all(isinstance(one, str) and _pattern(one) for one in value)
    if not good:
        raise ConfigError(
            f"{path} sets exclude to `{value}`: a list of patterns, each a path from the workspace's root as git "
            'reads one, such as ["vendor/**", "**/*.pem"]'
        )
    return tuple(value)


def _whole(
    path: Path, table: object, key: str, default: int, what: str, *, least: int = 0, most: int | None = None
) -> int:
    """A whole number from `least` to `most` under a table, or its default where the key is not set."""
    value = table.get(key, default) if isinstance(table, dict) else default
    if type(value) is not int or value < least or (most is not None and value > most):
        raise ConfigError(f"{path} sets {key} to `{value}`: {what}")
    return value
