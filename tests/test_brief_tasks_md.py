"""The brief's and the task list's grammars: rendered canonically and parsed strictly."""

from __future__ import annotations

import pytest
from samples import BRIEF, TASKS

from adk_spec.domain.brief_md import markers, parse_brief, render_brief
from adk_spec.domain.model import GrammarError
from adk_spec.domain.tasks_md import parse_tasks, render_tasks


def test_a_canonical_brief_and_tasks_file_survive_parse_and_render_unchanged() -> None:
    assert render_brief(parse_brief(BRIEF)) == BRIEF and render_tasks(parse_tasks(TASKS)) == TASKS


def test_parse_reads_the_briefs_sections() -> None:
    brief = parse_brief(BRIEF)
    assert brief.title == "Sign in with a passkey" and brief.capabilities == ("auth",)
    assert brief.non_goals == "No change to session length."
    assert brief.what_changes == "Users can register a passkey and sign in with it."


def test_a_brief_missing_a_section_parses_and_one_it_does_not_know_is_refused() -> None:
    assert parse_brief(BRIEF.replace("## Impact\n\nThe sign-in page and the session service.\n\n", "")).impact == ""
    with pytest.raises(GrammarError) as caught:
        parse_brief(BRIEF.replace("## Impact", "## Rollout"))
    assert caught.value.line == 19 and "Rollout" in caught.value.message


def test_a_capability_that_is_no_list_item_is_refused() -> None:
    with pytest.raises(GrammarError) as caught:
        parse_brief(BRIEF.replace("- auth", "auth and billing"))
    assert caught.value.line == 17


def test_markers_are_found_with_and_without_a_question() -> None:
    text = BRIEF + "[NEEDS CLARIFICATION: which browsers?] and [NEEDS CLARIFICATION]\n"
    assert markers(text) == ["[NEEDS CLARIFICATION: which browsers?]", "[NEEDS CLARIFICATION]"]
    assert markers(BRIEF) == []


def test_parse_reads_each_tasks_fields() -> None:
    (group,) = parse_tasks(TASKS)
    one, two, three = group.tasks
    assert group.title == "1. Passkey sign-in"
    assert (one.id, one.done, one.parallel, one.requirements) == ("T001", False, False, ("REQ-AUTH-004",))
    assert (two.done, two.parallel, two.requirements) == (True, True, ("REQ-AUTH-004", "REQ-AUTH-002"))
    assert two.files == ("src/auth/passkey.py", "src/auth/lockout.py")
    assert one.verify == "uv run pytest tests/test_passkey.py" and one.description.startswith("Write the failing")
    assert (three.requirements, three.files, three.verify) == ((), (), "read the page")


def test_unchecked_renders_every_box_empty_and_changes_nothing_else() -> None:
    assert render_tasks(parse_tasks(TASKS), unchecked=True) == TASKS.replace("- [x]", "- [ ]")


@pytest.mark.parametrize(
    ("broken", "line"),
    [
        (TASKS.replace("- [ ] T003 Update", "- [ ] 3. Update"), 11),
        (TASKS.replace("  - verify: read the page", "  - owner: someone"), 12),
        (TASKS.replace("## 1. Passkey sign-in\n\n", ""), 3),
    ],
)
def test_a_task_file_off_the_grammar_is_refused_with_its_line(broken: str, line: int) -> None:
    with pytest.raises(GrammarError) as caught:
        parse_tasks(broken)
    assert caught.value.line == line


def test_a_second_files_or_verify_line_under_one_task_is_refused() -> None:
    """Found by review: a later line replaced an earlier one in silence, so a line slipped in above an approved one
    changed nothing an approval saw."""
    first = "  - verify: uv run pytest tests/test_passkey.py\n"
    with pytest.raises(GrammarError) as caught:
        parse_tasks(TASKS.replace(first, "  - verify: skip the tests\n" + first))
    assert caught.value.line == 8 and "verify" in caught.value.message
    with pytest.raises(GrammarError):
        parse_tasks(TASKS.replace("  - files: tests/test_passkey.py\n", "  - files: a.py\n  - files: b.py\n"))


def test_an_empty_files_or_verify_line_is_named_for_what_it_is() -> None:
    """Deferred by the review: `  - verify:` with nothing after it was refused with the message for a task line."""
    with pytest.raises(GrammarError) as caught:
        parse_tasks(TASKS.replace("  - verify: read the page", "  - verify:"))
    assert caught.value.line == 12 and "verify" in caught.value.message and "empty" in caught.value.message


def test_a_marker_is_found_whatever_its_case_and_spacing() -> None:
    """Deferred by the review: a lower-case marker, or one with a space before its colon, was not counted."""
    text = "[needs clarification] [NEEDS CLARIFICATION : which?] [Needs Clarification: x]"
    assert len(markers(text)) == 3


def test_a_briefs_assumptions_are_counted_by_sentence_its_open_points_aside() -> None:
    """Phase 15, found live: on gpt-4.1 a standard brief assumed where it might have asked, and the owner chose to
    have propose say how many assumptions to check."""
    from adk_spec.domain.brief_md import assumption_count

    assert assumption_count("Only fetch_orders changes. Retries are on a timeout alone!\n\nNo logging is added.") == 3
    assert assumption_count("Browsers support WebAuthn.\n\n[NEEDS CLARIFICATION: Which browsers are in scope?]") == 1
    assert assumption_count("") == 0


def test_a_task_whose_description_opens_with_a_bracket_reads_back_as_written() -> None:
    """Found by the fourth audit: `[Setup] create the module`, on a task that names no requirement, read back with
    `Setup` as its requirement, so the tasks gate sent it back three times and `plan` gave up."""
    from adk_spec.domain.model import Task, TaskGroup

    for parallel in (False, True):
        task = Task(id="T001", done=False, parallel=parallel, requirements=(), description="[Setup] create it")
        groups = (TaskGroup(title="Setup", tasks=(task,)),)
        assert parse_tasks(render_tasks(groups)) == groups
