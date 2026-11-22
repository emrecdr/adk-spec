"""`adk-spec init` in an existing repository: the tree made, then the code read by the reading of phases 6 and 7, a
profile of the repository written, and the rules already true of the code drafted into the template constitution."""

from __future__ import annotations

import pytest
from conftest import on_the_fake, repository, run

from adk_spec.domain.secrets import scrub_lines
from adk_spec.workspace.files import read_text, write_text
from adk_spec.workspace.layout import CONSTITUTION_TEXT

SCOUT, SURVEY = "You choose what to read", "You read parts of a repository's code"
REVIEW = "You review what a reading of a repository's code found"
FILES = {
    "src/app.py": "def login(user):\n    return password(user)\n",
    "tests/test_app.py": "def test_login():\n    assert login('a')\n",
}
CONVENTION = {
    "kind": "convention",
    "file": "tests/test_app.py",
    "quote": "def test_login():",
    "note": "Each module has a test in tests/.",
}
PROFILE, RULES = ".spec/profile.md", ".spec/constitution.md"


@pytest.fixture(autouse=True)
def _fake_arm(monkeypatch) -> None:
    on_the_fake(monkeypatch)


def survey(*statements: dict) -> dict:
    return {"statements": list(statements), "more_files": [], "more_folders": [], "more_searches": []}


def reads_the_tests(fake_provider) -> None:
    fake_provider.answers_when(SCOUT, {"files": ["tests/test_app.py"], "folders": [], "searches": [], "reason": "."})
    fake_provider.answers_when(SURVEY, survey(CONVENTION))


def test_init_reads_the_code_writes_the_profile_and_drafts_the_rules(tmp_path, capsys, fake_provider) -> None:
    repository(tmp_path, FILES)
    reads_the_tests(fake_provider)
    assert run(tmp_path, "init") == 0
    out = capsys.readouterr().out
    assert [line.split()[0] for line in out.splitlines()] == ["made", "reading", "explored", "wrote", "drafted", "next"]
    assert "wrote     .spec/profile.md\n" in out
    assert "drafted   1 rule into .spec/constitution.md: keep, edit or delete each\n" in out
    assert read_text(tmp_path / PROFILE).startswith("# This repository\n\nRead from the repository at commit ")
    constitution = read_text(tmp_path / RULES)
    assert constitution.startswith(CONSTITUTION_TEXT.rstrip("\n")) and "\n## Drafted from the code\n" in constitution
    assert "- Each module has a test in tests/. (`tests/test_app.py:1`: def test_login():)\n" in constitution


@pytest.mark.usefixtures("fake_provider")
def test_init_says_what_it_will_spend_before_it_reads(tmp_path, capsys) -> None:
    repository(tmp_path, FILES)
    assert run(tmp_path, "init") == 0
    (reading,) = [line for line in capsys.readouterr().out.splitlines() if line.startswith("reading")]
    assert "up to 7 model calls" in reading and "--no-explore skips it" in reading


def test_no_explore_and_no_repository_read_nothing(tmp_path, capsys, fake_provider) -> None:
    repository(tmp_path / "repo", FILES)
    assert run(tmp_path / "repo", "init", "--no-explore") == 0
    (tmp_path / "plain").mkdir()
    assert run(tmp_path / "plain", "init") == 0
    assert fake_provider.requests == [] and not (tmp_path / "repo" / PROFILE).exists()
    assert (tmp_path / "plain/.spec").is_dir() and "init --refresh" in capsys.readouterr().out


def test_no_model_ready_makes_the_tree_and_says_how_to_read_later(tmp_path, capsys, monkeypatch, fake_provider) -> None:
    repository(tmp_path, FILES)
    monkeypatch.delenv("GOOGLE_API_KEY")
    assert run(tmp_path, "init") == 0
    out = capsys.readouterr().out
    assert (tmp_path / ".spec").is_dir() and "not read" in out and "init --refresh" in out
    assert fake_provider.requests == [] and read_text(tmp_path / RULES) == CONSTITUTION_TEXT


def test_refresh_rewrites_the_profile_and_never_the_constitution(tmp_path, fake_provider) -> None:
    repository(tmp_path, FILES)
    reads_the_tests(fake_provider)
    assert run(tmp_path, "init") == 0
    mine = "# Constitution\n\nVersion: 1\n\nEvery change ships with a test.\n"
    write_text(tmp_path / RULES, mine)
    write_text(tmp_path / PROFILE, "# This repository\n\nWritten by hand.\n")
    assert run(tmp_path, "init", "--refresh") == 0
    assert read_text(tmp_path / RULES) == mine
    assert "Written by hand." not in read_text(tmp_path / PROFILE) and "Each module has a test" in read_text(
        tmp_path / PROFILE
    )


def test_refresh_where_there_is_no_workspace_is_refused(tmp_path, capsys, fake_provider) -> None:
    repository(tmp_path, FILES)
    assert run(tmp_path, "init", "--refresh") == 2
    assert ".spec" in capsys.readouterr().err and not (tmp_path / ".spec").exists() and fake_provider.requests == []


def test_a_reading_that_keeps_nothing_writes_no_profile(tmp_path, capsys, fake_provider) -> None:
    repository(tmp_path, FILES)
    fake_provider.answers_when(SURVEY, survey())
    assert run(tmp_path, "init") == 0
    assert "explored  nothing: " in capsys.readouterr().out
    assert not (tmp_path / PROFILE).exists() and read_text(tmp_path / RULES) == CONSTITUTION_TEXT


def test_a_reading_that_ends_early_writes_a_partial_profile(tmp_path, fake_provider) -> None:
    repository(tmp_path, FILES)
    reads_the_tests(fake_provider)
    fake_provider.answers_when(REVIEW, "not json")
    assert run(tmp_path, "init") == 0
    assert "This reading is partial: review:" in read_text(tmp_path / PROFILE)


def test_a_secret_reaches_neither_the_profile_nor_a_rule(tmp_path, fake_provider) -> None:
    key = "AKIA" + "IOSFODNN7EXAMPLE"
    config = f'AWS_KEY = "{key}"\nTIMEOUT = 30\n'
    repository(tmp_path, {**FILES, "config.py": config})
    shown = scrub_lines(config)[0].split("\n")[0]
    fake_provider.answers_when(SCOUT, {"files": ["config.py"], "folders": [], "searches": [], "reason": "."})
    convention = {"kind": "convention", "file": "config.py", "quote": shown, "note": "Keys are set in config.py."}
    fake_provider.answers_when(SURVEY, survey(convention))
    assert run(tmp_path, "init") == 0
    profile, constitution = read_text(tmp_path / PROFILE), read_text(tmp_path / RULES)
    assert key not in profile and key not in constitution and "[REDACTED" in constitution
