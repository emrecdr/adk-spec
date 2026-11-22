"""Sizing a change request by rules, so that the first model call of `propose` goes straight to the work.

A rule decides only where it is sure, and says why: a short request that opens with a fix is lean, and a long one,
or one that names several features, is standard. Everything else, a request that may owe no spec at all included,
is sized by a model, as before. With the tier known, `propose` skips the sizing call: the capabilities come from the
brief.
"""

from __future__ import annotations

import re

from .model import Tier

#: How long a request a rule calls a fix may be, and how long one it calls a feature must be.
LEAN_MAX_CHARS = 240
STANDARD_MIN_CHARS = 600
#: A request this long that names two of the feature words is a feature too.
FEATURES_MIN_CHARS = 200
_FIX = re.compile(r"^(fix|correct|rename|reword|bump)\b|\btypos?\b", re.IGNORECASE)
_FEATURE_WORDS = frozenset({"add", "support", "integrate", "migrate", "introduce", "new", "replace", "redesign"})


def sized(request: str) -> tuple[Tier, str] | None:
    """The tier rules give `request`, and why; nothing where the model should size it."""
    text = " ".join(request.split())
    if len(text) <= LEAN_MAX_CHARS and _FIX.search(text):
        return "lean", "a short fix"
    named = _FEATURE_WORDS & set(re.findall(r"[a-z]+", text.lower()))
    if len(text) >= STANDARD_MIN_CHARS or (len(text) >= FEATURES_MIN_CHARS and len(named) >= 2):
        return "standard", "a request of some length"
    return None
