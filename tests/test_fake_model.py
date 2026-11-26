"""The tests' own fake model: what a test sets it to answer is held to the requests it is sent."""

from __future__ import annotations

from types import SimpleNamespace

from conftest import FakeProvider


def _request(instruction: str):
    return SimpleNamespace(config=SimpleNamespace(system_instruction=instruction))


def test_a_rule_no_request_matched_is_named() -> None:
    """Found by the audit of 25 November: tests aim the fake by a stage's opening line, copied into the test, and a
    rule whose text no longer matched was passed over in silence, the test running on the canned answer."""
    fake = FakeProvider()
    fake.answers_when("You size a change request", {"tier": "lean"})
    fake.answers_when("You write the brief", {"brief": "x"})
    fake.answer(_request("You size a change request.\nThe request: x"))
    assert fake.unmatched() == ["You write the brief"]


def test_a_default_for_a_stage_that_may_not_be_asked_is_not_named() -> None:
    fake = FakeProvider()
    fake.answers_if_asked("You review the files of a change", {"findings": []})
    assert fake.unmatched() == []
    fake.clear()
    fake.answers_when("You review the files of a change", {"findings": []})
    assert fake.unmatched() == ["You review the files of a change"], "a clear forgets which rules were optional"


def test_a_clear_part_way_through_a_test_names_the_rules_it_would_forget() -> None:
    """Found by the code review of phase 21: a test that cleared the fake part-way through threw its first rules
    away unchecked. The rules are forgotten all the same, so none reaches the next test."""
    import pytest

    fake = FakeProvider()
    fake.answers_when("You write the brief", {"brief": "x"})
    with pytest.raises(AssertionError, match="You write the brief"):
        fake.clear()
    assert fake.rules == [] and fake.unmatched() == []
    fake.answers_when("You write the brief", {"brief": "x"})
    fake.clear(check=False)  # a test whose body failed already is not told of rules it never reached
