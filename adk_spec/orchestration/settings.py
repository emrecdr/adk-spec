"""What the environment says of a run, read and nothing built: the arm, each role's model name, the fallback behind
it, and where Copilot's token is kept. Apart from `models.py`, which builds the models with ADK imported: the login
writes the token, and a command that calls no model should not pay the engine for one variable.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Each arm's model where none is named. Copilot's is the first that answered in a schema on the owner's seat
#: (`docs/confirmation/2026-11-smoke.md`); a seat's policy decides which models it is served, so `adk-spec models`
#: says what another seat may name. Gemini's is provisional: no live run has confirmed it.
DEFAULTS = {"copilot": "gpt-4.1", "gemini": "gemini-3.8-flash"}


def provider() -> str:
    """The arm `SPEC_PROVIDER` names, validated once for every function below. Blank or unset means Copilot."""
    arm = os.environ.get("SPEC_PROVIDER", "").strip().lower() or "copilot"
    if arm not in DEFAULTS:
        raise ValueError(f"SPEC_PROVIDER must be one of {sorted(DEFAULTS)}, not {arm!r}. Set it in .env or the shell")
    return arm


def model_pick(role: str = "") -> tuple[str, str]:
    """What names a role's model, and the model, the most specific choice first: the role's own `SPEC_<ROLE>_MODEL`,
    everyone's `SPEC_MODEL`, the arm's default."""
    arm = provider()
    own = f"SPEC_{role.upper().replace('-', '_')}_MODEL"
    if role and (name := os.environ.get(own, "").strip()):
        return own, name
    return "SPEC_MODEL", os.environ.get("SPEC_MODEL", "").strip() or DEFAULTS[arm]


def model_name(role: str = "") -> str:
    """The model a role runs on. The model is chosen per stage, so a role may run on a stricter or a cheaper one."""
    return model_pick(role)[1]


def fallback_name() -> str:
    """The model `SPEC_FALLBACK_MODEL` names, to stand behind every role's model; blank means none."""
    return os.environ.get("SPEC_FALLBACK_MODEL", "").strip()


def copilot_dir() -> Path:
    """LiteLLM's Copilot folder, where the login keeps its token and LiteLLM the API key it is issued. A blank value
    reads as unset."""
    return Path(os.environ.get("GITHUB_COPILOT_TOKEN_DIR") or "~/.config/litellm/github_copilot").expanduser()


def copilot_token() -> Path:
    """Where LiteLLM caches the Copilot device-flow token: one spelling, for readiness and the login."""
    return copilot_dir() / (os.environ.get("GITHUB_COPILOT_ACCESS_TOKEN_FILE") or "access-token")


def copilot_key() -> Path:
    """Where LiteLLM caches the API key it buys with the token: one spelling, for readiness and the login."""
    return copilot_dir() / (os.environ.get("GITHUB_COPILOT_API_KEY_FILE") or "api-key.json")


def quiet_litellm() -> None:
    """What LiteLLM is told before it is first imported: that it runs in production, so it reads no `.env`, and that
    it has its own model map, so it fetches no price list. `login` imports it too (the audit of 25 November, S8)."""
    os.environ.setdefault("LITELLM_MODE", "PRODUCTION")
    os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")  # the pinned version's own model map


def pin_copilot_dir() -> None:
    """The Copilot folder and its files written for LiteLLM, which reads them as written: `GITHUB_COPILOT_TOKEN_DIR`
    with its `~` expanded, and a blank file name dropped. LiteLLM would read `~/tokens` as a folder named `~` and
    start a device login of its own."""
    if "GITHUB_COPILOT_TOKEN_DIR" in os.environ:
        os.environ["GITHUB_COPILOT_TOKEN_DIR"] = str(copilot_dir())
    for name in ("GITHUB_COPILOT_ACCESS_TOKEN_FILE", "GITHUB_COPILOT_API_KEY_FILE"):
        if os.environ.get(name) == "":
            del os.environ[name]
