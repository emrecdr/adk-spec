"""The structural validator: each rule of its table fires on its fault, with the table's severity, and on no other."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from samples import BRIEF, DELTA, SPEC, TASKS

from adk_spec.domain.brief_md import parse_brief
from adk_spec.domain.delta_md import parse_delta
from adk_spec.domain.model import Change, ChangeState, Finding, Spec
from adk_spec.domain.spec_md import fingerprint, parse_spec
from adk_spec.domain.tasks_md import parse_tasks
from adk_spec.domain.validate import SEVERITY, failed, validate_change, validate_spec

BASES = {r.id: fingerprint(r) for r in parse_spec(SPEC).requirements}
SCENARIO_ONE = (
    "#### Scenario: Valid credentials\n\n- WHEN the user submits a valid email and password\n"
    "- THEN the system starts a session\n\n"
)
ADDED_BLOCK = DELTA.split("## ADDED Requirements\n\n")[1].split("\n## MODIFIED")[0]
SEARCH = "# Delta: search\n\n## ADDED Requirements\n\n" + ADDED_BLOCK.replace("AUTH", "SEARCH")


def valid() -> tuple[Change, dict[str, Spec]]:
    living = {"auth": parse_spec(SPEC)}
    state = ChangeState(id="passkeys", tier="lean", bases=BASES)
    change = Change(
        state=state,
        brief=parse_brief(BRIEF),
        brief_raw=BRIEF,
        deltas={"auth": parse_delta(DELTA)},
        tasks=parse_tasks(TASKS),
    )
    return change, living


def _change(
    *,
    brief: str = BRIEF,
    delta: str = DELTA,
    tasks: str = TASKS,
    bases: dict[str, str] | None = None,
    skip_specs: bool = False,
    drop: tuple[str, ...] = (),
) -> list[Finding]:
    """The findings of the valid change with one of its files, its bases or a flag replaced, or a file dropped."""
    parsed = parse_delta(delta)
    state = ChangeState(id="passkeys", tier="lean", bases=BASES if bases is None else bases, skip_specs=skip_specs)
    change = Change(
        state=state,
        brief=None if "brief" in drop else parse_brief(brief),
        brief_raw=None if "brief" in drop else brief,
        deltas={} if "deltas" in drop else {parsed.capability: parsed},
        tasks=None if "tasks" in drop else parse_tasks(tasks),
    )
    return validate_change(change, {"auth": parse_spec(SPEC)})


def _spec(text: str) -> list[Finding]:
    return validate_spec(parse_spec(text))


def test_the_valid_change_and_the_valid_spec_have_no_findings() -> None:
    change, living = valid()
    assert validate_change(change, living) == [] and validate_spec(living["auth"]) == []


#: One case a code: the valid input changed in exactly the way the rule's row says.
CASES: dict[str, Callable[[], list[Finding]]] = {
    "spec.id-capability": lambda: _spec(SPEC.replace("REQ-AUTH-001", "REQ-BILLING-001")),
    "spec.id-duplicate": lambda: _spec(SPEC.replace("REQ-AUTH-002", "REQ-AUTH-001")),
    "spec.id-retired-reused": lambda: _spec(SPEC.replace("REQ-AUTH-002", "REQ-AUTH-003")),
    "spec.no-scenario": lambda: _spec(SPEC.replace(SCENARIO_ONE, "")),
    "spec.statement-empty": lambda: _spec(
        SPEC.replace("The system SHALL let a registered user sign in with email and password.\n\n", "")
    ),
    "spec.no-shall": lambda: _spec(SPEC.replace("The system SHALL let", "The system lets")),
    "spec.scenario-no-when-then": lambda: _spec(SPEC.replace("- THEN the system starts a session\n", "")),
    "spec.statement-long": lambda: _spec(SPEC.replace("email and password.", "email and password. " + "x" * 500)),
    "spec.purpose-empty": lambda: _spec(SPEC.replace("Sign-in and session handling.\n\n", "")),
    "delta.empty": lambda: _change(delta="# Delta: auth\n"),
    "delta.added-exists": lambda: _change(delta=DELTA.replace("REQ-AUTH-004", "REQ-AUTH-003")),
    "delta.target-missing": lambda: _change(delta=DELTA.replace("### REQ-AUTH-002", "### REQ-AUTH-009")),
    "delta.duplicate-op": lambda: _change(delta=DELTA.replace("REQ-AUTH-004", "REQ-AUTH-002")),
    "delta.purpose-missing": lambda: _change(delta=SEARCH),
    "delta.purpose-on-existing": lambda: _change(
        delta=DELTA.replace("# Delta: auth\n", "# Delta: auth\n\n## Purpose\n\nAnother purpose.\n")
    ),
    "delta.base-stale": lambda: _change(bases={**BASES, "REQ-AUTH-002": "sha256:" + "0" * 64}),
    "delta.base-missing": lambda: _change(bases={}),
    "delta.drops-scenario": lambda: _change(delta=DELTA.replace("Scenario: Too many failures", "Scenario: Third")),
    "delta.removed-no-reason": lambda: _change(
        delta=DELTA.replace("Reason: Passwords are retired in favour of passkeys.\n", "")
    ),
    "tasks.id-duplicate": lambda: _change(tasks=TASKS.replace("T002", "T001")),
    "tasks.bad-requirement-id": lambda: _change(tasks=TASKS.replace("[REQ-AUTH-004] Write", "[FR-004] Write")),
    "tasks.no-verify": lambda: _change(tasks=TASKS.replace("  - verify: read the page\n", "")),
    "brief.section-empty": lambda: _change(
        brief=BRIEF.replace("Passwords are the top source of account takeovers.\n\n", "")
    ),
    "brief.capability-bad-slug": lambda: _change(brief=BRIEF.replace("- auth", "- Auth Service")),
    "brief.markers-over-budget": lambda: _change(brief=BRIEF + "[NEEDS CLARIFICATION] " * 4 + "\n"),
    "brief.marker-unresolved": lambda: _change(brief=BRIEF + "[NEEDS CLARIFICATION: which browsers?]\n"),
    "change.missing-brief": lambda: _change(drop=("brief",)),
    "change.no-deltas": lambda: _change(drop=("deltas",)),
    "change.missing-tasks": lambda: _change(drop=("tasks",)),
}


@pytest.mark.parametrize("code", sorted(CASES))
def test_each_rule_fires_on_its_fault_with_its_severity(code: str) -> None:
    found = [f for f in CASES[code]() if f.code == code]
    assert found and all(f.severity == SEVERITY[code] for f in found), code
    assert all(len(f.message) > 20 for f in found), "a message says what is wrong and what to change"


def test_every_code_has_a_case_and_a_severity() -> None:
    assert set(CASES) == set(SEVERITY) - {
        "syntax",
        "spec.folder-mismatch",
        "spec.folder-bad-name",
        "delta.living-unreadable",
    }


@pytest.mark.parametrize(
    ("code", "alone"),
    [("spec.no-shall", True), ("delta.base-stale", True), ("tasks.no-verify", True), ("brief.marker-unresolved", True)],
)
def test_one_fault_raises_its_own_rule_and_no_other(code: str, alone: bool) -> None:
    assert ({f.code for f in CASES[code]()} == {code}) is alone


def test_a_changes_findings_name_the_file_they_are_about() -> None:
    assert {f.path for f in _change(bases={})} == {"specs/auth/spec.md"}
    assert {f.path for f in CASES["tasks.no-verify"]()} == {"tasks.md"}
    assert {f.path for f in CASES["brief.marker-unresolved"]()} == {"brief.md"}


def test_a_change_that_says_it_changes_no_spec_needs_no_delta() -> None:
    assert _change(drop=("deltas",), skip_specs=True) == []


def test_warnings_fail_only_under_strict() -> None:
    warning = Finding(severity="WARNING", code="spec.no-shall", message="m")
    assert failed([warning]) is False and failed([warning], strict=True) is True
    assert failed([Finding(severity="ERROR", code="spec.no-scenario", message="m")]) is True
    assert failed([]) is False


def test_a_task_list_that_holds_no_task_is_no_plan() -> None:
    """Found by review: a tasks.md holding its title alone met the gate that asks for a plan."""
    assert "change.missing-tasks" in {f.code for f in _change(tasks="# Tasks\n")}
    assert "change.missing-tasks" in {f.code for f in _change(tasks="# Tasks\n\n## 1. Nothing yet\n")}


def test_a_requirement_with_no_statement_is_an_error_and_not_also_a_missing_obligation() -> None:
    """Deferred by the review: a requirement holding a header and scenarios alone was only a warning."""
    found = CASES["spec.statement-empty"]()
    assert [(f.code, f.severity) for f in found] == [("spec.statement-empty", "ERROR")]
