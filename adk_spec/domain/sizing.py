"""Sizing a change request by rules, so that the first model call of `propose` goes straight to the work.

A rule decides only where it is sure, and says why: a short request to fix a fault in behaviour is lean, and a long
one, or one that names several features, is standard. A request that may owe no spec at all, a typo or a cosmetic
change in the sizing stage's own words, is never sized by a rule, and neither is anything else a rule is unsure of:
the model sizes it, as before. With the tier known, `propose` skips the sizing call: the capabilities come from the
brief.
"""

from __future__ import annotations

import re

from .model import Tier
from .text import flat

#: How long a request a rule calls a fix may be, and how long one it calls a feature must be.
LEAN_MAX_CHARS = 240
STANDARD_MIN_CHARS = 600
#: A request this long that names two of the feature words is a feature too.
FEATURES_MIN_CHARS = 200
#: Words of a request that may owe no spec: a typo, a cosmetic change, the docs, a throwaway prototype.
_NO_SPEC_SHAPED = re.compile(
    r"\b(typos?|spelling|wording|cosmetic|readme|docs?|documentation|comments?|prototype|throwaway)\b", re.IGNORECASE
)
_FIX = re.compile(r"(fix|correct)\b", re.IGNORECASE)
#: Words that say what is fixed is a fault in behaviour: a bug fix, in the sizing stage's words.
_FAULT = re.compile(r"\b(bugs?|crash\w*|errors?|exceptions?|fail\w*|broken|wrong|hangs?|leaks?)\b", re.IGNORECASE)
_FEATURE_WORDS = frozenset({"add", "support", "integrate", "migrate", "introduce", "new", "replace", "redesign"})


def tier_by_rule(request: str) -> tuple[Tier, str] | None:
    """The tier rules give `request`, and why; nothing where the model should size it."""
    text = flat(request)
    if _NO_SPEC_SHAPED.search(text):  # it may owe no spec, which a rule never decides
        return None
    named = _FEATURE_WORDS & set(re.findall(r"[a-z]+", text.lower()))
    if len(text) <= LEAN_MAX_CHARS and _FIX.match(text) and _FAULT.search(text) and not named:
        return "lean", "a short bug fix"
    if len(text) >= STANDARD_MIN_CHARS or (len(text) >= FEATURES_MIN_CHARS and len(named) >= 2):
        return "standard", "a request of some length"
    return None
