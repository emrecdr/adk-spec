"""The structural validator: what code can say of a spec, a delta, a task list and a brief without judging them.

Every rule has one code and one severity, in `SEVERITY`. An ERROR stops work. A WARNING shows, and stops work only
under `--strict`. Whether a requirement is clear, or covered by a task, is not decided here: that is the model's
`check` stage until a measurement moves it.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence

from .brief_md import MARKER_BUDGET, markers
from .ids import REQ_ID, capability_of, slug_problem
from .model import Brief, Change, Delta, Finding, Requirement, Severity, Spec, TaskGroup
from .spec_md import fingerprint

#: Every rule's severity. The owner's to set: which faults stop work, and which only show.
SEVERITY: dict[str, Severity] = {
    "syntax": "ERROR",
    "spec.folder-mismatch": "ERROR",
    "spec.folder-bad-name": "ERROR",
    "spec.id-capability": "ERROR",
    "spec.id-duplicate": "ERROR",
    "spec.id-retired-reused": "ERROR",
    "spec.no-scenario": "ERROR",
    "spec.no-shall": "WARNING",
    "spec.scenario-no-when-then": "WARNING",
    "spec.statement-long": "WARNING",
    "spec.purpose-empty": "WARNING",
    "delta.living-unreadable": "ERROR",
    "delta.empty": "ERROR",
    "delta.added-exists": "ERROR",
    "delta.target-missing": "ERROR",
    "delta.duplicate-op": "ERROR",
    "delta.purpose-missing": "ERROR",
    "delta.purpose-on-existing": "ERROR",
    "delta.base-stale": "ERROR",
    "delta.base-missing": "WARNING",
    "delta.drops-scenario": "WARNING",
    "delta.removed-no-reason": "WARNING",
    "tasks.id-duplicate": "ERROR",
    "tasks.bad-requirement-id": "ERROR",
    "tasks.no-verify": "WARNING",
    "brief.section-empty": "ERROR",
    "brief.capability-bad-slug": "ERROR",
    "brief.markers-over-budget": "ERROR",
    "brief.marker-unresolved": "WARNING",
    "change.missing-brief": "ERROR",
    "change.no-deltas": "ERROR",
    "change.missing-tasks": "WARNING",
}
STATEMENT_MAX = 500
_OBLIGES = re.compile(r"\b(SHALL|MUST)\b")


def finding(code: str, message: str, *, path: str | None = None, line: int | None = None) -> Finding:
    """A finding of `code`, at the severity the table gives it."""
    return Finding(severity=SEVERITY[code], code=code, message=message, path=path, line=line)


def failed(findings: Iterable[Finding], *, strict: bool = False) -> bool:
    """Whether `findings` stop work: any ERROR, and under `strict` any WARNING too."""
    stops = {"ERROR", "WARNING"} if strict else {"ERROR"}
    return any(found.severity in stops for found in findings)


def _of_requirement(req: Requirement, capability: str) -> list[Finding]:
    """What one requirement block shows, in a spec or in a delta."""
    found = []
    if capability_of(req.id) != capability:
        found.append(
            finding(
                "spec.id-capability",
                f"{req.id} does not carry the capability `{capability}`. Name it REQ-{capability.upper()}-<NNN>.",
            )
        )
    if not req.scenarios:
        found.append(finding("spec.no-scenario", f"{req.id} has no scenario. Add one `#### Scenario:` at least."))
    if not _OBLIGES.search(req.statement):
        found.append(finding("spec.no-shall", f"{req.id} states no obligation. Write it with SHALL or MUST."))
    if len(req.statement) > STATEMENT_MAX:
        found.append(
            finding(
                "spec.statement-long",
                f"{req.id}'s statement is longer than {STATEMENT_MAX} characters. Split it, or move detail to a "
                "scenario.",
            )
        )
    for scenario in req.scenarios:
        words = {step.split(" ", 1)[0] for step in scenario.steps}
        if not {"WHEN", "THEN"} <= words:
            found.append(
                finding(
                    "spec.scenario-no-when-then",
                    f"{req.id}'s scenario `{scenario.name}` lacks a WHEN step or a THEN step. Give it both.",
                )
            )
    return found


def validate_spec(spec: Spec) -> list[Finding]:
    """What a living spec shows."""
    found = []
    if not spec.purpose:
        found.append(finding("spec.purpose-empty", f"The spec of `{spec.capability}` has no purpose. Write one."))
    retired = {gone.id for gone in spec.retired}
    for req_id, times in Counter(req.id for req in spec.requirements).items():
        if times > 1:
            found.append(
                finding("spec.id-duplicate", f"{req_id} names {times} requirements. Give each its own number.")
            )
    for req in spec.requirements:
        found += _of_requirement(req, spec.capability)
        if req.id in retired:
            found.append(
                finding(
                    "spec.id-retired-reused",
                    f"{req.id} is listed as retired, and a number is never used twice. Give the requirement a new one.",
                )
            )
    return found


def validate_delta(delta: Delta, living: Spec | None, bases: Mapping[str, str]) -> list[Finding]:
    """What a delta shows against the living spec it changes, `None` where the change creates the capability, and
    against the fingerprints recorded when it was based."""
    found = []
    targets = [*delta.modified, *delta.removed]
    if not delta.added and not targets:
        found.append(
            finding(
                "delta.empty",
                f"The delta of `{delta.capability}` holds no operation. Add a requirement under ADDED, MODIFIED or "
                "REMOVED, or delete the file.",
            )
        )
    for req_id, times in Counter(held.id for held in (*delta.added, *targets)).items():
        if times > 1:
            found.append(
                finding("delta.duplicate-op", f"{req_id} stands under {times} operations. Keep it under one, once.")
            )
    for req in (*delta.added, *delta.modified):
        found += _of_requirement(req, delta.capability)
    held = {req.id: req for req in living.requirements} if living else {}
    taken = {*held, *(gone.id for gone in living.retired)} if living else set()
    found += _of_purpose(delta, living)
    found += [
        finding(
            "delta.added-exists",
            f"{req.id} is already in the spec of `{delta.capability}`, or retired there. Give the new requirement "
            "the next free number.",
        )
        for req in delta.added
        if req.id in taken
    ]
    for target in targets:
        found += _of_target(target.id, held, bases, delta.capability)
    found += [
        finding(
            "delta.drops-scenario",
            f"The modified {req.id} drops the scenario `{scenario.name}`. Keep it, or confirm it is meant to go.",
        )
        for req in delta.modified
        if req.id in held
        for scenario in held[req.id].scenarios
        if scenario.name not in {kept.name for kept in req.scenarios}
    ]
    found += [
        finding("delta.removed-no-reason", f"{gone.id} is removed with no reason. Add a `Reason:` line.")
        for gone in delta.removed
        if not gone.reason
    ]
    return found


def _of_purpose(delta: Delta, living: Spec | None) -> list[Finding]:
    """A delta carries a purpose where it creates its capability, and there alone."""
    if living is None and not delta.purpose:
        return [
            finding(
                "delta.purpose-missing",
                f"`{delta.capability}` is a new capability, and its delta has no purpose. Add a `## Purpose` section.",
            )
        ]
    if living is not None and delta.purpose is not None:
        return [
            finding(
                "delta.purpose-on-existing",
                f"`{delta.capability}` exists, and a delta does not change a purpose. Remove the `## Purpose` section.",
            )
        ]
    return []


def _of_target(
    req_id: str, held: Mapping[str, Requirement], bases: Mapping[str, str], capability: str
) -> list[Finding]:
    """What a modified or removed ID shows: it must be in the living spec, and unchanged there since it was based."""
    if req_id not in held:
        return [
            finding(
                "delta.target-missing",
                f"{req_id} is not in the living spec of `{capability}`. Change an ID the spec holds, or add it under "
                "ADDED.",
            )
        ]
    if req_id not in bases:
        return [
            finding(
                "delta.base-missing",
                f"No base is recorded for {req_id}. Run `adk-spec rebase` to record what the delta was written "
                "against.",
            )
        ]
    if bases[req_id] != fingerprint(held[req_id]):
        return [
            finding(
                "delta.base-stale",
                f"{req_id} changed in the living spec after this delta was based on it. Read the current "
                "requirement, update the delta, then run `adk-spec rebase`.",
            )
        ]
    return []


def validate_tasks(groups: Sequence[TaskGroup]) -> list[Finding]:
    """What a task list shows."""
    tasks = [task for group in groups for task in group.tasks]
    found = [
        finding("tasks.id-duplicate", f"{task_id} names {times} tasks. Give each its own number.")
        for task_id, times in Counter(task.id for task in tasks).items()
        if times > 1
    ]
    found += [
        finding(
            "tasks.bad-requirement-id",
            f"{task.id} names `{named}`, which is no requirement ID. Write it as REQ-<CAPABILITY>-<NNN>.",
        )
        for task in tasks
        for named in task.requirements
        if not REQ_ID.fullmatch(named)
    ]
    found += [
        finding("tasks.no-verify", f"{task.id} has no `verify` line. Say how its result is checked.")
        for task in tasks
        if task.verify is None
    ]
    return found


def validate_brief(brief: Brief, raw: str) -> list[Finding]:
    """What a brief shows. `raw` is its text, where the clarification markers are counted."""
    needed = {"Why": brief.why, "What changes": brief.what_changes, "Capabilities": brief.capabilities}
    found = [
        finding("brief.section-empty", f"The brief's `{name}` section is empty. Fill it in.")
        for name, held in needed.items()
        if not held
    ]
    found += [
        finding("brief.capability-bad-slug", f"The brief names a capability that cannot be one: {why}.")
        for capability in brief.capabilities
        if (why := slug_problem(capability))
    ]
    open_points = markers(raw)
    if len(open_points) > MARKER_BUDGET:
        found.append(
            finding(
                "brief.markers-over-budget",
                f"The brief holds {len(open_points)} clarification markers, past the {MARKER_BUDGET} it may. The "
                "request is not ready: settle some with its author first.",
            )
        )
    found += [
        finding("brief.marker-unresolved", f"The brief leaves a point open: {marker}. Settle it, then remove it.")
        for marker in open_points
    ]
    return found


def validate_change(change: Change, living: Mapping[str, Spec]) -> list[Finding]:
    """What a change shows, each finding with the file it is about, relative to the change's folder."""
    found: list[Finding] = []

    def about(path: str, findings: Iterable[Finding]) -> None:
        found.extend(held.model_copy(update={"path": path}) for held in findings)

    if change.brief is None:
        about("brief.md", [finding("change.missing-brief", "The change has no brief.md. Write its brief first.")])
    else:
        about("brief.md", validate_brief(change.brief, change.brief_raw or ""))
    if not change.deltas and not change.state.skip_specs:
        no_delta = "The change holds no delta. Add specs/<capability>/spec.md, or set skip_specs where no spec changes."
        about("specs", [finding("change.no-deltas", no_delta)])
    for capability, delta in sorted(change.deltas.items()):
        about(f"specs/{capability}/spec.md", validate_delta(delta, living.get(capability), change.state.bases))
    groups = change.tasks or ()
    if not any(group.tasks for group in groups):
        no_tasks = "The change has no task. Plan its tasks in tasks.md before approval."
        about("tasks.md", [finding("change.missing-tasks", no_tasks)])
    else:
        about("tasks.md", validate_tasks(groups))
    return found
