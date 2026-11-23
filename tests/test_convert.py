"""A model's drafts turned into the domain's types: IDs and task numbers are Python's, and what is converted is
what the canonical file holds."""

from __future__ import annotations

from typing import Any

import pytest
from conftest import BRIEF_WITH_A_MARKER, OPEN_POINT
from samples import SPEC

from adk_spec.domain import drafts
from adk_spec.domain.brief_md import asked_in, markers, parse_brief, render_brief
from adk_spec.domain.convert import kept_ids, questions_of, render_design, slug_of, to_brief, to_deltas, to_tasks
from adk_spec.domain.delta_md import parse_delta, render_delta
from adk_spec.domain.drafts import (
    BriefDraft,
    DeltaDraft,
    DeltasDraft,
    DesignDraft,
    ModifiedDraft,
    RemovedDraft,
    RequirementDraft,
    ScenarioDraft,
    TaskDraft,
    TaskGroupDraft,
    TasksDraft,
)
from adk_spec.domain.ids import slug_problem
from adk_spec.domain.lifecycle import capture_bases
from adk_spec.domain.model import Removal
from adk_spec.domain.spec_md import parse_spec
from adk_spec.domain.tasks_md import parse_tasks, render_tasks
from adk_spec.domain.validate import validate_brief, validate_delta

ADD = RequirementDraft(
    name="Sign in with a passkey",
    statement="The system SHALL let a user sign in with a passkey.",
    scenarios=[
        ScenarioDraft(
            name="Registered passkey",
            steps=["when the user presents a passkey", "- **THEN** the system starts a session"],
        )
    ],
)
LIVING = {"auth": parse_spec(SPEC)}


def one(capability: str = "auth", purpose: str = "", **ops: Any) -> DeltasDraft:
    held = {"added": [], "modified": [], "removed": [], **ops}
    return DeltasDraft(deltas=[DeltaDraft(capability=capability, purpose=purpose, **held)])


def test_an_added_requirement_is_given_the_next_free_id_and_each_one_counts() -> None:
    taken = {"REQ-AUTH-001", "REQ-AUTH-002", "REQ-AUTH-003", "REQ-AUTH-007"}
    delta = to_deltas(one(added=[ADD, ADD]), LIVING, taken)["auth"]
    assert [r.id for r in delta.added] == ["REQ-AUTH-008", "REQ-AUTH-009"]
    assert delta.added[0].scenarios[0].steps == ("WHEN the user presents a passkey", "THEN the system starts a session")


def test_a_kept_id_is_given_once_and_a_second_requirement_of_its_name_gets_its_own() -> None:
    """A revision keeps a requirement's ID by its name: once, so two of one name are never given one ID."""
    kept = {("auth", "sign in with a passkey"): ["REQ-AUTH-004"]}
    delta = to_deltas(one(added=[ADD, ADD]), LIVING, {"REQ-AUTH-004"}, kept)["auth"]
    assert [r.id for r in delta.added] == ["REQ-AUTH-004", "REQ-AUTH-005"]


def test_two_requirements_of_one_name_keep_their_ids_in_order() -> None:
    """Found by the review: the second ID of a name overwrote the first, and both requirements moved."""
    kept = kept_ids(to_deltas(one(added=[ADD, ADD]), LIVING, {"REQ-AUTH-003"}))
    delta = to_deltas(one(added=[ADD, ADD]), LIVING, {"REQ-AUTH-004", "REQ-AUTH-005"}, kept)["auth"]
    assert [r.id for r in delta.added] == ["REQ-AUTH-004", "REQ-AUTH-005"]


def test_a_requirement_the_change_adds_given_back_as_modified_stays_added_with_its_id() -> None:
    """Found by the review: a revision shows the model the change's own IDs, and it may restate one as modified."""
    kept = {("auth", "sign in with a passkey"): ["REQ-AUTH-004"]}
    restated = one(modified=[{"id": "REQ-AUTH-004", "requirement": ADD}], removed=[])
    delta = to_deltas(restated, LIVING, {"REQ-AUTH-004"}, kept)["auth"]
    assert [r.id for r in delta.added] == ["REQ-AUTH-004"] and delta.modified == ()
    dropped = to_deltas(one(removed=[{"id": "REQ-AUTH-004", "reason": "Not wanted."}]), LIVING, {"REQ-AUTH-004"}, kept)
    assert dropped["auth"].removed == () and dropped["auth"].added == ()


def test_a_modified_draft_keeps_its_id_and_a_removed_one_takes_the_living_name() -> None:
    draft = one(
        modified=[ModifiedDraft(id="REQ-AUTH-002", requirement=ADD)],
        removed=[RemovedDraft(id="REQ-AUTH-001", reason="Retired.")],
    )
    delta = to_deltas(draft, LIVING, set())["auth"]
    assert (delta.modified[0].id, delta.modified[0].name) == ("REQ-AUTH-002", "Sign in with a passkey")
    assert delta.removed == (Removal(id="REQ-AUTH-001", name="Sign in with email", reason="Retired."),)
    bases = capture_bases({"auth": delta}, LIVING)
    assert [f.code for f in validate_delta(delta, LIVING["auth"], bases) if f.severity == "ERROR"] == []


def test_a_purpose_is_kept_for_a_new_capability_alone() -> None:
    assert to_deltas(one(purpose="Another purpose.", added=[ADD]), LIVING, set())["auth"].purpose is None
    assert to_deltas(one("search", "Find things.", added=[ADD]), LIVING, set())["search"].purpose == "Find things."


def test_two_drafts_for_one_capability_are_joined() -> None:
    twice = DeltasDraft(
        deltas=[*one(added=[ADD]).deltas, *one(removed=[RemovedDraft(id="REQ-AUTH-001", reason="x")]).deltas]
    )
    deltas = to_deltas(twice, LIVING, {"REQ-AUTH-003"})
    assert list(deltas) == ["auth"] and len(deltas["auth"].added) == 1 and len(deltas["auth"].removed) == 1


def test_what_a_converted_draft_renders_parses_back_to_itself() -> None:
    delta = to_deltas(one("search", "Find things.", added=[ADD]), {}, set())["search"]
    assert parse_delta(render_delta(delta)) == delta and delta.added[0].id == "REQ-SEARCH-001"


def test_a_brief_draft_becomes_a_brief_the_validator_passes() -> None:
    draft = BriefDraft(
        title=" Sign in with a passkey ",
        why="Passwords are phished.",
        what_changes="Users can sign in with a passkey.",
        non_goals="",
        capabilities=["auth"],
        impact="The sign-in page.",
        assumptions="",
        open_points=[],
        design_needed=False,
        design_reason="",
    )
    brief = to_brief(draft)
    assert brief.title == "Sign in with a passkey" and brief.capabilities == ("auth",)
    assert validate_brief(brief, "") == []


def test_tasks_are_numbered_in_order_across_groups() -> None:
    task = TaskDraft(
        description="Write the test",
        requirements=["REQ-AUTH-004"],
        files=["tests/t.py"],
        verify="run it",
        parallel=False,
    )
    draft = TasksDraft(
        groups=[TaskGroupDraft(title="1. A", tasks=[task, task]), TaskGroupDraft(title="2. B", tasks=[task])]
    )
    groups = to_tasks(draft)
    assert [t.id for g in groups for t in g.tasks] == ["T001", "T002", "T003"]
    assert parse_tasks(render_tasks(groups)) == groups and not any(t.done for g in groups for t in g.tasks)


def test_a_design_draft_renders_its_four_sections() -> None:
    text = render_design(DesignDraft(context="c", goals="g", decisions="d", risks="r"))
    assert text == "# Design\n\n## Context\n\nc\n\n## Goals\n\ng\n\n## Decisions\n\nd\n\n## Risks\n\nr\n"


@pytest.mark.parametrize(
    ("title", "held", "slug"),
    [
        ("Sign in with a passkey", [], "sign-in-with-a-passkey"),
        ("Sign in with a passkey", ["sign-in-with-a-passkey"], "sign-in-with-a-passkey-2"),
        ("Sign in", ["sign-in", "sign-in-2"], "sign-in-3"),
        ("  R" + chr(0xE9) + "duire les d" + chr(0xE9) + "lais!! ", [], "r-duire-les-d-lais"),
        ("???", [], "change"),
        ("2 factor", [], "change-2-factor"),
        ("con", [], "con-change"),
        ("word " * 20, [], "word-word-word-word-word-word-word-word"),
    ],
)
def test_a_title_becomes_a_slug_no_other_change_holds(title: str, held: list[str], slug: str) -> None:
    assert slug_of(title, held) == slug and slug_problem(slug) is None


def _objects(schema: Any) -> list[dict]:
    """Every object node of a JSON schema, at any depth."""
    if isinstance(schema, list):
        return [found for item in schema for found in _objects(item)]
    if not isinstance(schema, dict):
        return []
    here = [schema] if schema.get("type") == "object" else []
    return here + [found for held in schema.values() for found in _objects(held)]


DRAFTS = ("Triage", "BriefDraft", "DeltasDraft", "TasksDraft", "DesignDraft", "ScoutDraft", "SurveyDraft")


@pytest.mark.parametrize("name", DRAFTS)
def test_each_arm_is_sent_each_draft_schema_whole_and_strict(name: str) -> None:
    """ADK's own converters, private on purpose. Copilot's strict mode needs every property required at every
    level; Gemini's `response_schema` has refused `additionalProperties`."""
    from google.adk.models.lite_llm import _to_litellm_response_format
    from google.genai import Client, _transformers

    schema = getattr(drafts, name)
    copilot = _to_litellm_response_format(schema, "github_copilot/claude-sonnet-5.5")["json_schema"]
    assert copilot["strict"] is True
    for node in _objects(copilot["schema"]):
        assert sorted(node["required"]) == sorted(node["properties"]) and node["additionalProperties"] is False, node
    gemini = _transformers.t_schema(Client(api_key="offline")._api_client, schema)
    assert "additionalProperties" not in str(gemini.model_dump(exclude_none=True, by_alias=True, mode="json"))


@pytest.mark.parametrize("name", DRAFTS)
def test_every_field_of_a_draft_is_required_and_described(name: str) -> None:
    for model in [
        getattr(drafts, name),
        *[getattr(drafts, n) for n in dir(drafts) if n.endswith("Draft") or n == "Question"],
    ]:
        for field, held in model.model_fields.items():
            assert held.is_required() and held.description, f"{model.__name__}.{field}"


def test_requirement_ids_given_in_one_string_are_split() -> None:
    """Found by review: `["REQ-A-001, REQ-A-002"]` failed its round trip three times."""
    task = TaskDraft(
        description="Do it",
        requirements=["REQ-AUTH-001, REQ-AUTH-002"],
        files=["a.py, b.py"],
        verify="run",
        parallel=False,
    )
    (group,) = to_tasks(TasksDraft(groups=[TaskGroupDraft(title="1. A", tasks=[task])]))
    assert group.tasks[0].requirements == ("REQ-AUTH-001", "REQ-AUTH-002") and group.tasks[0].files == ("a.py", "b.py")
    assert parse_tasks(render_tasks((group,))) == (group,)


def test_a_modified_requirement_the_model_copied_unchanged_is_left_out() -> None:
    """The first live run did this (`docs/confirmation/2026-11-propose.md`, finding 3): REQ-AUTH-002 stood under
    MODIFIED word for word as the living spec has it."""
    living = LIVING["auth"].requirements
    changed = {
        "name": living[0].name,
        "statement": "The system SHALL let a user sign in, whatever the case.",
        "scenarios": [{"name": "Valid", "steps": ["WHEN the user signs in", "THEN a session starts"]}],
    }
    copied = {
        "name": living[1].name,
        "statement": living[1].statement,
        "scenarios": [{"name": s.name, "steps": list(s.steps)} for s in living[1].scenarios],
    }
    draft = one(
        modified=[{"id": "REQ-AUTH-001", "requirement": changed}, {"id": "REQ-AUTH-002", "requirement": copied}]
    )
    assert [req.id for req in to_deltas(draft, LIVING, set())["auth"].modified] == ["REQ-AUTH-001"]


# A brief's open points: data in the draft, markers in the file, questions for the person.


def brief_draft(**changed: Any) -> BriefDraft:
    return BriefDraft.model_validate({**BRIEF_WITH_A_MARKER, **changed})


def test_an_open_point_is_a_marker_in_the_briefs_file_and_a_question_with_its_suggestion() -> None:
    draft = brief_draft()
    brief = to_brief(draft)
    assert (
        brief.assumptions
        == "Browsers in scope support WebAuthn.\n\n[NEEDS CLARIFICATION: Which browsers are in scope?]"
    )
    text = render_brief(brief)
    assert parse_brief(text) == brief and len(markers(text)) == 1
    assert questions_of(draft) == [OPEN_POINT]


def test_a_question_that_would_break_its_marker_is_kept_whole_on_one_line() -> None:
    awkward = {"question": f"Which [evergreen] browsers,\nand since{chr(27)} when?", "suggested": "All of\nthem"}
    draft = brief_draft(open_points=[awkward])
    brief = to_brief(draft)
    text = render_brief(brief)
    assert markers(text) == ["[NEEDS CLARIFICATION: Which (evergreen) browsers, and since when?]"]
    assert parse_brief(text) == brief, "the file still reads back as written"
    assert questions_of(draft) == [
        {"question": "Which (evergreen) browsers, and since when?", "suggested": "All of them"}
    ]


def test_a_marker_written_in_a_section_is_asked_too_with_nothing_suggested() -> None:
    draft = brief_draft(assumptions="EU only. [NEEDS CLARIFICATION: which regions?]")
    asked = questions_of(draft)
    assert asked == [{"question": "which regions?", "suggested": ""}, OPEN_POINT], "in the order of the file"


def test_a_marker_with_no_question_is_still_put_to_the_person() -> None:
    draft = brief_draft(assumptions="Unsure. [NEEDS CLARIFICATION]", open_points=[])
    assert questions_of(draft) == [
        {"question": "The brief leaves a point open and names no question.", "suggested": ""}
    ]


def test_no_open_point_and_no_marker_is_no_question_and_an_empty_one_is_left_out() -> None:
    settled = brief_draft(open_points=[])
    assert questions_of(settled) == [] and to_brief(settled).assumptions == "Browsers in scope support WebAuthn."
    assert questions_of(brief_draft(open_points=[{"question": "   ", "suggested": "x"}])) == []
    only = brief_draft(assumptions="", open_points=[{"question": "Which regions?", "suggested": ""}])
    assert to_brief(only).assumptions == "[NEEDS CLARIFICATION: Which regions?]"


def test_an_open_point_the_model_also_wrote_as_a_marker_is_one_marker_and_one_question() -> None:
    """A new draft is shown the brief it replaces, markers and all: a model that copies a marker and names the point
    as well would otherwise ask the person the same thing twice."""
    copied = "Browsers in scope support WebAuthn.\n\n[NEEDS CLARIFICATION: Which browsers are in scope?]"
    draft = brief_draft(assumptions=copied)
    assert len(markers(render_brief(to_brief(draft)))) == 1
    assert questions_of(draft) == [OPEN_POINT]


def test_a_point_copied_as_a_marker_into_another_section_is_still_one_marker() -> None:
    """Found by the cleanup review: the guard read the assumptions alone, while the validator and the questions read
    the whole file, so a point named and also copied into another section stood twice and was counted twice."""
    copied = "Users sign in with a passkey. [NEEDS CLARIFICATION: Which browsers are in scope?]"
    draft = brief_draft(what_changes=copied)
    brief = to_brief(draft)
    assert len(markers(render_brief(brief))) == 1
    assert brief.assumptions == "Browsers in scope support WebAuthn.", "the point stands where the model wrote it"
    assert questions_of(draft) == [OPEN_POINT], "and keeps its suggestion"


def test_an_open_point_named_twice_is_asked_once_with_its_first_suggestion() -> None:
    twice = [{"question": "Which regions?", "suggested": "EU"}, {"question": " Which  regions? ", "suggested": "All"}]
    draft = brief_draft(open_points=twice)
    assert len(markers(render_brief(to_brief(draft)))) == 1
    assert questions_of(draft) == [{"question": "Which regions?", "suggested": "EU"}]


def test_a_hand_written_question_is_read_by_the_markers_own_grammar() -> None:
    """Found by the cleanup review: the question was read by a second parse of the marker, which disagreed with the
    pattern where a question ends in a bracket."""
    assert asked_in(
        "a [NEEDS CLARIFICATION: which of [a, b[] b [ needs  clarification :\n x ] c [NEEDS CLARIFICATION]"
    ) == [
        "which of [a, b[",
        "x",
        "",
    ]


@pytest.mark.parametrize(
    "written",
    [
        "We assume. [NEEDS CLARIFICATION: which provider",  # never closed
        "We assume. [NEEDS CLARIFICATION which provider]",  # no colon before its question
        "We assume. [NEEDS CLARIFICATIONS: which provider?]",  # not the marker's words
    ],
)
def test_a_marker_that_is_no_marker_is_an_error_and_not_a_point_silently_dropped(written: str) -> None:
    """Found by two reviews: such a line was counted as no marker at all, so the point it left open held no
    approval, or it ran on to the next `]` in the file and took what stood between into its question."""
    brief = to_brief(brief_draft(assumptions=written, open_points=[]))
    codes = [found.code for found in validate_brief(brief, render_brief(brief)) if found.severity == "ERROR"]
    assert codes == ["brief.marker-malformed"]


def test_a_well_formed_marker_is_not_called_malformed() -> None:
    brief = to_brief(brief_draft(assumptions="A. [ needs clarification : which of [a, b? ] B. [NEEDS CLARIFICATION]"))
    assert [found.code for found in validate_brief(brief, render_brief(brief))] == ["brief.marker-unresolved"] * 3


# Phase 15: open points asked in order of what they depend on, as the grilling skill asks a design tree.

SCOPE = {"question": "Which browsers are in scope?", "suggested": "The last two versions of each.", "depends_on": []}
FALLBACK = {"question": "What do other browsers get?", "suggested": "Passwords, as now.", "depends_on": [1]}


def test_a_round_asks_only_the_points_whose_prerequisites_are_settled() -> None:
    draft = brief_draft(open_points=[SCOPE, FALLBACK])  # the second waits on the first's answer
    assert [one["question"] for one in questions_of(draft)] == ["Which browsers are in scope?"]


def test_points_that_depend_on_each_other_in_a_loop_are_all_asked() -> None:
    one = {**SCOPE, "depends_on": [2]}
    draft = brief_draft(open_points=[one, FALLBACK])
    assert len(questions_of(draft)) == 2, "with nothing askable now, every point is asked rather than none"


def test_a_dependency_on_a_point_that_is_not_there_waits_on_nothing() -> None:
    draft = brief_draft(open_points=[{**SCOPE, "depends_on": [1, 7]}])
    assert [one["question"] for one in questions_of(draft)] == ["Which browsers are in scope?"]


def test_the_brief_lists_the_points_answerable_now_first() -> None:
    waiting = {**FALLBACK, "depends_on": [2]}
    draft = brief_draft(assumptions="", open_points=[waiting, SCOPE])
    assert markers(render_brief(to_brief(draft))) == [
        "[NEEDS CLARIFICATION: Which browsers are in scope?]",
        "[NEEDS CLARIFICATION: What do other browsers get?]",
    ]


def test_a_point_waiting_on_one_that_is_never_asked_waits_on_nothing() -> None:
    """Found by review: a dependency on a point with no question, which is never asked, held a point back for good."""
    nameless = {"question": "", "suggested": "", "depends_on": []}
    draft = brief_draft(open_points=[{**SCOPE, "depends_on": [2]}, nameless, FALLBACK | {"depends_on": []}])
    assert [one["question"] for one in questions_of(draft)] == [
        "Which browsers are in scope?",
        "What do other browsers get?",
    ]


def test_the_last_round_asks_every_point_still_open() -> None:
    """Found by review: a point that waited was never put to the person once the rounds ran out."""
    draft = brief_draft(open_points=[SCOPE, FALLBACK])
    assert len(questions_of(draft, every=True)) == 2
