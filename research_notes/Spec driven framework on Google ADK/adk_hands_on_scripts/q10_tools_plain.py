"""Tool functions defined in a module WITHOUT `from __future__ import annotations`
(Python 3.14 evaluates annotations lazily by default, PEP 649/749)."""
import enum
from typing import Literal, Optional

from pydantic import BaseModel, Field

from google.adk.tools import ToolContext


class Priority(enum.Enum):
    LOW = "low"
    HIGH = "high"


class TaskSpec(BaseModel):
    """A task to add to the plan."""
    title: str = Field(description="Short task title")
    estimate_hours: float | None = None
    labels: list[str] = []


def save_spec(
    filename: str,
    markdown: str,
    tags: list[str],
    reviewer: str | None,
    task: TaskSpec,
    tool_context: ToolContext,
    section: Optional[str] = None,
    priority: Priority = Priority.LOW,
    mode: Literal["draft", "final"] = "draft",
    max_versions: int = 5,
) -> dict:
    """Saves a spec as markdown.

    Args:
      filename: Name of the spec file, for example "spec.md".
      markdown: The markdown body.
      tags: Free-form labels.
      reviewer: Reviewer login, or null when unassigned.
      task: The task this spec belongs to.
      section: Optional section heading.
      priority: Priority of the spec.
      mode: Whether this is a draft or the final version.
      max_versions: How many versions to keep.

    Returns:
      dict with "status" and "received" (what the function actually got).
    """
    return {
        "status": "success",
        "received": {
            "task_type": type(task).__name__, "task": task.model_dump(),
            "tags_type": type(tags).__name__, "reviewer": reviewer,
            "priority_type": type(priority).__name__, "priority": str(priority),
            "has_tool_context": tool_context is not None, "mode": mode, "section": section,
        },
    }


async def list_tasks(spec_ids: list[str], include_done: bool = False) -> list[TaskSpec]:
    """Lists tasks for the given specs."""
    return [TaskSpec(title=f"task for {s}") for s in spec_ids]
