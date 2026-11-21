"""The graphs, built where a command asks for one and never at import.

A command is one short `Workflow` run. `NAME` is the app's and the root node's, the package folder's own name, as
ADK's loader expects of a root agent.
"""

from __future__ import annotations

from google.adk.apps.app import App
from google.adk.workflow import Workflow

from .stages.triage import build_triage

NAME = "adk_spec"


def build_smoke_app() -> App:
    """The triage stage alone: what `adk-spec smoke` runs to prove an arm answers in a schema."""
    return App(name=NAME, root_agent=Workflow(name=NAME, edges=[("START", build_triage())]), plugins=[])
