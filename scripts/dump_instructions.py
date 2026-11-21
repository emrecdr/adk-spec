"""Every stage's instruction as it is built, the per-process boundary replaced by a fixed word.

`uv run python scripts/dump_instructions.py > before.txt`, change the code, run it again and compare the two: a
refactor of `stages/` must leave every instruction byte for byte what it was, and a change to one stage's wording
must show in that stage alone. It builds the agents on the suite's fake model. Nothing is run and nothing is sent.
"""

from __future__ import annotations

import importlib
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    os.environ.update(SPEC_PROVIDER="gemini", SPEC_MODEL="fake", GOOGLE_API_KEY="offline")
    os.environ["GITHUB_COPILOT_TOKEN_DIR"] = tempfile.mkdtemp()  # an empty folder: no token of the person's is read
    sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
    importlib.import_module("conftest")  # the suite's own: it registers the fake model

    from adk_spec.orchestration import stages
    from adk_spec.orchestration.stages import brief, check, deltas, design, tasks, triage, verify

    built = {
        "triage": triage.build_triage(),
        "brief": brief.build_brief(),
        "deltas": deltas.build_deltas(),
        "design": design.build_design(),
        "tasks": tasks.build_tasks(),
        "check": check.build_check(),
        "verify": verify.build_verify(),
    }
    for name, agent in built.items():
        print(f"##### {name}")
        print(str(agent.instruction).replace(stages.BOUNDARY, "BOUNDARY"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
