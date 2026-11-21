"""A model's drafts turned into the domain's types: IDs and task numbers are Python's, and what is converted is
what the canonical file holds."""

from __future__ import annotations

from typing import Any

import pytest
from samples import SPEC

from adk_spec.domain import drafts
from adk_spec.domain.convert import render_design, slug_of, to_brief, to_deltas, to_tasks
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


DRAFTS = ("Triage", "BriefDraft", "QuestionsDraft", "DeltasDraft", "TasksDraft", "DesignDraft")


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
