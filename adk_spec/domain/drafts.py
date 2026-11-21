"""What a model answers in: the schemas a stage's agent is bound to.

Written for the strictest arm. Each is a plain `BaseModel`: Gemini's `response_schema` refuses the
`additionalProperties` that `extra="forbid"` adds. Every field is required and described, since the Copilot arm's
strict mode lists every property as required and both arms read the descriptions.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Triage(BaseModel):
    """How much ceremony a change request needs, and which capabilities it touches."""

    tier: Literal["none", "lean", "standard", "strict"] = Field(description="The smallest tier that fits the request.")
    capabilities: list[str] = Field(description="Kebab-case capability slugs the request touches. Empty for tier none.")
    reason: str = Field(description="One sentence: why this tier.")
