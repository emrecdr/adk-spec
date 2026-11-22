"""Shared test plumbing: a fake model registered with ADK, and an environment no test inherits anything from.

The fake goes through ADK's own resolution path: `LLMRegistry` maps a model name to a class by regex, so registering
`FakeModel` for `fake.*` and setting `SPEC_MODEL=fake` on the Gemini arm makes the real `build_model()` hand its
agents the fake. Nothing in the package is patched: the real runner, workflow and agents all run. The fake answers
the canned answer the request's schema accepts, a sentence where there is no schema, and what a test told it for a
request whose instruction contains a text. Three canned answers are fitted to their request, since one that does
not fit would pass for work it did not do: a task list names the requirements the request's deltas add or modify
(`tasks_serving`), a scout names a file the request lists (`scout_naming`), and a survey quotes text the request
shows (`survey_quoting`).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
from collections.abc import AsyncGenerator, Iterator
from pathlib import Path

import pytest
from google.adk.models.google_llm import Gemini
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.models.registry import LLMRegistry
from google.genai import types
from pydantic import BaseModel, ValidationError

from adk_spec.domain.ids import REQ_ID

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "adk_spec"

CANNED_TRIAGE = {"tier": "lean", "capabilities": ["auth"], "reason": "one small change"}
#: A brief draft that converts to the sample `BRIEF`: no marker, and no design owed.
CANNED_BRIEF = {
    "title": "Sign in with a passkey",
    "why": "Passwords are the top source of account takeovers.",
    "what_changes": "Users can register a passkey and sign in with it.",
    "non_goals": "No change to session length.",
    "capabilities": ["auth"],
    "impact": "The sign-in page and the session service.",
    "assumptions": "Browsers in scope support WebAuthn.",
    "open_points": [],
    "design_needed": False,
    "design_reason": "One capability, and no new dependency.",
}
_PASSKEY = {
    "name": "Sign in with a passkey",
    "statement": "The system SHALL let a user sign in with a passkey.",
    "scenarios": [
        {
            "name": "Registered passkey",
            "steps": ["WHEN the user presents a registered passkey", "THEN the system starts a session"],
        }
    ],
}
#: A deltas draft that adds one requirement to `auth`.
CANNED_DELTAS = {"deltas": [{"capability": "auth", "purpose": "", "added": [_PASSKEY], "modified": [], "removed": []}]}
#: A deltas draft that modifies a requirement the living spec does not hold.
DELTAS_ON_A_MISSING_ID = {
    "deltas": [
        {
            "capability": "auth",
            "purpose": "",
            "added": [],
            "modified": [{"id": "REQ-AUTH-099", "requirement": _PASSKEY}],
            "removed": [],
        }
    ]
}
#: What a scout asks to see of the repository `repository()` makes by default, and what a survey states of it.
CANNED_SCOUT = {"files": ["src/app.py"], "folders": [], "searches": [], "reason": "Sign-in is decided there."}
CANNED_SURVEY = {
    "statements": [
        {"kind": "touches", "file": "src/app.py", "quote": "return password()", "note": "Sign-in is decided here."}
    ],
    "more_files": [],
    "more_folders": [],
    "more_searches": [],
}
#: The answers the fake gives by default, one a schema: the first one a request's schema accepts.
#: A brief draft that says a design is owed.
BRIEF_OWING_A_DESIGN = {**CANNED_BRIEF, "design_needed": True, "design_reason": "It adds a dependency."}
#: A brief draft that leaves one point open: its question, and the answer the brief stage would suggest.
OPEN_POINT = {"question": "Which browsers are in scope?", "suggested": "Evergreen browsers only"}
BRIEF_WITH_A_MARKER = {**CANNED_BRIEF, "open_points": [OPEN_POINT]}
CANNED_TASKS = {
    "groups": [
        {
            "title": "1. Passkey sign-in",
            "tasks": [
                {
                    "description": "Write the failing passkey sign-in test",
                    "requirements": ["REQ-AUTH-004"],
                    "files": ["tests/test_passkey.py"],
                    "verify": "uv run pytest tests/test_passkey.py",
                    "parallel": False,
                },
                {
                    "description": "Implement the passkey handler",
                    "requirements": ["REQ-AUTH-004", "REQ-AUTH-002"],
                    "files": ["src/auth/passkey.py"],
                    "verify": "uv run pytest tests/test_passkey.py",
                    "parallel": False,
                },
            ],
        }
    ]
}
CANNED_DESIGN = {
    "context": "Sign-in is one handler behind the session service.",
    "goals": "Passkeys beside passwords, with no change to sessions.",
    "decisions": "WebAuthn through the platform API, not a library: one less dependency.",
    "risks": "Older browsers lack WebAuthn: the password path stays.",
}
#: One finding of the check's, a warning that quotes the sample brief's last line.
CANNED_FINDINGS = {
    "findings": [
        {
            "kind": "ambiguity",
            "severity": "warning",
            "file": "brief.md",
            "quote": "Browsers in scope support WebAuthn.",
            "message": "Which browsers are in scope is not said.",
        }
    ]
}
#: A verdict for each requirement the sample delta touches, each quoting a line of `test_verify.py`'s diff: 004 is
#: added and 002 modified, so they quote added lines; 001 is removed, so it quotes a removed one.
CANNED_VERDICTS = {
    "verdicts": [
        {
            "id": "REQ-AUTH-004",
            "verdict": "met",
            "evidence": [{"path": "src/auth.py", "quote": "return passkey(user)"}],
            "reason": "Sign-in now goes through the passkey.",
        },
        {
            "id": "REQ-AUTH-002",
            "verdict": "met",
            "evidence": [{"path": "src/auth.py", "quote": "return account.failures >= 3"}],
            "reason": "The lock now falls at three failures.",
        },
        {
            "id": "REQ-AUTH-001",
            "verdict": "met",
            "evidence": [{"path": "src/auth.py", "quote": "return password(user)"}],
            "reason": "The password path is gone.",
        },
    ]
}
#: A review that disputes nothing, finds nothing unknown and asks for nothing more.
CANNED_REVIEW = {"disputed": [], "unknown": [], "more_files": [], "more_folders": [], "more_searches": []}
CANNED: tuple[dict, ...] = (
    CANNED_TRIAGE,
    CANNED_BRIEF,
    CANNED_DELTAS,
    CANNED_TASKS,
    CANNED_DESIGN,
    CANNED_FINDINGS,
    CANNED_VERDICTS,
    CANNED_SCOUT,
    CANNED_SURVEY,
    CANNED_REVIEW,
)


def canned_for(schema: type[BaseModel]) -> dict:
    """The canned answer `schema` accepts: the fake answers as the schema requires, whichever schema it is."""
    for payload in CANNED:
        try:
            schema.model_validate(payload)
        except ValidationError:
            continue
        return payload
    raise AssertionError(f"no canned answer fits {schema.__name__}")


#: A delta's section headings and requirement headings, the ID as the domain's own grammar spells one.
_OWED = re.compile(
    rf"^## (?P<section>ADDED|MODIFIED|REMOVED) Requirements\s*$|^### (?P<req>{REQ_ID.pattern}):", re.MULTILINE
)


def tasks_serving(instruction: str) -> dict:
    """The canned tasks, naming the requirements the deltas of `instruction` add or modify where those are not the
    canned ones: a task list must serve what its change owes, and a change `propose` drafts owes IDs of its own."""
    try:
        deltas = between(instruction, "deltas")
    except ValueError:
        return CANNED_TASKS
    section, owed = "", []
    for found in _OWED.finditer(deltas):
        if found["section"]:
            section = found["section"]
        elif section != "REMOVED" and found["req"] not in owed:
            owed.append(found["req"])
    named = {req for group in CANNED_TASKS["groups"] for task in group["tasks"] for req in task["requirements"]}
    if not owed or set(owed) == named:
        return CANNED_TASKS
    groups = [
        {**group, "tasks": [{**task, "requirements": owed} for task in group["tasks"]]}
        for group in CANNED_TASKS["groups"]
    ]
    return {"groups": groups}


def scout_naming(instruction: str) -> dict:
    """The canned scout, naming a file the request's own list of files holds: its own where that is listed, and the
    first one otherwise. A scout that names a file the repository does not hold reads nothing, and a test would
    then pass without the reading it thinks it made."""
    try:
        # A repository too large to list is shown as a sentence and its folders, and none of those is a file.
        listed = [line for line in between(instruction, "tree").split("\n") if line and not line.endswith((")", ":"))]
    except ValueError:
        return CANNED_SCOUT
    if not listed or set(CANNED_SCOUT["files"]) <= set(listed):
        return CANNED_SCOUT
    return {**CANNED_SCOUT, "files": listed[:1]}


_SHOWN = re.compile(
    r"^=== (?P<path>\S+) \((?:whole|lines \d+ to \d+ of \d+)\)\n(?P<text>(?:(?!===).*\n?)*)", re.MULTILINE
)


def survey_quoting(instruction: str) -> dict:
    """The canned survey, quoting text the request really shows: the first line of eight characters or more of the
    first file under `material`. Where the canned statement's own file is shown, it is the canned survey itself."""
    try:
        material = between(instruction, "material")
    except ValueError:
        return CANNED_SURVEY
    canned = CANNED_SURVEY["statements"][0]
    for found in _SHOWN.finditer(material):
        if found["path"] == canned["file"] and canned["quote"] in found["text"]:
            return CANNED_SURVEY
    for found in _SHOWN.finditer(material):
        quote = next((line.strip() for line in found["text"].split("\n") if len(line.strip()) >= 8), None)
        if quote:
            return {**CANNED_SURVEY, "statements": [{**canned, "file": found["path"], "quote": quote}]}
    return {**CANNED_SURVEY, "statements": []}


class FakeProvider:
    """What the fake does for a request whose instruction contains a text, per test, and every request it was sent."""

    def __init__(self) -> None:
        self.rules: list[tuple[str, object]] = []
        self.requests: list[LlmRequest] = []

    def clear(self) -> None:
        self.rules.clear()
        self.requests.clear()

    def raises_when(self, text: str, exc: BaseException) -> None:
        self.rules.append((text, exc))

    def answers_when(self, text: str, payload: dict | str) -> None:
        """`payload` in place of the canned answer; as a str, the text itself."""
        self.rules.append((text, payload))

    def answers_each_time(self, text: str, payloads) -> None:
        """The next of `payloads`, an iterator, on each request whose instruction holds `text`; None among them, or
        the iterator's end, means the canned answer."""
        self.rules.append((text, payloads))

    def answers_from(self, recording) -> None:
        """Each stage's answers as a recording holds them, in their order: a stage is known by the first line of
        its instruction, and a call that got no answer gave none to replay."""
        by_opening: dict[str, list[str]] = {}
        for call in recording.calls:
            if call.answer is not None:
                by_opening.setdefault(call.instruction.split("\n", 1)[0], []).append(call.answer)
        for opening, answers in by_opening.items():
            self.answers_each_time(opening, iter(answers))

    def answer(self, llm_request: LlmRequest) -> dict | str | None:
        instruction = str(llm_request.config.system_instruction or "")
        for text, rule in self.rules:
            if text in instruction:
                if isinstance(rule, BaseException):
                    raise rule
                if isinstance(rule, dict | str | LlmResponse):
                    return rule
                return next(rule, None)  # an iterator: one answer a request
        return None


PROVIDER = FakeProvider()  # process-wide, like the registry below; the fixture clears it around each test


class FakeModel(Gemini):
    """Answers instantly and offline. A Gemini model, as the Gemini arm, where it runs, requires one."""

    model: str = "fake"

    @classmethod
    def supported_models(cls) -> list[str]:
        return [r"fake.*"]

    async def generate_content_async(
        self,
        llm_request: LlmRequest,
        stream: bool = False,  # noqa: ARG002 -- the BaseLlm contract
    ) -> AsyncGenerator[LlmResponse]:
        PROVIDER.requests.append(llm_request)
        payload = PROVIDER.answer(llm_request)
        if isinstance(payload, LlmResponse):  # a whole response, as a provider would stamp it
            yield payload
            return
        schema = llm_request.config.response_schema
        if payload is None and schema is not None:
            payload = canned_for(schema)
            fitted = {
                id(CANNED_TASKS): tasks_serving,
                id(CANNED_SCOUT): scout_naming,
                id(CANNED_SURVEY): survey_quoting,
            }
            if fit := fitted.get(id(payload)):
                payload = fit(str(llm_request.config.system_instruction or ""))
        if isinstance(payload, str):
            text = payload
        else:
            text = json.dumps(payload) if payload is not None else "Hello from the fake model."
        yield LlmResponse(
            content=types.ModelContent(text),
            usage_metadata=types.GenerateContentResponseUsageMetadata(
                prompt_token_count=100, candidates_token_count=20, total_token_count=120
            ),
        )


LLMRegistry.register(FakeModel)  # process-wide, once; `fake.*` matches nothing a real run would name


@pytest.fixture
def fake_provider() -> Iterator[FakeProvider]:
    """The fake's behaviour for one test; whatever a test sets is gone before the next."""
    PROVIDER.clear()
    yield PROVIDER
    PROVIDER.clear()


def pytest_configure() -> None:
    """Before any test module imports LiteLLM, which in its default mode reads the nearest `.env` into the process
    and fetches its model map from the network."""
    os.environ["LITELLM_MODE"] = "PRODUCTION"
    os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"


@pytest.fixture(autouse=True)
def _umask_kept() -> Iterator[None]:
    """No test leaves its umask to the next: the login sets 0o077 for its whole process."""
    umask = os.umask
    mask = umask(0o022)
    umask(mask)
    yield
    umask(mask)


@pytest.fixture(autouse=True)
def _nothing_from_the_shell(monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory) -> None:
    """No test inherits a provider, a model, a key or where an arm's calls go, nor reads the developer's Copilot
    login: its folder is one no test made. Each test sets what it runs on."""
    for name in [name for name in os.environ if name.startswith("SPEC_")] + [
        "GOOGLE_GENAI_USE_ENTERPRISE",
        "GOOGLE_GENAI_USE_VERTEXAI",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_LOCATION",
        "GITHUB_COPILOT_API_BASE",
        "GITHUB_COPILOT_ACCESS_TOKEN_FILE",
        "GITHUB_COPILOT_API_KEY_FILE",
    ]:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GITHUB_COPILOT_TOKEN_DIR", str(tmp_path_factory.getbasetemp() / "no-copilot-login"))


def cached_copilot_token(monkeypatch: pytest.MonkeyPatch, folder: Path, text: str | None = "a token") -> None:
    """The Copilot arm's token cache in `folder`, holding `text`, or holding no token where `text` is None."""
    if text is not None:
        (folder / "access-token").write_text(text, encoding="utf-8")
    monkeypatch.setenv("GITHUB_COPILOT_TOKEN_DIR", str(folder))


@pytest.fixture(autouse=True)
def _no_dotenv(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test reads the developer's `.env`: the command's one loader is replaced."""
    from adk_spec.interfaces import cli

    monkeypatch.setattr(cli, "_load_env", lambda: None)


def device_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    """The Copilot login's device flow with no network and no wait: GitHub's code for the person to enter, then each
    poll answered as `github_answers` says."""
    import importlib

    from litellm.llms.github_copilot import authenticator

    code = {"device_code": "d", "user_code": "ABCD-1234", "verification_uri": "https://github.com/login/device"}
    monkeypatch.setattr(authenticator.Authenticator, "_get_device_code", lambda _self: code)
    monkeypatch.setattr(importlib.import_module("adk_spec.interfaces.login").time, "sleep", lambda _seconds: None)


def github_answers(monkeypatch: pytest.MonkeyPatch, reply: object) -> None:
    """GitHub's token endpoint, answering `reply` to each poll of the login: no network in the suite. A dict is the
    JSON object GitHub sends; an `httpx.Response` is handed over as it is, a page that is no JSON among them."""
    from types import SimpleNamespace

    import httpx

    class Client:
        def __init__(self, **_kwargs) -> None: ...

        def __enter__(self):
            return self

        def __exit__(self, *_exc) -> bool:
            return False

        def post(self, *_args, **_kwargs):
            return reply if isinstance(reply, httpx.Response) else SimpleNamespace(json=lambda: reply)

    monkeypatch.setattr(httpx, "Client", Client)  # the login imports httpx and resolves Client at the call


def seeded(root: Path):
    """A workspace at `root` holding the sample living spec of `auth` and one lean draft change, `passkeys`, with
    its brief, tasks and delta: where most tests of the workspace and the command start."""
    from samples import BRIEF, DELTA, SPEC, TASKS

    from adk_spec.domain.spec_md import parse_spec
    from adk_spec.workspace.files import write_text
    from adk_spec.workspace.layout import Workspace

    workspace = Workspace.init(root)
    workspace.write_specs({"auth": parse_spec(SPEC)})
    folder = workspace.new_change("passkeys", "lean")
    write_text(folder / "brief.md", BRIEF)
    write_text(folder / "tasks.md", TASKS)
    write_text(folder / "specs" / "auth" / "spec.md", DELTA)
    return workspace


def on_the_fake(monkeypatch: pytest.MonkeyPatch) -> None:
    """The Gemini arm on the fake model, with a key present: what a test of a model-calling command runs on."""
    monkeypatch.setenv("SPEC_PROVIDER", "gemini")
    monkeypatch.setenv("SPEC_MODEL", "fake")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")


def run(root: Path, *argv: str) -> int:
    """The command, in process, in the workspace at `root`."""
    from adk_spec.interfaces.cli import main

    return main(["--root", str(root), *argv])


def approved(root: Path, change: str = "passkeys") -> None:
    """The change approved, as a person does before the work starts. No `rebase` first: an approval records the
    bases that are missing."""
    assert run(root, "approve", change, "--by", "reviewer") == 0


def state_of(root: Path, change: str = "passkeys") -> dict:
    return json.loads((root / f".spec/changes/{change}/change.json").read_text(encoding="utf-8"))


def _git(root: Path, *args: str) -> str:
    """One git command a test makes of its own, by `subprocess` and an argv list, under settings of its own: a
    person's config and signing key change nothing."""
    import shutil
    import subprocess

    git = shutil.which("git")
    assert git, "the suite needs git on PATH"
    env = {name: value for name, value in os.environ.items() if not name.startswith("GIT_")}
    env |= {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    who = ["-c", "user.name=A Test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false"]
    done = subprocess.run([git, "-C", str(root), *who, *args], env=env, capture_output=True, check=True)
    return done.stdout.decode("utf-8").strip()


def repository_commit(root: Path, message: str) -> str:
    """Everything under `root` committed, `.spec/` too: the new commit's ID."""
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)
    return _git(root, "rev-parse", "HEAD")


def repository(root: Path, files: dict[str, str] | None = None) -> str:
    """A git repository at `root` with one commit of `files` (one source file where none is given) and of whatever
    stands there already: the commit's ID."""
    root.mkdir(parents=True, exist_ok=True)
    for path, text in (files or {"src/app.py": "def login():\n    return password()\n"}).items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text, encoding="utf-8", newline="\n")
    _git(root, "init", "-q", "-b", "main")
    return repository_commit(root, "first")


#: An API repository's files, for a change that spans the workspace's repository and an API beside it.
API = {"src/routes.py": "def sign_in(request):\n    return start_session(request.user)\n"}


def beside(tmp_path: Path) -> Path:
    """A workspace and its change in a repository at `tmp_path / "app"`, and an API repository beside it at
    `tmp_path / "api"`: the workspace's root."""
    root = tmp_path / "app"
    seeded(root)
    repository(root)
    repository(tmp_path / "api", API)
    return root


def between(text: str, label: str) -> str:
    """What an instruction holds between the two markers of `label`."""
    from adk_spec.orchestration.stages import BOUNDARY

    opened, closed = f"<<< {label} {BOUNDARY}\n", f"\n>>> {label} {BOUNDARY}"
    return text[text.index(opened) + len(opened) : text.index(closed)]


def asked(fake_provider, opening: str) -> int:
    """How many requests the fake was sent whose instruction opens with `opening`."""
    return sum(str(r.config.system_instruction).startswith(opening) for r in fake_provider.requests)


def sent_to(fake_provider, opening: str) -> str:
    """The instruction of the one request the fake was sent that opens with `opening`."""
    (instruction,) = [
        str(r.config.system_instruction)
        for r in fake_provider.requests
        if str(r.config.system_instruction).startswith(opening)
    ]
    return instruction


def removed(path: Path) -> None:
    """A folder deleted whole, a repository's with it: git makes its objects read-only, which Windows will not delete
    until they are made writable again."""

    def writable_then_again(remove, name, _exc) -> None:
        os.chmod(name, stat.S_IWRITE)
        remove(name)

    shutil.rmtree(path, onexc=writable_then_again)


def held_open_from(monkeypatch: pytest.MonkeyPatch, nth: int = 2) -> None:
    """`os.replace` refused on the file its `nth` call names, from then on: held open, as Windows holds a file, so
    every try at it fails, a retry's too, and every other file is replaced."""
    real, asked = os.replace, []

    def replace(source, target) -> None:
        asked.append(target)
        if len(asked) >= nth and target == asked[nth - 1]:
            raise PermissionError("another process holds the file")
        real(source, target)

    monkeypatch.setattr(os, "replace", replace)
