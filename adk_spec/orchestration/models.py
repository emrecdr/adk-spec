"""Which model, on which arm, and what a request to it looks like: a deadline and retries, on both arms.

The only file in the package that names a provider. GitHub Copilot is the arm when none is named; like everything
that is not Gemini it goes through LiteLLM. Gemini, which ADK speaks natively, is a plain model name. Both are the
same `LlmAgent` to the rest of the code; `SPEC_PROVIDER` is the one switch, read from the environment at each call.

No request carries a temperature: Copilot's GPT models refuse any value but 1, and no measurement yet gives a reason
to set one elsewhere.
"""

from __future__ import annotations

import asyncio
import functools
import importlib.util
import json
import logging
import os
import re
from collections.abc import AsyncGenerator
from typing import Any

import truststore
from google.adk.models import FallbackModel
from google.adk.models.base_llm import BaseLlm
from google.adk.models.google_llm import Gemini
from google.adk.models.registry import LLMRegistry
from google.adk.utils.env_utils import is_enterprise_mode_enabled
from google.auth.exceptions import GoogleAuthError
from google.genai import types

from .settings import copilot_token, fallback_name, model_name, model_pick, pin_copilot_dir, provider

#: The Copilot arm's provider, as LiteLLM names it.
COPILOT = "github_copilot"
#: Where Copilot's calls go where the cached key names no endpoint of its own.
COPILOT_API = "https://api.githubcopilot.com"
#: Attempts per model call on a transient failure: the original plus two.
RETRY_ATTEMPTS = 3
#: Seconds one model call may take, its retries included on the Copilot arm.
REQUEST_TIMEOUT_S = 180.0
#: Seconds one run may take, every stage of it.
RUN_DEADLINE_S = 600.0

#: A bearer token in a log line. LiteLLM's debug dump masks a request's headers but prints its body whole.
_BEARER = re.compile(r"(Bearer\s+)[^\s'\",}]+")


class _HideBearer(logging.Filter):
    """Every LiteLLM log line with its bearer token hidden."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg, record.args = _BEARER.sub(r"\1[REDACTED]", record.getMessage()), ()
        return True


#: What a fallback model moves a call on from: ADK's codes, and a timeout, which ADK leaves out.
_FALL_BACK_ON = FallbackModel.DEFAULT_STATUS_CODES | {408}


class CallTimeoutError(TimeoutError):
    """A call no answer came back to within `REQUEST_TIMEOUT_S`, the client's own retries included: a timeout, 408,
    which a fallback model moves on from."""

    status_code = 408


def serving(role: str = "") -> str:
    """What a run's model calls go to, for a report: the role's model and its arm."""
    return f"{model_name(role)} on {provider()}"


@functools.cache
def trust_the_system() -> None:
    """Certificates verified through the operating system's own store, as a browser does, once, where the first
    client is built: a company proxy re-signs HTTPS with a root the machine trusts and Python's bundled list does
    not. Not on import: a process that embeds adk-spec decides how its own connections are verified."""
    truststore.inject_into_ssl()


def build_model(*, role: str = "") -> BaseLlm:
    """The model for `SPEC_PROVIDER`, the class ADK names for it on Gemini and a LiteLLM model otherwise, each under
    one deadline for a call and every retry of it, and, when `SPEC_FALLBACK_MODEL` names another, ADK's
    `FallbackModel` over both. A fallback the role runs already is not asked again."""
    trust_the_system()
    primary = model_name(role)
    names = [primary] + ([fallback] if (fallback := fallback_name()) and fallback != primary else [])
    if provider() == "gemini":
        gemini = [bounded_over(LLMRegistry.resolve(name))(model=name) for name in names]
        return gemini[0] if len(gemini) == 1 else FallbackModel(models=gemini, retriable_status_codes=_FALL_BACK_ON)
    litellm = _litellm()
    litellm.suppress_debug_info = True  # else a red "Give Feedback" banner on stdout with every error
    # The instruction as Copilot's system turn. Run below LiteLLM: without this it is sent as an assistant turn, so
    # the fences and the reminder after them reach the model as words it had said itself.
    litellm.disable_copilot_system_to_assistant = True
    log = logging.getLogger("LiteLLM")
    if not any(isinstance(held, _HideBearer) for held in log.filters):
        log.addFilter(_HideBearer())
    # The attempts are the OpenAI SDK's own retries, `RETRY_ATTEMPTS` in all. LiteLLM's MCP gateway, which nothing
    # here uses, is skipped: on LiteLLM 1.106.x a chat call carrying a tool imported it, and it needs `mcp`.
    from google.adk.models.lite_llm import LiteLlm

    bounded = bounded_over(LiteLlm)
    models = [
        bounded(model=f"{COPILOT}/{name}", max_retries=RETRY_ATTEMPTS - 1, _skip_mcp_handler=True) for name in names
    ]
    return models[0] if len(models) == 1 else FallbackModel(models=models, retriable_status_codes=_FALL_BACK_ON)


@functools.cache
def bounded_over(base: type[BaseLlm]) -> type[BaseLlm]:
    """`base` under one deadline for a call and every retry its client makes of it, where each attempt had a deadline
    of its own: three on Gemini's client, nine minutes in all, found by an outside audit. Past it the call raises
    `CallTimeoutError`, a 408, which a fallback model moves on from."""

    class Bounded(base):  # pyrefly: ignore[invalid-inheritance]
        async def generate_content_async(self, llm_request: Any, stream: bool = False) -> AsyncGenerator[Any]:
            # The answer is gathered under the deadline and handed on after it: a deadline held across the yield
            # would count ADK's own time against an answer that came in time.
            asked = super().generate_content_async(llm_request, stream)
            try:
                async with asyncio.timeout(REQUEST_TIMEOUT_S):
                    answered = [response async for response in asked]
            except TimeoutError as exc:
                raise CallTimeoutError(f"no answer within {REQUEST_TIMEOUT_S:g} s, the retries included") from exc
            for response in answered:
                yield _ended_said(response)

    return Bounded


#: The finish reasons of an answer that ended as it should, or of one that says no reason.
_ENDED_WELL = frozenset({"STOP", "FINISH_REASON_UNSPECIFIED"})


def _ended_said(response: Any) -> Any:
    """An answer the provider ended early, at its output limit or for safety, given the reason as its error code: one
    rule for both arms. LiteLLM's sets the code itself; Gemini's says it by a finish reason alone wherever the answer
    holds text. Found by the third audit: Gemini's answer cut at its limit was taken for a schema fault, and asked for
    again twice."""
    reason = response.finish_reason
    named = getattr(reason, "value", reason)  # found by the code review: `str()` spells an enum `FinishReason.X`
    if response.error_code or response.partial or named is None or named in _ENDED_WELL:
        return response
    return response.model_copy(
        update={"error_code": str(named), "error_message": "the answer ended before it was whole"}
    )


def _litellm():  # unannotated: a checker then knows the module and its typed flags
    """LiteLLM, imported where the Copilot arm needs it and nowhere else. On its own import it reads `.env` unless
    told it runs in production, and fetches a price list unless `LITELLM_LOCAL_MODEL_COST_MAP` is set. It reads
    `GITHUB_COPILOT_TOKEN_DIR` as written, so it is handed the folder readiness and the login read."""
    quiet_litellm()
    pin_copilot_dir()
    trust_the_system()  # before LiteLLM's import, which keeps the certificate context it makes then
    import litellm

    return litellm


def quiet_litellm() -> None:
    """What LiteLLM is told before it is first imported: that it runs in production, so it reads no `.env`, and that
    it has its own model map, so it fetches no price list. `login` imports it too (the audit of 25 November, S8)."""
    os.environ.setdefault("LITELLM_MODE", "PRODUCTION")
    os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")  # the pinned version's own model map


def _has_mcp() -> bool:
    """Whether the `mcp` package can be imported, which the pinned LiteLLM needs on every Responses-API call."""
    return importlib.util.find_spec("mcp") is not None


def _gemini_retried() -> list[int]:
    """The statuses genai retries: a timeout and each 5xx, and a 429 only through Vertex AI, whose shared quota
    throws 429s a moment's wait passes. AI Studio's names a quota spent for a minute or a day."""
    return [408, *([429] if is_enterprise_mode_enabled() else []), 500, 502, 503, 504]


def request_config() -> types.GenerateContentConfig:
    """What every call carries, on both arms: a deadline, and on Gemini its retries, which Copilot's OpenAI SDK makes
    itself (`build_model`). No temperature and no thinking setting: the provider's own defaults."""
    gemini = provider() == "gemini"
    return types.GenerateContentConfig(
        http_options=types.HttpOptions(
            timeout=int(REQUEST_TIMEOUT_S * 1000),
            retry_options=types.HttpRetryOptions(
                attempts=RETRY_ATTEMPTS, initial_delay=1.0, http_status_codes=_gemini_retried()
            )
            if gemini
            else None,
        ),
    )


def require_ready(*, roles: tuple[str, ...] = (), names: bool = True) -> str | None:
    """Why the chosen arm cannot run, or None. Called by a command before anything is spent, never at import.
    `roles` names the stages the run will build, so a model no class serves is a sentence here, not a traceback.
    `names` off asks after the arm alone, its token or key: for a command that lists the models to choose from."""
    try:
        arm = provider()
    except ValueError as exc:
        return str(exc)
    named = [model_pick(role) for role in ("", *roles)] if names else []
    if names and (fallback := fallback_name()):
        named.append(("SPEC_FALLBACK_MODEL", fallback))
    if arm == "copilot":
        return _copilot_refused(named)
    return _gemini_refused() or _not_gemini(named)


def _copilot_refused(named: list[tuple[str, str]]) -> str | None:
    """Why the Copilot arm cannot run with the models `named`, each by the variable that names it, or None."""
    if not ((token := copilot_token()).is_file() and token.stat().st_size):  # an empty file is no token
        return (
            f"SPEC_PROVIDER=copilot needs a cached token at {token}. "
            "Run `adk-spec login` once: `uv run adk-spec login` in the checkout"
        )
    known = _litellm().model_cost
    for var, name in named:
        entry = known.get(f"{COPILOT}/{name}")
        if entry is None:
            return (
                f"{var}={name} is not in the model map of the pinned LiteLLM, so how to call it is unknown. "
                "Name a model the map holds"
            )
        # Run on the pinned pair: LiteLLM 1.106.2 imports its MCP gateway on every Responses call, before it reads
        # the flag that skips it, so each such call fails with "No module named 'mcp'".
        if entry.get("mode") == "responses" and not _has_mcp():
            return (
                f"{var}={name} is served on the Responses API, where the pinned LiteLLM needs the mcp package. "
                "Name a Claude model, or add mcp to the project"
            )
    return None


def _not_gemini(named: list[tuple[str, str]]) -> str | None:
    """Why a model `named` on the Gemini arm is one ADK would send elsewhere, or no class claims, or None."""
    for var, name in named:
        try:
            model = LLMRegistry.resolve(name)
        except ValueError as exc:
            first, _, _ = str(exc).partition("\n")
            why = f"{var}: {first.rstrip('.')}"
        except ImportError:  # a `class:name` prefix whose class needs a package this project does not install
            why = f"{var}={name} is no Gemini model"
        else:
            if issubclass(model, Gemini):
                continue
            # ADK resolves a name to the class that will serve it: `gpt-*` goes to OpenAI's own API.
            why = f"{var}={name} is no Gemini model: ADK sends it to {model.__name__}, another provider's class"
        return f"{why}. Name a Gemini model in {var}"
    return None


def _gemini_refused() -> str | None:
    """Why google-genai will not build the Gemini arm's client as ADK builds it for each call, or None. Asked of
    the SDK, which reads a key, a project, a region and Application Default Credentials its own way."""
    try:
        Gemini(model=model_name()).api_client.close()  # built for what building it refuses, and let go
    except (ValueError, GoogleAuthError) as exc:
        if not is_enterprise_mode_enabled():
            return (
                "SPEC_PROVIDER=gemini needs GOOGLE_API_KEY, set in the shell or in .env at the checkout's root, or "
                "Vertex AI and its project"
            )
        return (
            "SPEC_PROVIDER=gemini through Vertex AI finds no project: set GOOGLE_CLOUD_PROJECT, or sign in with "
            f"Application Default Credentials that name one (`gcloud auth application-default login`) ({exc})"
        )
    return None


#: LiteLLM's wrapping of a provider's error body: its own class again, then the provider's.
_WRAPPED = re.compile(r"(?:\w+Error: )?\w+Exception - (.*)", re.DOTALL)


def said(error: Exception) -> str:
    """A provider's error in its own words: genai's `.message`; LiteLLM's with the class it puts before them gone
    and the provider's body unwrapped, a JSON body read as its code and the sentence it holds."""
    message = str(getattr(error, "message", None) or error).removeprefix(f"litellm.{type(error).__name__}: ")
    wrapped = _WRAPPED.fullmatch(message)
    if wrapped is None:
        return message
    try:
        body = json.loads(wrapped[1])["error"]
    except ValueError, KeyError, TypeError:
        return wrapped[1]
    if not isinstance(body, dict) or not body.get("message"):
        return wrapped[1]
    kind = body.get("code") or body.get("type")
    return f"{kind}: {body['message']}" if kind else str(body["message"])
