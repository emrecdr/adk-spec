"""The reading of a repository's code for one change: a scout names what to read, code reads it through git's own
list, a survey states what it shows, and code keeps a statement only where its quote is in the file it names."""

from __future__ import annotations

import pytest
from conftest import between, on_the_fake, python_environment, repository

from adk_spec.orchestration import explore
from adk_spec.orchestration.explore import build_explore_app, explored
from adk_spec.orchestration.gate import FAILURE
from adk_spec.orchestration.plugins import UsageLedger
from adk_spec.orchestration.run import run_seeded
from adk_spec.orchestration.stages import BRIEF_TEXT, DELTAS_TEXT, RULES_TEXT, TREE
from adk_spec.workspace import context, source
from adk_spec.workspace.context import tree_text
from adk_spec.workspace.source import Source

SCOUT, SURVEY = "You choose what to read", "You read parts of a repository's code"
REVIEW = "You review what a reading of a repository's code found"
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


async def read(root, files: dict[str, str] | None = None, extra: dict | None = None):
    repository(root, files or FILES)
    held = Source.of(root, exclude=())
    seed = {BRIEF_TEXT: "# Sign in with a passkey\n", DELTAS_TEXT: "", RULES_TEXT: "", TREE: tree_text(held.paths)}
    seed |= extra or {}
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
    assert found.over == 1, "phase 18: the statement past the budget is counted"


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


@pytest.mark.asyncio
async def test_a_file_left_out_for_room_is_read_when_it_is_asked_for_again(
    tmp_path, monkeypatch, fake_provider
) -> None:
    """Every request of a round was remembered as answered, also one left out for room: asked for again by its
    path, it was passed over, nothing was left to read, and the reading ended as if it were whole."""
    monkeypatch.setattr(source, "ROUND_MAX_CHARS", 120)
    fake_provider.answers_when(SCOUT, {"files": list(FILES), "folders": [], "searches": [], "reason": "All three."})
    # The first round has room for two of the three files: the session's is left out for room, and asked for again.
    rounds = [survey(APP, DOCS, files=("src/auth/session.py",)), survey(SESSION)]
    fake_provider.answers_each_time(SURVEY, iter(rounds))
    found = explored((await read(tmp_path)).state)
    assert found.read == ("src/app.py (whole)", "docs/auth.md (whole)", "src/auth/session.py (whole)")
    assert [one.path for one in found.statements] == ["src/app.py", "docs/auth.md", "src/auth/session.py"]
    assert "not shown, for room" in between(sent(fake_provider, SURVEY)[0], "material")


@pytest.mark.asyncio
async def test_a_repository_too_large_to_list_is_read_by_way_of_a_folder(tmp_path, monkeypatch, fake_provider) -> None:
    """Past the cap the scout is shown folders and no file. It lists a folder, the survey names a file it then
    sees, and the file is read: the way every reading of a large repository goes."""
    monkeypatch.setattr(context, "TREE_MAX_PATHS", 2)
    fake_provider.answers_when(SCOUT, {"files": [], "folders": ["src/auth"], "searches": [], "reason": "Sign-in."})
    fake_provider.answers_each_time(SURVEY, iter([survey(files=("src/auth/session.py",)), survey(SESSION)]))
    run = await read(tmp_path)
    found = explored(run.state)
    (scout,) = sent(fake_provider, SCOUT)
    assert "too many to list" in between(scout, "tree") and "src/auth/session.py" not in between(scout, "tree")
    assert "=== src/auth/ (1 file)\nsrc/auth/session.py" in between(sent(fake_provider, SURVEY)[0], "material")
    assert found.read == ("src/auth/session.py (whole)",) and [one.path for one in found.statements] == [
        SESSION["file"]
    ]


# The review: a model reads the statements a reading kept, and no file.


def reviewed(*, disputed=(), unknown=(), files: tuple[str, ...] = ()) -> dict:
    return {
        "disputed": [{"statement": n, "reason": "Its quote is from another function."} for n in disputed],
        "unknown": [{"question": q, "where": w} for q, w in unknown],
        "more_files": list(files),
        "more_folders": [],
        "more_searches": [],
    }


@pytest.mark.asyncio
@pytest.mark.usefixtures("fake_provider")
async def test_a_kept_statement_carries_the_line_that_opens_its_block(tmp_path) -> None:
    found = explored((await read(tmp_path)).state)
    assert [(one.path, one.line, one.within) for one in found.statements] == [("src/app.py", 2, "def login():")]


@pytest.mark.asyncio
async def test_the_review_reads_the_statements_and_no_file(tmp_path, fake_provider) -> None:
    await read(tmp_path)
    (review,) = sent(fake_provider, REVIEW)
    numbered = between(review, "statements")
    assert numbered.startswith("1. touches src/app.py:2\n   in: def login():\n   Sign-in is decided here.")
    assert "   > return password()" in numbered and "=== src/app.py" not in review


@pytest.mark.asyncio
async def test_a_disputed_statement_is_left_out_and_counted_and_a_number_naming_nothing_is_ignored(
    tmp_path, fake_provider
) -> None:
    fake_provider.answers_when(
        SCOUT, {"files": ["src/app.py", "docs/auth.md"], "folders": [], "searches": [], "reason": "."}
    )
    fake_provider.answers_when(SURVEY, survey(APP, DOCS))
    fake_provider.answers_when(REVIEW, reviewed(disputed=(2, 9)))
    found = explored((await read(tmp_path)).state)
    assert [one.path for one in found.statements] == ["src/app.py"] and found.disputed == 1 and found.dropped == 0


@pytest.mark.asyncio
async def test_unknowns_are_kept_plain_and_at_most_eight(tmp_path, fake_provider) -> None:
    asked = [(f"Who owns sessions?\x1b[31m {n}", "the API\nrepository") for n in range(10)]
    fake_provider.answers_when(REVIEW, reviewed(unknown=asked))
    found = explored((await read(tmp_path)).state)
    assert len(found.unknown) == explore.UNKNOWN_BUDGET == 8 and found.unknown_over == 2
    assert found.unknown[0] == ("Who owns sessions? [31m 0", "the API repository")


@pytest.mark.asyncio
async def test_the_review_may_send_the_reading_one_round_further_and_runs_twice_at_most(
    tmp_path, fake_provider
) -> None:
    fake_provider.answers_each_time(SURVEY, iter([survey(APP), survey(DOCS)]))
    first = reviewed(unknown=[("How long does a session last?", "docs")], files=("docs/auth.md",))
    second = reviewed(unknown=[("Where is a session ended?", "src/auth")], files=("src/auth/session.py",))
    fake_provider.answers_each_time(REVIEW, iter([first, second]))
    found = explored((await read(tmp_path)).state)
    assert len(sent(fake_provider, REVIEW)) == explore.REVIEW_BUDGET == 2
    assert found.read == ("src/app.py (whole)", "docs/auth.md (whole)"), "what the second review asked is not read"
    assert [one.path for one in found.statements] == ["src/app.py", "docs/auth.md"]
    assert found.unknown == (("Where is a session ended?", "src/auth"),), "the second review's unknowns stand"


@pytest.mark.asyncio
async def test_a_reading_is_at_most_seven_model_calls(tmp_path, fake_provider) -> None:
    many = {**FILES, **{f"src/m{n}.py": f"VALUE_{n} = {n}\n" for n in range(8)}}
    rounds = [survey(APP, files=("src/m0.py",)), survey(files=("src/m1.py",)), survey(files=("src/m2.py",))]
    fake_provider.answers_each_time(SURVEY, iter([*rounds, survey(files=("src/m4.py",))]))
    fake_provider.answers_each_time(REVIEW, iter([reviewed(files=("src/m3.py",)), reviewed(files=("src/m5.py",))]))
    await read(tmp_path, many)
    assert len(fake_provider.requests) == 7, "one scout, four surveys, two reviews"


@pytest.mark.asyncio
async def test_a_review_that_fails_keeps_what_was_kept_and_ends_the_run(tmp_path, fake_provider) -> None:
    fake_provider.answers_when(REVIEW, "not json")
    run = await read(tmp_path)
    assert run.state[FAILURE].startswith("review:") and [one.path for one in explored(run.state).statements] == [
        "src/app.py"
    ]


@pytest.mark.asyncio
async def test_a_reading_that_kept_nothing_is_not_reviewed(tmp_path, fake_provider) -> None:
    fake_provider.answers_when(SURVEY, survey())
    await read(tmp_path)
    assert sent(fake_provider, REVIEW) == []


@pytest.mark.asyncio
async def test_a_review_that_disputes_every_statement_may_look_again(tmp_path, fake_provider) -> None:
    """Found by an outside review: where the review disputed all and asked for more, nothing more was read."""
    fake_provider.answers_each_time(SURVEY, iter([survey(APP), survey(DOCS)]))
    fake_provider.answers_each_time(REVIEW, iter([reviewed(disputed=(1,), files=("docs/auth.md",)), reviewed()]))
    found = explored((await read(tmp_path)).state)
    assert len(sent(fake_provider, SURVEY)) == 2 and [one.path for one in found.statements] == ["docs/auth.md"]


@pytest.mark.asyncio
async def test_a_statement_quoting_an_installed_library_is_kept(tmp_path, fake_provider) -> None:
    """Phase 15: a reading may look into the project's installed libraries, offline, at the versions it runs; a
    statement about one counts where its quote is in the library's file, as for code."""
    repository(tmp_path, {".gitignore": ".venv/\n", "src/app.py": "import httpx\n"})
    python_environment(tmp_path)
    fake_provider.answers_when(
        SCOUT, {"files": ["python:httpx/_client.py"], "folders": [], "searches": [], "reason": "Its timeout."}
    )
    quoted = {"kind": "exists", "file": "python:httpx/_client.py", "quote": "timeout=5.0", "note": "Five seconds."}
    fake_provider.answers_when(SURVEY, survey(quoted))
    held = Source.of(tmp_path, exclude=(), installed=True)
    seed = {BRIEF_TEXT: "# Time out slow calls\n", DELTAS_TEXT: "", RULES_TEXT: "", TREE: held.tree()}
    run = await run_seeded(build_explore_app(source=held, ledger=UsageLedger()), state=seed, prompt="explore")
    found = explored(run.state)
    assert [(one.path, one.line) for one in found.statements] == [("python:httpx/_client.py", 2)]
    (scout,) = sent(fake_provider, SCOUT)
    assert "httpx 0.28.1" in between(scout, "tree") and "python:<path>" in scout, "the scout is told how to name one"
    assert "worth a file only where the change depends on how it behaves" in scout, "and when one is worth a file"


@pytest.mark.asyncio
async def test_the_survey_and_the_review_are_shown_the_libraries_they_may_ask_for(tmp_path, fake_provider) -> None:
    """Found live, phase 15: the review named the unknown, how httpx sets its timeout, and could not ask to read it:
    only the scout was shown the installed libraries."""
    repository(tmp_path, {".gitignore": ".venv/\n", "src/app.py": "import httpx\n"})
    python_environment(tmp_path)
    held = Source.of(tmp_path, exclude=(), installed=True)
    seed = {BRIEF_TEXT: "# Time out slow calls\n", DELTAS_TEXT: "", RULES_TEXT: "", TREE: held.tree()}
    await run_seeded(build_explore_app(source=held, ledger=UsageLedger()), state=seed, prompt="explore")
    for opening in (SURVEY, REVIEW):
        (told,) = sent(fake_provider, opening)[:1]
        assert "httpx 0.28.1" in told and "python:<path>" in told, opening


@pytest.mark.asyncio
async def test_the_searches_and_folders_a_reading_made_are_said(tmp_path, fake_provider) -> None:
    """Phase 18: a search and a folder listing were shown to the survey and never said in what was read."""
    asks = {"statements": [APP], "more_files": [], "more_folders": ["src/auth"], "more_searches": ["password"]}
    fake_provider.answers_each_time(SURVEY, iter([asks, survey(SESSION)]))
    found = explored((await read(tmp_path)).state)
    assert any(one.startswith("search: password (") for one in found.looked)
    assert any(one.startswith("src/auth/ (") for one in found.looked)


@pytest.mark.asyncio
async def test_a_review_naming_one_unknown_twice_keeps_it_once(tmp_path, fake_provider) -> None:
    """Found by phase 18's code review: a question named twice took two of the eight places."""
    asked = [("Who owns sessions?", ""), *((f"Q{n}?", "") for n in range(8)), ("Who owns sessions?", "src")]
    fake_provider.answers_when(REVIEW, reviewed(unknown=asked))
    found = explored((await read(tmp_path)).state)
    assert found.unknown[0] == ("Who owns sessions?", "src"), "first named stays first, with where it may be answered"
    assert len(found.unknown) == 8 and found.unknown_over == 1


@pytest.mark.asyncio
async def test_the_scout_is_shown_the_files_the_code_graph_ranks_first(tmp_path, fake_provider) -> None:
    """A hint beside the tree, never in its place (the owner, 27 November 2026)."""
    from adk_spec.orchestration.stages import RANKED

    await read(tmp_path, extra={RANKED: "- src/app.py: defines `login`"})
    (scout,) = sent(fake_provider, SCOUT)
    assert between(scout, "ranked") == "- src/app.py: defines `login`" and "src/auth/session.py" in between(
        scout, "tree"
    )


@pytest.mark.asyncio
async def test_the_review_is_given_the_leads_the_code_graph_finds(tmp_path, fake_provider) -> None:
    """The owner: the graph finds what the reading missed, and the review, which reads it, confirms each or not."""
    from adk_spec.orchestration.stages import RANKED_PATHS

    fake_provider.answers_when(SURVEY, survey({**APP, "note": "`Session.close` ends it here."}))
    await read(tmp_path, extra={RANKED_PATHS: ["src/auth/session.py", "src/app.py"]})
    (review,) = sent(fake_provider, REVIEW)
    assert between(review, "leads") == (
        "- Ranked first for this change, and not read: src/auth/session.py\n"
        "- Statement 1 names `Session.close`, which the code defines nowhere"
    )
