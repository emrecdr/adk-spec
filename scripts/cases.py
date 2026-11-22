"""The labelled set: six changes, each well formed, each with one fault planted or none, and what a check or a
verification must find in it.

A case builds its own workspace from the domain's types, rendered by the package's own renderers, so the set cannot
drift from the grammar it measures against. Nothing here calls a model: `measure.py` does.
"""

from __future__ import annotations

import contextlib
import io
import os
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from adk_spec.domain.brief_md import render_brief
from adk_spec.domain.delta_md import render_delta
from adk_spec.domain.lifecycle import capture_bases
from adk_spec.domain.model import Brief, Delta, Requirement, Scenario, Spec, Task, TaskGroup
from adk_spec.domain.tasks_md import render_tasks
from adk_spec.interfaces import cli
from adk_spec.workspace.files import write_text
from adk_spec.workspace.layout import Workspace

CHANGE = "measured"


@dataclass(frozen=True)
class Expected:
    """What must be found: a finding or a verdict whose code starts with one of `codes`, on one of `paths`, and,
    where `words` are given, whose text holds one of them."""

    codes: tuple[str, ...] | str
    paths: tuple[str, ...]
    words: tuple[str, ...] = ()

    def met_by(self, seen: Any) -> bool:
        text = seen.text.lower()
        return (
            seen.code.startswith(self.codes)
            and seen.path in self.paths
            and (not self.words or any(word.lower() in text for word in self.words))
        )


@dataclass(frozen=True)
class Case:
    name: str
    #: Makes the workspace under a folder and returns the change's ID.
    build: Callable[[Path], str]
    command: str
    expect: tuple[Expected, ...]
    #: A case with nothing planted: a blocking finding on it is a false one.
    clean: bool = False
    #: A case code decides before any model is asked: it costs no call.
    by_code: bool = False


def _req(req_id: str, name: str, statement: str, *steps: str) -> Requirement:
    return Requirement(id=req_id, name=name, statement=statement, scenarios=(Scenario(name=name, steps=steps),))


LIVING = Spec(
    capability="auth",
    purpose="Sign-in and session handling.",
    requirements=(
        _req(
            "REQ-AUTH-001",
            "Sign in with email",
            "The system SHALL let a registered user sign in with email and password.",
            "WHEN the user submits a valid email and password",
            "THEN the system starts a session",
        ),
        _req(
            "REQ-AUTH-002",
            "Lock after failures",
            "The system MUST lock an account after five failed attempts.",
            "GIVEN four failed attempts",
            "WHEN a fifth attempt fails",
            "THEN the account is locked",
        ),
    ),
)
PASSKEY = _req(
    "REQ-AUTH-003",
    "Sign in with a passkey",
    "The system SHALL let a user sign in with a passkey.",
    "WHEN the user presents a registered passkey",
    "THEN the system starts a session",
)
BRIEF = Brief(
    title="Sign in with a passkey",
    why="Passwords are the top source of account takeovers.",
    # What the delta delivers, and no more: a promise no requirement keeps is a fault of its own, and the model
    # finds it. The second live measurement did, in the clean case too.
    what_changes="Users can sign in with a passkey. Password sign-in stays as it is.",
    non_goals="No change to session length. No change to the lock after failed attempts.",
    capabilities=("auth",),
    impact="The sign-in page and the session service.",
    assumptions="Browsers in scope support WebAuthn.",
)


def _task(number: int, description: str, *requirements: str, test: bool = False) -> Task:
    file = "tests/test_auth.py" if test else "src/auth.py"
    return Task(
        id=f"T{number:03d}",
        done=False,
        parallel=False,
        requirements=requirements,
        description=description,
        files=(file,),
        verify="uv run pytest tests/test_auth.py",
    )


PASSKEY_TASKS = (
    _task(1, "Write the failing passkey sign-in test", "REQ-AUTH-003", test=True),
    _task(2, "Implement the passkey handler", "REQ-AUTH-003"),
)


def _workspace(
    root: Path, *, brief: Brief, delta: Delta, tasks: tuple[Task, ...], constitution: str | None = None
) -> Workspace:
    """A workspace holding the living spec of `auth` and one standard change, its bases recorded."""
    workspace = Workspace.init(root)
    workspace.write_specs({"auth": LIVING})
    if constitution is not None:
        write_text(workspace.home / "constitution.md", constitution)
    folder = workspace.new_change(CHANGE, "standard")
    write_text(folder / "brief.md", render_brief(brief))
    write_text(folder / "specs" / "auth" / "spec.md", render_delta(delta))
    write_text(folder / "tasks.md", render_tasks((TaskGroup(title="1. The change", tasks=tasks),)))
    state = workspace.load_change(CHANGE).change.state
    workspace.save_state(state.model_copy(update={"bases": capture_bases({"auth": delta}, {"auth": LIVING})}))
    return workspace


def _contradiction(root: Path) -> str:
    """The brief says session length is left alone; the delta adds a requirement that ends idle sessions."""
    idle = _req(
        "REQ-AUTH-004",
        "End idle sessions",
        "The system SHALL end a session after ten minutes without a request.",
        "WHEN a session has seen no request for ten minutes",
        "THEN the system ends the session",
    )
    tasks = (
        *PASSKEY_TASKS,
        _task(3, "Write the failing test for ending an idle session", "REQ-AUTH-004", test=True),
        _task(4, "End a session after ten idle minutes", "REQ-AUTH-004"),
    )
    _workspace(root, brief=BRIEF, delta=Delta(capability="auth", added=(PASSKEY, idle)), tasks=tasks)
    return CHANGE


def _ambiguity(root: Path) -> str:
    """A requirement nobody could test: `quickly`, and a scenario that says `fast`."""
    fast = _req(
        "REQ-AUTH-003",
        "Fast sign-in",
        "The system SHALL respond quickly to a sign-in.",
        "WHEN the user signs in",
        "THEN the response is fast",
    )
    brief = BRIEF.model_copy(
        update={"title": "Faster sign-in", "why": "Sign-in feels slow.", "what_changes": "Sign-in responds faster."}
    )
    tasks = (
        _task(1, "Write the failing test for the sign-in response time", "REQ-AUTH-003", test=True),
        _task(2, "Make the sign-in respond faster", "REQ-AUTH-003"),
    )
    _workspace(root, brief=brief, delta=Delta(capability="auth", added=(fast,)), tasks=tasks)
    return CHANGE


def _no_task(root: Path) -> str:
    """Two requirements added, tasks for one: code finds this, every run, with no model asked."""
    remove = _req(
        "REQ-AUTH-004",
        "Remove a passkey",
        "The system SHALL let a user remove a passkey of theirs.",
        "WHEN the user removes a passkey",
        "THEN that passkey signs nobody in",
    )
    brief = BRIEF.model_copy(update={"what_changes": BRIEF.what_changes + " A user can remove a passkey of theirs."})
    _workspace(root, brief=brief, delta=Delta(capability="auth", added=(PASSKEY, remove)), tasks=PASSKEY_TASKS)
    return CHANGE


def _constitution(root: Path) -> str:
    """The repository's rules ask for a test with every change; the tasks hold none."""
    rules = (
        "# Constitution\n\n## Rules\n\n"
        "- Every change adds or updates a test, because a requirement nobody tests is not kept. A task list with no "
        "task that writes a test is not ready.\n"
    )
    tasks = (_task(1, "Implement the passkey handler", "REQ-AUTH-003"),)
    delta = Delta(capability="auth", added=(PASSKEY,))
    _workspace(root, brief=BRIEF, delta=delta, tasks=tasks, constitution=rules)
    return CHANGE


def _clean(root: Path) -> str:
    """Nothing planted: a brief, one added requirement and its two tasks, which agree."""
    _workspace(root, brief=BRIEF, delta=Delta(capability="auth", added=(PASSKEY,)), tasks=PASSKEY_TASKS)
    return CHANGE


BEFORE = "def sign_in(user):\n    return password(user)\n\n\ndef lock(account):\n    return account.failures >= 5\n"
#: The line of the half-done work that shows the passkey requirement met.
HALF_DONE_LINE = "return passkey(user) or password(user)"
AFTER = BEFORE.replace("return password(user)", HALF_DONE_LINE)
TEST = "def test_a_registered_passkey_starts_a_session(user):\n    assert sign_in(user).session\n"


def _half_done(root: Path) -> str:
    """Two requirements approved, one implemented: the passkey is there, the lock still falls at five."""
    sooner = _req(
        "REQ-AUTH-002",
        "Lock after failures",
        "The system MUST lock an account after three failed attempts.",
        "GIVEN two failed attempts",
        "WHEN a third attempt fails",
        "THEN the account is locked",
    )
    brief = BRIEF.model_copy(
        update={
            "what_changes": BRIEF.what_changes + " An account is locked after three failed attempts, not five.",
            "non_goals": "No change to session length.",
        }
    )
    tasks = (*PASSKEY_TASKS, _task(3, "Lock an account after three failed attempts", "REQ-AUTH-002"))
    _workspace(root, brief=brief, delta=Delta(capability="auth", added=(PASSKEY,), modified=(sooner,)), tasks=tasks)
    write_text(root / "src" / "auth.py", BEFORE)
    _commit_all(root)
    with contextlib.redirect_stdout(io.StringIO()):
        for command in (("check", CHANGE, "--no-model"), ("approve", CHANGE, "--by", "the measurement")):
            if cli.main(["--root", str(root), *command]) != 0:
                raise RuntimeError(f"the half-done case could not be built: `{' '.join(command)}` was refused")
    write_text(root / "src" / "auth.py", AFTER)
    write_text(root / "tests" / "test_auth.py", TEST)
    return CHANGE


SESSION_PY = '"""Sessions: the one place a signed-in user is given one."""\n\n\ndef start_session(user):\n'
SESSION_PY += '    return {"user": user, "hours": 8}\n'
PASSWORD_PY = "from auth.session import start_session\n\n\ndef sign_in_with_password(user, password):\n"
PASSWORD_PY += '    if not user.check(password):\n        raise PermissionError("wrong password")\n'
PASSWORD_PY += "    return start_session(user)\n"
OLD_PY = "# Kept for the 2019 migration. Nothing imports this file.\n\n\ndef start_session_v1(user):\n"
OLD_PY += "    return user.id\n"
#: Where a passkey sign-in plugs in, and the old file of a similar name that it does not.
INTEGRATION = ("src/auth/password.py", "src/auth/session.py")
DECOY = "src/legacy/auth_session_old.py"


def _integration(root: Path) -> str:
    """A repository with one place where sign-in starts a session, and an old file of a similar name that nothing
    uses. The change has no plan yet: `plan` reads the code first, and what it states is what is scored."""
    _workspace(root, brief=BRIEF, delta=Delta(capability="auth", added=(PASSKEY,)), tasks=())
    sources = {INTEGRATION[0]: PASSWORD_PY, INTEGRATION[1]: SESSION_PY, DECOY: OLD_PY}
    for path, text in {**sources, "tests/test_password.py": "def test_sign_in(): ...\n"}.items():
        write_text(root / path, text)
    _commit_all(root)
    return CHANGE


LOGIN_JS = "export async function signIn(user, password) {\n"
LOGIN_JS += "  return fetch('/api/sign-in', { method: 'POST', body: JSON.stringify({ user, password }) });\n}\n"
#: Where a passkey sign-in plugs in when the API is a repository of its own, beside the web app's.
ACROSS = tuple(f"api/{path}" for path in INTEGRATION)


def _across(root: Path) -> str:
    """A web app in the workspace, which signs in through an API in a repository beside it, named with the change.
    Where sign-in starts a session is in the API; the web app holds an old file of a similar name that nothing uses.
    The change has no plan yet: `plan` reads both repositories, and what it states is what is scored."""
    workspace = _workspace(root, brief=BRIEF, delta=Delta(capability="auth", added=(PASSKEY,)), tasks=())
    for path, text in {"src/login.js": LOGIN_JS, DECOY: OLD_PY}.items():
        write_text(root / path, text)
    _commit_all(root)
    api = root.parent / f"{root.name}-api"  # beside the workspace, and the run's own
    sources = {INTEGRATION[0]: PASSWORD_PY, INTEGRATION[1]: SESSION_PY, "tests/test_password.py": "def test(): ...\n"}
    for path, text in sources.items():
        write_text(api / path, text)
    _commit_all(api)
    state = workspace.load_change(CHANGE).change.state
    workspace.save_state(state.model_copy(update={"repositories": {"api": f"../{api.name}"}}))
    return CHANGE


ERRORS_PY = '"""Every error this service raises: one class, and a reason in words."""\n\n\n'
ERRORS_PY += "class AppError(Exception):\n    pass\n"
STORE_PY = "from errors import AppError\n\n\ndef save(row):\n    if not row:\n"
STORE_PY += '        raise AppError("an empty row is not saved")\n    return row\n'
SESSION_TEST_PY = "from auth.session import start_session\n\n\ndef test_a_session_is_given_to_a_user():\n"
SESSION_TEST_PY += "    assert start_session('a')['user'] == 'a'\n"
#: The two conventions planted in the profile case: errors raised as one class, and tests beside the code.
PROFILE = ("src/errors.py", "src/auth/session_test.py")


def _profile(root: Path) -> str:
    """A repository with no `.spec/` yet, whose errors are raised as one class and whose tests stand beside the code
    they test. `init` reads it, and what is scored is the rules it drafts into the constitution: there is no change,
    so the ID is empty."""
    files = {PROFILE[0]: ERRORS_PY, "src/store.py": STORE_PY, "src/auth/session.py": SESSION_PY}
    for path, text in {**files, PROFILE[1]: SESSION_TEST_PY, "README.md": "# A service\n"}.items():
        write_text(root / path, text)
    _commit_all(root)
    return ""


def _commit_all(root: Path) -> None:
    """A git repository at `root` with one commit of all it holds, made under settings of this script's own."""
    git = shutil.which("git")
    if git is None:
        raise RuntimeError("the half-done case needs git on PATH")
    env = {name: value for name, value in os.environ.items() if not name.startswith("GIT_")}
    env |= {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    who = ["-c", "user.name=The measurement", "-c", "user.email=measure@example.invalid", "-c", "commit.gpgsign=false"]
    for args in (["init", "-q", "-b", "main"], ["add", "-A"], ["commit", "-q", "-m", "before the work"]):
        subprocess.run([git, "-C", str(root), *who, *args], env=env, capture_output=True, check=True)


CASES = (
    Case(
        "contradiction",
        _contradiction,
        "check",
        (Expected(("check.contradiction", "check.gap"), ("brief.md", "specs/auth/spec.md"), ("session",)),),
    ),
    Case(
        "ambiguity", _ambiguity, "check", (Expected("check.ambiguity", ("specs/auth/spec.md",), ("quickly", "fast")),)
    ),
    Case(
        "no-task",
        _no_task,
        "check",
        (Expected("check.requirement-no-task", ("tasks.md",), ("REQ-AUTH-004",)),),
        by_code=True,
    ),
    Case(
        "constitution",
        _constitution,
        "check",
        (Expected(("check.constitution", "check.gap"), ("tasks.md",), ("test",)),),
    ),
    Case("clean", _clean, "check", (), clean=True),
    Case(
        "half-done",
        _half_done,
        "verify",
        (Expected("verdict.met", ("REQ-AUTH-003",)), Expected("verdict.un", ("REQ-AUTH-002",))),
    ),
    Case("integration", _integration, "plan", (Expected(("context.touches", "context.exists"), INTEGRATION),)),
    Case("across", _across, "plan", (Expected(("context.touches", "context.exists"), ACROSS),)),
    Case("profile", _profile, "init", (Expected("rule", PROFILE),)),
)
