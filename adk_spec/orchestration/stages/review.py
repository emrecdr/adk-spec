"""The review stage: what a reading of a repository's code kept, read by a second model as a reviewer.

It reads the statements, each with its quote and the line that opens the block it stands in, and no file: code
already checked that every quote is in its file. What a quote cannot show is whether the note is right about it, and
what the reading did not find at all. The review says both, and may ask for one more round of reading.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from ...domain.drafts import ReviewDraft
from . import THE_BRIEF, THE_DELTAS, THE_LIBRARIES, instruction, section, stage
from .survey import READ

KEY = "review"
#: The state keys of a review: the statements kept, numbered, and what the reading asked for and could not read.
NUMBERED = "numbered"
NOT_READ = "not_read"
OPENING = "You review what a reading of a repository's code found for a change. You read no file and plan nothing."
GUIDE = """\
Each statement above names a file and a line, the line that opens the block it stands in, its note, and the text it
quotes, which was found in that file. Dispute a statement only where its quote, or the block it stands in, does not
show what its note says: a note about one function that rests on a line of another, say. Give its number and why.
Then name what the change needs to know that no statement establishes: where it plugs in, what it must not break,
how this repository does such a thing. Ask each as a question, and say where it might be answered.
Where reading more would answer one, ask for it: a file by its path, a folder to list, or a word to search for.
Where the answer is in an installed library, ask for its file, python:<path> or node:<path>, or for the library to
list its files. Empty lists are a good answer."""


def build_review() -> LlmAgent:
    text = instruction(
        OPENING,
        GUIDE,
        section("## The statements kept", "statements", NUMBERED),
        section("## Every file read", "read", READ, optional=True),
        section("## What was asked for and not read", "not read", NOT_READ, optional=True),
        THE_LIBRARIES,
        THE_BRIEF,
        THE_DELTAS,
    )
    return stage(KEY, "Reviews what a reading of the code kept for a change.", text, ReviewDraft)
