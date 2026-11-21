"""The merge: a delta folded into its living spec by requirement ID, refused whole where its base has moved."""

from __future__ import annotations

import pytest
from samples import DELTA, SPEC

from adk_spec.domain.delta_md import parse_delta
from adk_spec.domain.merge import MergeError, apply_delta
from adk_spec.domain.model import Delta, Retired, Spec
from adk_spec.domain.spec_md import fingerprint, parse_spec
from adk_spec.domain.validate import validate_spec

BASES = {r.id: fingerprint(r) for r in parse_spec(SPEC).requirements}
ADDED_SCENARIO = (
    "#### Scenario: Registered passkey\n\n- WHEN the user presents a registered passkey\n"
    "- THEN the system starts a session\n\n"
)


def living() -> Spec:
    return parse_spec(SPEC)


def test_a_delta_folds_in_removed_then_modified_then_added() -> None:
    merged = apply_delta(living(), parse_delta(DELTA), bases=BASES, change="passkeys")
    assert [r.id for r in merged.requirements] == ["REQ-AUTH-002", "REQ-AUTH-004"]
    assert "three failed attempts" in merged.requirements[0].statement
    removed = Retired(id="REQ-AUTH-001", name="Sign in with email", change="passkeys")
    assert merged.retired == (*living().retired, removed)
    assert merged.purpose == living().purpose and validate_spec(merged) == []


def test_a_modified_block_keeps_its_place() -> None:
    only_modified = "# Delta: auth\n\n## MODIFIED Requirements\n\n" + (
        DELTA.split("## MODIFIED Requirements\n\n")[1].split("\n## REMOVED")[0].replace("REQ-AUTH-002", "REQ-AUTH-001")
    )
    merged = apply_delta(living(), parse_delta(only_modified), bases=BASES, change="x")
    assert [r.id for r in merged.requirements] == ["REQ-AUTH-001", "REQ-AUTH-002"]
    assert merged.requirements[0].name == "Lock after failures", "a rename is a modified block with the new name"


def test_a_requirement_changed_since_the_delta_was_based_refuses_the_merge() -> None:
    other = parse_spec(SPEC.replace("after five failed attempts", "after ten failed attempts"))
    with pytest.raises(MergeError) as refused:
        apply_delta(other, parse_delta(DELTA), bases=BASES, change="passkeys")
    assert [f.code for f in refused.value.findings] == ["delta.base-stale"]


def test_a_merge_without_a_recorded_base_is_refused() -> None:
    with pytest.raises(MergeError) as refused:
        apply_delta(living(), parse_delta(DELTA), bases={}, change="passkeys")
    assert {f.code for f in refused.value.findings} == {"delta.base-missing"}


def test_every_reason_is_reported_at_once() -> None:
    clash = DELTA.replace("REQ-AUTH-004", "REQ-AUTH-003")  # a retired id
    other = parse_spec(SPEC.replace("after five failed attempts", "after ten failed attempts"))
    with pytest.raises(MergeError) as refused:
        apply_delta(other, parse_delta(clash), bases=BASES, change="passkeys")
    assert sorted(f.code for f in refused.value.findings) == ["delta.added-exists", "delta.base-stale"]


def test_a_new_capability_starts_from_its_delta() -> None:
    added = parse_delta(DELTA).added[0].model_copy(update={"id": "REQ-SEARCH-001"})
    delta = Delta(capability="search", purpose="Find things.", added=(added,))
    assert apply_delta(None, delta, bases={}, change="add-search") == Spec(
        capability="search", purpose="Find things.", requirements=(added,)
    )


def test_a_merge_that_would_break_the_spec_is_refused() -> None:
    with pytest.raises(MergeError) as refused:
        apply_delta(living(), parse_delta(DELTA.replace(ADDED_SCENARIO, "")), bases=BASES, change="passkeys")
    assert "spec.no-scenario" in {f.code for f in refused.value.findings}


def test_a_warning_alone_does_not_refuse_a_merge() -> None:
    renamed = DELTA.replace("Scenario: Too many failures", "Scenario: Third failure")
    merged = apply_delta(living(), parse_delta(renamed), bases=BASES, change="passkeys")
    assert merged.requirements[0].scenarios[0].name == "Third failure"
