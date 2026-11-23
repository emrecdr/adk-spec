"""Rules the drafting stages follow, taken from the skills the owner pointed to (github.com/mattpocock/skills), each
where it fits adk-spec: written into the stage's own guide, so every model on either arm is told it."""

from __future__ import annotations

from adk_spec.orchestration.stages.brief import build_brief
from adk_spec.orchestration.stages.check import build_check
from adk_spec.orchestration.stages.deltas import build_deltas
from adk_spec.orchestration.stages.tasks import build_tasks


def test_the_brief_states_nothing_it_was_not_told_and_keeps_an_answers_exact_words() -> None:
    """to-spec: "If the spec states something you never said, that is a defect"; precise answers get softened."""
    told = str(build_brief().instruction)
    assert "State nothing the request, an answer or what the repository holds does not say." in told
    assert "Keep an answer's numbers, order and negatives exactly as the person gave them." in told


def test_each_scenario_is_written_so_that_a_run_could_show_it_false() -> None:
    """to-tickets: each criterion names the observation that would show it false."""
    assert "so that a run could show it false" in str(build_deltas().instruction)


def test_tasks_make_the_change_easy_first_slice_it_and_test_at_the_highest_seam() -> None:
    """to-tickets and tdd: prefactoring first, vertical slices, tests at the seams the repository has."""
    told = str(build_tasks().instruction)
    assert "make the change easy, then make the easy change" in told
    assert "can be seen working on its own" in told
    assert "highest seam the repository already has" in told


def test_a_bug_fixs_first_task_is_a_test_that_fails_on_the_bug_as_reported() -> None:
    """diagnosing-bugs: no fix before a command that goes red on the symptom."""
    assert "the first task is a test that fails on the bug as reported" in str(build_tasks().instruction)


def test_the_check_finds_a_requirement_that_softens_the_brief_or_could_never_fail() -> None:
    told = str(build_check().instruction)
    assert "softens a number, an order or a negative the brief gives" in told
    assert "a THEN no run could show false" in told


def test_the_brief_names_as_few_capabilities_as_hold_the_change() -> None:
    """Found live, phase 15: a brief that named three capabilities for one small change left the deltas stage
    unable to give each a requirement."""
    told = str(build_brief().instruction)
    assert "Name as few capabilities as hold the change" in told
    assert "Each capability you name gets one requirement at least." in told
