"""The check stage: a change's files read against each other, before anyone approves them.

What code can decide is decided before this stage runs: structure, and which requirement has a task. This stage is
asked for what takes a reading: two files that disagree, wording that allows two readings, a promise no requirement
keeps, a rule of the repository that is broken. Each finding must quote the text it is about, and code keeps only
those whose quote is really in the file they name.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from google.adk.agents import LlmAgent

from ...domain.drafts import FindingsDraft
from . import CHANGE_FILES, LIVING_SPECS, RULES, instruction, read_back, section, stage

KEY = "check"
OPENING = "You review the files of a change against each other. You change none of them."
GUIDE = """\
Look for what the files say against each other, and against the rules of this repository:
a contradiction between two files; wording in a requirement or a task that allows two readings; something the brief
promises that no requirement delivers; a requirement that softens a number, an order or a negative the brief gives;
a THEN no run could show false; one requirement stated twice; a rule of the repository the change breaks.
Report every fault you find. One finding does not excuse the next.
Report only what you can point to. For each finding, name one file by the path given above it and copy from it the
exact text the finding is about: a line or a phrase, word for word.
critical means the change would be built wrong as it stands. warning means worth a look. note is a remark.
Leave out what a check of structure finds without you: a missing section, a malformed ID, a requirement with no
task. An empty list is a good answer."""


def build_check() -> LlmAgent:
    files = section("## The files of the change", "change", CHANGE_FILES)
    return stage(
        KEY,
        "Reviews a change's files against each other.",
        instruction(OPENING, GUIDE, RULES, LIVING_SPECS, files),
        FindingsDraft,
    )


def read_check(state: Mapping[str, Any]) -> FindingsDraft | str:
    return read_back(state, KEY, FindingsDraft)
