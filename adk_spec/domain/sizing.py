"""Sizing a change request by rule, so that the first model call of `propose` goes straight to the work.

A rule decides only where it is sure, and says why: a short request to fix a fault in behaviour, naming no risk and
no feature, is lean. Everything else is sized by a model, as before: a request that may owe no spec, a typo or a
cosmetic change in the sizing stage's own words; a long one, which may be standard or strict; and a fix that names a
risk, security or money or data, which the model may call strict. With the tier known, `propose` skips the sizing
call: the capabilities come from the brief.
"""

from __future__ import annotations

import re

from .model import Tier
from .text import flat

#: How long a request a rule calls a fix may be.
LEAN_MAX_CHARS = 240
#: Words of a request that may owe no spec: a typo, a cosmetic change, the docs, a throwaway prototype.
_NO_SPEC_SHAPED = re.compile(
    r"\b(typos?|spelling|wording|cosmetic|readme|docs?|documentation|comments?|prototype|throwaway)\b", re.IGNORECASE
)
#: Words of a fix that touches security, money or data: the model weighs it, and may call it strict. A list cannot
#: be whole; it only keeps the rule off the plainest of them.
_RISKY = re.compile(
    r"\b(auth(n|z|entic\w*|ori[sz]\w*)?|secur\w*|tokens?|passwords?|secrets?|credentials?|permissions?|log-?ins?|"
    r"sessions?|cookies?|injection|xss|csrf|encrypt\w*|privacy|payments?|billing|refunds?|invoices?|migrat\w*|"
    r"data loss|corrupt\w*)\b",
    re.IGNORECASE,
)
_FIX = re.compile(r"(fix|correct)\b", re.IGNORECASE)
#: Words that say what is fixed is a fault in behaviour: a bug fix, in the sizing stage's words.
_FAULT = re.compile(r"\b(bugs?|crash\w*|errors?|exceptions?|fail\w*|broken|wrong|hangs?|leaks?)\b", re.IGNORECASE)
_FEATURE = re.compile(r"\b(add|support|integrate|introduce|new|replace|redesign)\b", re.IGNORECASE)


def tier_by_rule(request: str) -> tuple[Tier, str] | None:
    """The tier a rule gives `request`, and why; nothing where the model should size it."""
    text = flat(request)
    if _NO_SPEC_SHAPED.search(text) or _RISKY.search(text):  # it may owe no spec, or be strict: the model says
        return None
    if len(text) <= LEAN_MAX_CHARS and _FIX.match(text) and _FAULT.search(text) and not _FEATURE.search(text):
        return "lean", "a short bug fix"
    return None
