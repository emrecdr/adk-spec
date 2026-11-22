"""The workspace's settings, `.spec/config.toml`, read whole: a table or key the code does not know, a missing key
or a wrong value is refused by name, never passed over in silence."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import get_args

from ..domain.model import Tier
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


#: Each table the code reads, and the keys it reads there.
KNOWN = {"project": ("default_tier",), "limits": ("max_tokens", "keep_runs"), "repository": ("exclude",)}


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
        for key in keys if isinstance(keys, dict) else ():
            if key not in KNOWN[table]:
                raise ConfigError(f"{path} holds `{key}` under [{table}], which adk-spec does not read")
    project = held.get("project", {})
    if not isinstance(project, dict) or "default_tier" not in project:
        raise ConfigError(f"{path} lacks `default_tier` under [project]: one of {', '.join(TIERS)}")
    tier = project["default_tier"]
    if tier not in TIERS:
        raise ConfigError(f"{path} sets default_tier to `{tier}`, which is none of {', '.join(TIERS)}")
    limits = held.get("limits", {})
    ceiling = _whole(path, limits, "max_tokens", Config.max_tokens, "a whole number of tokens, 0 for no ceiling")
    keep = _whole(path, limits, "keep_runs", Config.keep_runs, "a whole number of recordings, 0 to keep none")
    return Config(default_tier=tier, max_tokens=ceiling, keep_runs=keep, exclude=_excluded(path, held))


def _excluded(path: Path, held: dict[str, object]) -> tuple[str, ...]:
    """The patterns under `[repository] exclude`, or none. Each is handed to git as a path to leave out, so one
    that opens with `:` is refused: git would read it as an instruction of its own."""
    repository = held.get("repository", {})
    value = repository.get("exclude", []) if isinstance(repository, dict) else []
    good = isinstance(value, list) and all(
        isinstance(one, str) and one.strip() and one.isprintable() and not one.startswith(":") for one in value
    )
    if not good:
        raise ConfigError(
            f"{path} sets exclude to `{value}`: a list of patterns, each a path from the workspace's root as git "
            'reads one, such as ["vendor/**", "**/*.pem"]'
        )
    return tuple(value)


def _whole(path: Path, limits: object, key: str, default: int, what: str) -> int:
    """A whole number of zero or more under `[limits]`, or its default where the key is not set."""
    value = limits.get(key, default) if isinstance(limits, dict) else default
    if type(value) is not int or value < 0:
        raise ConfigError(f"{path} sets {key} to `{value}`: {what}")
    return value
