"""The survey stage: what the code that was read shows, for one change.

Each statement must name a file and quote the text it rests on, and code keeps only those whose quote is really in
that file. The stage may ask to see more; code decides whether another round is left.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from ...domain.drafts import SurveyDraft
from . import THE_BRIEF, THE_DELTAS, THE_LIBRARIES, instruction, section, stage

KEY = "survey"
#: The state keys of a round: what was read for it, the statements kept so far, and every file read so far.
MATERIAL = "material"
STATED = "stated"
READ = "read"
OPENING = "You read parts of a repository's code and state what in them matters for a change. You plan nothing."
GUIDE = """\
State only what the text you were shown shows: what the code is, never what the change should cover, which is the
person's to settle. For each statement, name one file by the path written above its
text, and copy from it the exact text the statement rests on: a line or a phrase, word for word. A statement whose
quote is not in that file is thrown away.
exists: behaviour or code already there that the change builds on, or must not write a second time.
touches: where the change plugs in, code that would be called, extended or changed.
convention: how this repository does a thing that new code should follow, such as where tests live or how an
error is raised.
risk: what the code leaves unclear, or what the change could break.
Say each thing once, and nothing the statements kept so far already say.
Where something that matters is not in what you were shown, ask for it: a file by its path, a folder to list, or a
word to search for. Ask only for what would change a statement. Empty lists are a good answer.
Where it turns on how an installed library behaves, ask for the library's file, python:<path> or node:<path>, its path
inside the environment as the list of libraries shows, or for python:<name> or node:<name> as a folder, to list the
library's files."""


def build_survey() -> LlmAgent:
    text = instruction(
        OPENING,
        GUIDE,
        section("## What was read for this round", "material", MATERIAL),
        section("## The statements kept so far", "stated", STATED, optional=True),
        section("## Every file read so far", "read", READ, optional=True),
        THE_LIBRARIES,
        THE_BRIEF,
        THE_DELTAS,
    )
    return stage(KEY, "States what the code that was read shows for a change.", text, SurveyDraft)
