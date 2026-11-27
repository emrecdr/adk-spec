"""The scout stage: what to read of a repository's code, before a change to it is planned.

It is shown the brief, the deltas and the paths of the repository's files, and reads none of them. Code reads what
it names, and only where git lists the path.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from ...domain.drafts import ScoutDraft
from . import FILES, RULES, THE_BRIEF, THE_DELTAS, THE_PROFILE, THE_RANKED, instruction, stage

KEY = "scout"
OPENING = "You choose what to read of a repository's code before a change to it is planned. You plan nothing."
GUIDE = """\
Name what a person would open to learn where this change belongs: the code it would call, extend or change, the
tests beside that code, and the configuration or documentation that says how this repository does such a thing.
Name a file by its path exactly as the list below spells it. For part of a long file add a range of lines:
src/app.py:120-260, or name one definition in it: src/app.py::Reader.read. Where the list shows a folder and not its
files, name the folder to have it listed, or a word to search for.
The files the code graph ranks first, where given, come from the names the code defines and from its imports, not from
reading it: a hint beside the list, never in its place.
An installed library, listed after the files, is worth a file only where the change depends on how it behaves at the
version installed: an option it takes, a default, what it raises.
A change that sets or relies on a library's option or default depends on it: a timeout, a retry, a limit. Name the
file that defines it, or the library itself to list its files. Libraries are not searched.
Name little, and what matters most first: twelve files, four folders and six searches are read at most."""


def build_scout() -> LlmAgent:
    text = instruction(OPENING, GUIDE, RULES, THE_PROFILE, FILES, THE_RANKED, THE_BRIEF, THE_DELTAS)
    return stage(KEY, "Chooses what to read of a repository's code for a change.", text, ScoutDraft)
