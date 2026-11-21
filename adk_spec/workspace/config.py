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


def load_config(path: Path) -> Config:
    """The settings `path` holds. `ConfigError` names what is unknown, missing or wrong."""
    try:
        held = tomllib.loads(read_text(path))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path} is not valid TOML: {exc}") from exc
    for table in held:
        if table != "project":
            raise ConfigError(f"{path} holds `{table}`, which adk-spec does not read. Its one table is [project]")
    project = held.get("project", {})
    for key in project if isinstance(project, dict) else ():
        if key != "default_tier":
            raise ConfigError(f"{path} holds `{key}` under [project], which adk-spec does not read")
    if not isinstance(project, dict) or "default_tier" not in project:
        raise ConfigError(f"{path} lacks `default_tier` under [project]: one of {', '.join(TIERS)}")
    tier = project["default_tier"]
    if tier not in TIERS:
        raise ConfigError(f"{path} sets default_tier to `{tier}`, which is none of {', '.join(TIERS)}")
    return Config(default_tier=tier)
