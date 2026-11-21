"""The tasks stage: a change broken into tasks a coding agent carries out, each with how its result is checked."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from google.adk.agents import LlmAgent

from ...domain.drafts import TasksDraft
from . import ENDING, RETRY, fenced, placeholder, read_back, stage
from .brief import CONSTITUTION
from .deltas import BRIEF_TEXT, LIVING
from .design import DELTAS_TEXT

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
Write no task for anything the brief lists as a non-goal."""


def build_tasks() -> LlmAgent:
    instruction = "\n".join(
        [
            OPENING,
            "",
            "## What to write",
            GUIDE,
            "",
            RETRY,
            "",
            "## The rules of this repository",
            fenced("constitution", placeholder(CONSTITUTION, optional=True)),
            "",
            "## The living specs the change touches",
            fenced("living", placeholder(LIVING, optional=True)),
            "",
            "## The brief",
            fenced("brief", placeholder(BRIEF_TEXT)),
            "",
            "## The requirement deltas",
            fenced("deltas", placeholder(DELTAS_TEXT, optional=True)),
            "",
            "## The design",
            fenced("design", placeholder(DESIGN_TEXT, optional=True)),
            ENDING,
        ]
    )
    return stage(KEY, "Breaks a change into tasks.", instruction, TasksDraft)


def read_tasks(state: Mapping[str, Any]) -> TasksDraft | str:
    return read_back(state, KEY, TasksDraft)
