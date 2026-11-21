"""The merge: one change's delta folded into the living spec of its capability, by requirement ID.

Refused whole, with every reason at once, where the delta has an error, where a base is unrecorded or has moved, or
where the merged spec would have an error. Otherwise: each removed requirement leaves and is listed as retired, each
modified one is replaced where it stood, and each added one is appended in the delta's order.
"""

from __future__ import annotations

from collections.abc import Mapping

from .model import Delta, Finding, Retired, Spec
from .validate import validate_delta, validate_spec

#: A finding that refuses a merge whatever its severity: nothing is folded in against an unrecorded base.
REFUSES = frozenset({"delta.base-missing"})


class MergeError(Exception):
    """A merge refused: every finding that refused it."""

    def __init__(self, findings: tuple[Finding, ...]) -> None:
        super().__init__("; ".join(f"{found.code}: {found.message}" for found in findings))
        self.findings = findings


def _refusing(findings: list[Finding]) -> tuple[Finding, ...]:
    return tuple(found for found in findings if found.severity == "ERROR" or found.code in REFUSES)


def apply_delta(living: Spec | None, delta: Delta, *, bases: Mapping[str, str], change: str) -> Spec:
    """The living spec with `delta` folded in, `living` being None where the change creates the capability.
    `MergeError` where it is refused; nothing is changed then."""
    if refused := _refusing(validate_delta(delta, living, bases)):
        raise MergeError(refused)
    gone = {removal.id: removal for removal in delta.removed}
    replaced = {req.id: req for req in delta.modified}
    kept = [replaced.get(req.id, req) for req in (living.requirements if living else ()) if req.id not in gone]
    retired = [*(living.retired if living else ())]
    # The living requirement's own name, whatever the delta's block calls it: the list is the spec's record.
    names = {req.id: req.name for req in (living.requirements if living else ())}
    retired += [Retired(id=gone.id, name=names.get(gone.id, gone.name), change=change) for gone in delta.removed]
    merged = Spec(
        capability=delta.capability,
        purpose=living.purpose if living else (delta.purpose or ""),
        requirements=(*kept, *delta.added),
        retired=tuple(retired),
    )
    if refused := _refusing(validate_spec(merged)):
        raise MergeError(refused)
    return merged
