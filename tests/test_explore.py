"""The reading of a repository's code for one change: a scout names what to read, code reads it through git's own
list, a survey states what it shows, and code keeps a statement only where its quote is in the file it names."""

from __future__ import annotations

import pytest
from conftest import between, on_the_fake, repository

from adk_spec.orchestration import explore
from adk_spec.orchestration.explore import build_explore_app, explored
from adk_spec.orchestration.gate import FAILURE
from adk_spec.orchestration.plugins import UsageLedger
from adk_spec.orchestration.run import run_seeded
from adk_spec.orchestration.stages import BRIEF_TEXT, CONSTITUTION, DELTAS_TEXT, TREE
from adk_spec.workspace.context import tree_text
from adk_spec.workspace.source import Source

SCOUT, SURVEY = "You choose what to read", "You read parts of a repository's code"
FILES = {
    "src/app.py": "def login():\n    return password()\n",
    "src/auth/session.py": "def start_session(user):\n    return Session(user)\n",
    "docs/auth.md": "# Auth\n\nSessions last eight hours.\n",
}
APP = {"kind": "touches", "file": "src/app.py", "quote": "return password()", "note": "Sign-in is decided here."}
SESSION = {"kind": "exists", "file": "src/auth/session.py", "quote": "def start_session(user):", "note": "One place."}
DOCS = {"kind": "convention", "file": "docs/auth.md", "quote": "Sessions last eight hours.", "note": "Eight hours."}


@pytest.fixture(autouse=True)
def _fake_arm(monkeypatch) -> None:
    on_the_fake(monkeypatch)


def survey(*statements: dict, files: tuple[str, ...] = ()) -> dict:
    return {"statements": list(statements), "more_files": list(files), "more_folders": [], "more_searches": []}


async def read(root):
    repository(root, FILES)
    held = Source.of(root, exclude=())
    seed = {BRIEF_TEXT: "# Sign in with a passkey\n", DELTAS_TEXT: "", CONSTITUTION: "", TREE: tree_text(held.paths)}
    return await run_seeded(build_explore_app(source=held, ledger=UsageLedger()), state=seed, prompt="explore")


def sent(fake_provider, opening: str) -> list[str]:
    texts = (str(r.config.system_instruction) for r in fake_provider.requests)
    return [text for text in texts if text.startswith(opening)]


@pytest.mark.asyncio
async def test_the_scout_names_and_the_survey_states_and_code_keeps_what_is_quoted(tmp_path, fake_provider) -> None:
    run = await read(tmp_path)
    found = explored(run.state)
    assert [(one.kind, one.path, one.line) for one in found.statements] == [("touches", "src/app.py", 2)]
    assert found.read == ("src/app.py (whole)",) and found.dropped == 0 and run.state.get(FAILURE) is None
    (scout,), (surveyed,) = sent(fake_provider, SCOUT), sent(fake_provider, SURVEY)
    assert "src/auth/session.py" in between(scout, "tree"), "the scout chooses from the repository's own paths"
    assert between(surveyed, "material") == "=== src/app.py (whole)\ndef login():\n    return password()"


@pytest.mark.asyncio
async def test_a_statement_that_quotes_nothing_real_is_counted_and_not_kept(tmp_path, fake_provider) -> None:
    invented = {**APP, "quote": "return passkey_or_password()"}
    fake_provider.answers_when(SURVEY, survey(APP, invented, {**SESSION}))
    found = explored((await read(tmp_path)).state)
    assert [one.path for one in found.statements] == ["src/app.py"] and found.dropped == 2, "one invented, one unread"


@pytest.mark.asyncio
async def test_the_survey_may_look_again_and_no_more_than_the_budget(tmp_path, fake_provider) -> None:
    rounds = [survey(APP, files=("src/auth/session.py",)), survey(SESSION, files=("docs/auth.md",))]
    rounds += [survey(DOCS, files=("src/app.py:1-1",)), survey(APP, files=("docs/auth.md",))]
    fake_provider.answers_each_time(SURVEY, iter(rounds))
    found = explored((await read(tmp_path)).state)
    assert len(sent(fake_provider, SURVEY)) == explore.LOOK_BUDGET == 3, "what the third asked for is not read"
    assert [one.path for one in found.statements] == ["src/app.py", "src/auth/session.py", "docs/auth.md"]
    assert found.read == ("src/app.py (whole)", "src/auth/session.py (whole)", "docs/auth.md (whole)")
    second = sent(fake_provider, SURVEY)[1]
    assert between(second, "material").startswith("=== src/auth/session.py (whole)")
    assert "src/app.py:2" in between(second, "stated"), "a later round is told what is kept already"


@pytest.mark.asyncio
async def test_a_file_already_read_is_not_read_twice(tmp_path, fake_provider) -> None:
    again = survey(APP, files=("src/app.py", "src/auth/session.py"))
    fake_provider.answers_each_time(SURVEY, iter([again, survey(SESSION)]))
    found = explored((await read(tmp_path)).state)
    assert found.read == ("src/app.py (whole)", "src/auth/session.py (whole)")
    assert "src/app.py (whole)" not in between(sent(fake_provider, SURVEY)[1], "material")


@pytest.mark.asyncio
async def test_a_scout_that_names_nothing_readable_ends_with_nothing_kept(tmp_path, fake_provider) -> None:
    fake_provider.answers_when(SCOUT, {"files": ["../.env", "nope.py"], "folders": [], "searches": [], "reason": "x"})
    run = await read(tmp_path)
    found = explored(run.state)
    assert found.statements == [] and found.read == () and len(found.left_out) == 2
    assert sent(fake_provider, SURVEY) == [], "there is nothing to survey"


@pytest.mark.asyncio
async def test_a_survey_given_up_keeps_what_the_rounds_before_it_kept(tmp_path, fake_provider) -> None:
    answers = [survey(APP, files=("src/auth/session.py",)), "not json", "not json", "not json"]
    fake_provider.answers_each_time(SURVEY, iter(answers))
    run = await read(tmp_path)
    assert run.state[FAILURE].startswith("survey:")
    assert [one.path for one in explored(run.state).statements] == ["src/app.py"]


@pytest.mark.asyncio
async def test_each_round_has_its_own_tries_and_reads_no_answer_of_the_round_before(tmp_path, fake_provider) -> None:
    answers = ["not json", survey(APP, files=("src/auth/session.py",)), "not json", "not json", survey(SESSION)]
    fake_provider.answers_each_time(SURVEY, iter(answers))
    run = await read(tmp_path)
    assert run.state.get(FAILURE) is None
    assert [one.path for one in explored(run.state).statements] == ["src/app.py", "src/auth/session.py"]


@pytest.mark.asyncio
async def test_no_more_statements_are_kept_than_the_budget(tmp_path, monkeypatch, fake_provider) -> None:
    monkeypatch.setattr(explore, "STATEMENT_BUDGET", 2)
    more = {**APP, "quote": "def login():", "note": "The entry point."}
    fake_provider.answers_when(SURVEY, survey(APP, more, {**APP, "kind": "risk"}, files=("src/auth/session.py",)))
    found = explored((await read(tmp_path)).state)
    assert len(found.statements) == 2 and len(sent(fake_provider, SURVEY)) == 1, "a full budget ends the reading"


@pytest.mark.asyncio
async def test_a_reader_that_fails_on_a_later_look_loses_no_statement_already_made(
    tmp_path, monkeypatch, fake_provider
) -> None:
    """Found by the cleanup review: one node held a statement to its quote and then read on, so a failure of the
    reading threw away the statement the survey had just been paid to make."""
    looks = []
    real = Source.gathered

    def flaky(self, files, folders, searches):
        looks.append(files)
        if len(looks) == 2:
            raise OSError("the disk went away")
        return real(self, files, folders, searches)

    monkeypatch.setattr(Source, "gathered", flaky)
    fake_provider.answers_when(SURVEY, survey(APP, files=("src/auth/session.py",)))
    run = await read(tmp_path)
    assert [one.path for one in explored(run.state).statements] == ["src/app.py"] and len(looks) == 2
