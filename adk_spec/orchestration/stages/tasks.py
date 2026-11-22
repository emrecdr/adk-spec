"""The tasks stage: a change broken into tasks a coding agent carries out, each with how its result is checked."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from google.adk.agents import LlmAgent

from ...domain.drafts import TasksDraft
from . import (
    FILES,
    LIVING_SPECS,
    RULES,
    THE_BRIEF,
    THE_CONTEXT,
    THE_DELTAS,
    THE_PROFILE,
    instruction,
    read_back,
    section,
    stage,
)

KEY = "tasks"
#: The state key the change's design is read from, where it has one.
DESIGN_TEXT = "design_text"
OPENING = "You break a change into tasks for a coding agent to carry out. You write no code."
GUIDE = """\
Group the tasks by what each group delivers, in the order to do them. Number each group in its title.
A task is one step with one result. Put the task that writes a test before the task whose code it tests.
Name the requirement IDs each task serves, exactly as the deltas spell them. A setup task names none.
Give each task one way its result is checked: a command to run, or what to look at.
Mark a task parallel only where it touches other files than its neighbours and waits on none of them.
Write no task for anything the brief lists as a non-goal.
Name files by the paths the repository uses. Where a file is new, put it beside its kind.
Where what the repository already holds is given, name the files it names and follow the conventions it gives.
Where it lists something as still unknown, do not plan on it as if it were known: a task that depends on it says so."""


def build_tasks() -> LlmAgent:
    design = section("## The design", "design", DESIGN_TEXT, optional=True)
    text = instruction(
        OPENING, GUIDE, RULES, LIVING_SPECS, THE_PROFILE, FILES, THE_CONTEXT, THE_BRIEF, THE_DELTAS, design
    )
    return stage(KEY, "Breaks a change into tasks.", text, TasksDraft)


def read_tasks(state: Mapping[str, Any]) -> TasksDraft | str:
    return read_back(state, KEY, TasksDraft)
