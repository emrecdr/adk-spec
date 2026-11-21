"""The delta's grammar: three operations keyed by requirement ID, rendered canonically and parsed strictly."""

from __future__ import annotations

import pytest
from samples import DELTA

from adk_spec.domain.delta_md import parse_delta, render_delta
from adk_spec.domain.model import GrammarError, Removal


def test_a_canonical_delta_survives_parse_and_render_unchanged() -> None:
    assert render_delta(parse_delta(DELTA)) == DELTA


def test_parse_reads_each_operation() -> None:
    delta = parse_delta(DELTA)
    assert delta.capability == "auth" and delta.purpose is None
    assert [r.id for r in delta.added] == ["REQ-AUTH-004"] and [r.id for r in delta.modified] == ["REQ-AUTH-002"]
    assert delta.removed == (
        Removal(id="REQ-AUTH-001", name="Sign in with email", reason="Passwords are retired in favour of passkeys."),
    )


def test_a_new_capabilitys_delta_carries_its_purpose() -> None:
    added = DELTA.split("## ADDED Requirements\n\n")[1].split("\n## MODIFIED")[0].replace("AUTH", "SEARCH")
    new = "# Delta: search\n\n## Purpose\n\nFind things.\n\n## ADDED Requirements\n\n" + added
    assert parse_delta(new).purpose == "Find things." and render_delta(parse_delta(new)) == new


def test_a_removal_with_no_reason_parses_for_the_validator_to_judge() -> None:
    bare = DELTA.replace("Reason: Passwords are retired in favour of passkeys.\n", "")
    assert parse_delta(bare).removed[0].reason == ""
    assert parse_delta(render_delta(parse_delta(bare))) == parse_delta(bare)


def test_a_renamed_section_is_refused_and_told_what_to_write() -> None:
    with pytest.raises(GrammarError) as caught:
        parse_delta(DELTA.replace("## REMOVED Requirements", "## RENAMED Requirements"))
    assert caught.value.line == 25 and "MODIFIED block with the new name" in caught.value.message


def test_sections_out_of_order_are_refused() -> None:
    swapped = (
        "# Delta: auth\n\n## REMOVED Requirements\n\n### REQ-AUTH-001: Sign in with email\n\nReason: x\n\n"
        "## ADDED Requirements\n"
    )
    with pytest.raises(GrammarError) as caught:
        parse_delta(swapped)
    assert caught.value.line == 9


def test_text_under_a_removal_that_is_no_reason_is_refused() -> None:
    with pytest.raises(GrammarError) as caught:
        parse_delta(DELTA.replace("Reason: Passwords", "Because passwords"))
    assert caught.value.line == 29 and "Reason:" in caught.value.message
