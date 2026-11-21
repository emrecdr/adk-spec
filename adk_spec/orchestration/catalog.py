"""What the chosen arm serves: the provider's own list of models, asked with the arm's own credentials.

A seat's plan and its organisation's policy decide which models answer, and a model the seat is not served fails
only when it is called. This asks first. It sends one read-only request and calls no model.

The shape of Copilot's answer is not something this code was written against a live reply for, so nothing is guessed:
the list under `data` is returned where there is one, the whole body otherwise, and only the keys an entry holds are
shown.
"""

from __future__ import annotations

from typing import Any

from .models import COPILOT_API, _litellm, said
from .settings import provider

#: The keys of an entry worth a column, where the entry holds them; a dot reaches into a nested object.
SHOWN = ("vendor", "model_picker_enabled", "policy.state", "capabilities.type")


class CatalogError(Exception):
    """The provider would not list its models: its own words."""


def list_models() -> list[dict[str, Any]]:
    """The models the chosen arm serves, one entry each. `CatalogError` where the provider will not list them."""
    try:
        return _gemini() if provider() == "gemini" else _copilot()
    except CatalogError:
        raise
    except Exception as exc:
        raise CatalogError(said(exc)) from exc


def _copilot() -> list[dict[str, Any]]:
    """Copilot's list, asked as LiteLLM asks for a chat: its key, its base and its headers."""
    _litellm()
    import httpx
    from litellm.llms.github_copilot.authenticator import Authenticator
    from litellm.llms.github_copilot.common_utils import get_copilot_default_headers

    auth = Authenticator()
    key = auth.get_api_key()
    base = (auth.get_api_base() or COPILOT_API).rstrip("/")
    with httpx.Client(timeout=30) as client:
        reply = client.get(f"{base}/models", headers=get_copilot_default_headers(key))
    try:
        body = reply.json()
    except ValueError:  # a page where JSON would be
        body = None
    if reply.status_code != 200:
        error = body.get("error") if isinstance(body, dict) else None
        why = error.get("message") if isinstance(error, dict) else None
        raise CatalogError(f"Copilot answered HTTP {reply.status_code}" + (f": {why}" if why else ""))
    data = body.get("data") if isinstance(body, dict) else None
    if isinstance(data, list):
        return [entry if isinstance(entry, dict) else {"id": str(entry)} for entry in data]
    return [body if isinstance(body, dict) else {"body": body}]


def _gemini() -> list[dict[str, Any]]:
    """Google's list, by google-genai, which reads a key or a project its own way."""
    from google import genai

    listed = genai.Client().models.list()
    return [{"id": (model.name or "").removeprefix("models/"), "display_name": model.display_name} for model in listed]


def _reached(entry: dict[str, Any], key: str) -> Any:
    held: Any = entry
    for part in key.split("."):
        held = held.get(part) if isinstance(held, dict) else None
    return held


def shown(models: list[dict[str, Any]]) -> list[str]:
    """One line a model: its id, then each of `SHOWN` the entry holds. An entry with no id shows its keys."""
    lines = []
    for entry in models:
        if "id" not in entry:
            lines.append(f"(no id)  keys={', '.join(sorted(entry))}")
            continue
        columns = [f"{key}={held}" for key in SHOWN if (held := _reached(entry, key)) is not None]
        lines.append("  ".join([str(entry["id"]), *columns]))
    return lines
