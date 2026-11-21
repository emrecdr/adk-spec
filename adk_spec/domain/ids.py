"""The identifier grammar: a capability's slug, a requirement's ID and a task's ID.

A slug becomes a folder's name, so it is lowercase ASCII, short, and no name Windows reserves. A requirement's ID
carries its capability and a number that is never reused, so a name may change and the ID stays.
"""

from __future__ import annotations

import ntpath
import re
from collections.abc import Iterable

SLUG = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")
SLUG_MAX = 40
#: `REQ-`, the capability's slug in upper case, `-`, and a number of three digits or more.
REQ_ID = re.compile(r"REQ-([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*)-(\d{3,})")
#: `T` and three digits or more.
TASK_ID = re.compile(r"T\d{3,}")


def slug_problem(slug: str) -> str | None:
    """Why `slug` cannot name a capability or a change, or None where it can."""
    if not SLUG.fullmatch(slug):
        return f"{slug!r} is not lowercase ASCII words joined by single hyphens, starting with a letter"
    if len(slug) > SLUG_MAX:
        return f"{slug!r} is longer than {SLUG_MAX} characters"
    if ntpath.isreserved(slug):  # a pure function, the same answer on every system
        return f"{slug!r} is a name Windows reserves"
    return None


def requirement_id(capability: str, number: int) -> str:
    """The ID of requirement `number` of `capability`: `REQ-BILLING-EXPORT-007`."""
    return f"REQ-{capability.upper()}-{number:03d}"


def capability_of(req_id: str) -> str | None:
    """The capability a requirement ID carries, as its slug, or None where `req_id` is no requirement ID."""
    found = REQ_ID.fullmatch(req_id)
    return found[1].lower() if found else None


def number_of(req_id: str) -> int:
    """The number a requirement ID ends in. `ValueError` where `req_id` is no requirement ID."""
    found = REQ_ID.fullmatch(req_id)
    if found is None:
        raise ValueError(f"{req_id!r} is no requirement ID")
    return int(found[2])


def next_requirement_id(capability: str, taken: Iterable[str]) -> str:
    """The next ID of `capability`: one past the highest number among `taken`, living and retired alike, so no
    number is ever used twice."""
    numbers = [number_of(held) for held in taken if capability_of(held) == capability]
    return requirement_id(capability, max(numbers, default=0) + 1)
