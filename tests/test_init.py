"""`adk-spec init` in an existing repository: the tree made, then the code read by the reading of phases 6 and 7, a
profile of the repository written, and the rules already true of the code drafted into the template constitution."""

from __future__ import annotations

import pytest
from conftest import on_the_fake, repository, run

from adk_spec.domain.secrets import scrub_lines
from adk_spec.orchestration.explore import MAX_CALLS
from adk_spec.workspace.files import read_text, write_text
from adk_spec.workspace.layout import CONSTITUTION_TEXT
from adk_spec.workspace.skill import SKILL_PARTS

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
    said = [line.split()[0] for line in out.splitlines()]
    # The skill, then the reading; the unset test command said before the next step (U8).
    assert said == ["made", "wrote", "reading", "explored", "wrote", "drafted", "tests", "next"], out
    assert "wrote     .spec/profile.md\n" in out
    assert "drafted   1 rule into .spec/constitution.md: keep, edit or delete each\n" in out
    assert read_text(tmp_path / PROFILE).startswith("# This repository\n\nRead from the repository at commit ")
    constitution = read_text(tmp_path / RULES)
    assert constitution.startswith(CONSTITUTION_TEXT.rstrip("\n")) and "\n## Drafted from the code\n" in constitution
    assert "- Each module has a test in tests/. (`tests/test_app.py:1`: `def test_login():`)\n" in constitution


@pytest.mark.usefixtures("fake_provider")
def test_init_says_what_it_will_spend_before_it_reads(tmp_path, capsys) -> None:
    repository(tmp_path, FILES)
    assert run(tmp_path, "init") == 0
    (reading,) = [line for line in capsys.readouterr().out.splitlines() if line.startswith("reading")]
    assert f"up to {MAX_CALLS} model calls" in reading and MAX_CALLS == 7 and "--no-explore skips it" in reading


def test_no_explore_and_no_repository_read_nothing(tmp_path, capsys, fake_provider) -> None:
    repository(tmp_path / "repo", FILES)
    assert run(tmp_path / "repo", "init", "--no-explore") == 0
    (tmp_path / "plain").mkdir()
    assert "init --refresh" in capsys.readouterr().out
    assert run(tmp_path / "plain", "init") == 0
    assert fake_provider.requests == [] and not (tmp_path / "repo" / PROFILE).exists()
    out = capsys.readouterr().out
    assert (tmp_path / "plain/.spec").is_dir() and out.split()[0] == "made"
    assert "refresh" not in out, "outside a repository, a refresh reads nothing either"


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
    profile = read_text(tmp_path / PROFILE)
    assert read_text(tmp_path / RULES) == mine and "Written by hand." not in profile and "Each module has a" in profile


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
    assert read_text(tmp_path / RULES) == CONSTITUTION_TEXT, "no rule from a reading the review did not finish"


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


def test_a_refresh_that_reads_nothing_says_so_in_its_exit_code(tmp_path, monkeypatch, fake_provider) -> None:
    """A first init never fails: the tree is what it owes. A refresh owes the profile."""
    repository(tmp_path, FILES)
    assert run(tmp_path, "init", "--no-explore") == 0
    fake_provider.answers_when(SURVEY, survey())
    assert run(tmp_path, "init", "--refresh") == 3
    monkeypatch.delenv("GOOGLE_API_KEY")
    assert run(tmp_path, "init", "--refresh") == 2


def test_init_inside_another_workspace_is_refused(tmp_path, capsys, fake_provider) -> None:
    repository(tmp_path, FILES)
    assert run(tmp_path, "init", "--no-explore") == 0
    capsys.readouterr()
    assert run(tmp_path / "src", "init") == 2
    assert "init --refresh" in capsys.readouterr().err and not (tmp_path / "src/.spec").exists()
    assert fake_provider.requests == []


def test_a_refresh_drafts_while_the_constitution_is_still_the_template(tmp_path, fake_provider) -> None:
    """A first init made with no model, or with --no-explore, drafted nothing: the refresh every message points to
    drafts, as long as the constitution is still exactly the template."""
    repository(tmp_path, FILES)
    assert run(tmp_path, "init", "--no-explore") == 0
    reads_the_tests(fake_provider)
    assert run(tmp_path, "init", "--refresh") == 0
    assert "\n## Drafted from the code\n" in read_text(tmp_path / RULES)


def test_refresh_with_no_explore_writes_what_needs_no_model_and_reads_nothing(tmp_path, capsys, fake_provider) -> None:
    """Found by the fourth audit and the skill's code review: a workspace made before the skill could be given it
    only by a reading, which called a model and rewrote the profile."""
    repository(tmp_path, FILES)
    assert run(tmp_path, "init", "--no-explore") == 0
    (tmp_path / SKILL).unlink()
    capsys.readouterr()
    assert run(tmp_path, "init", "--refresh", "--no-explore") == 0
    said = capsys.readouterr().out
    assert f"wrote     {SKILL}" in said and "reading" not in said and fake_provider.requests == []


def test_init_asks_for_the_whole_repository_and_for_conventions_as_rules(tmp_path, fake_provider) -> None:
    """Measured live: the profile leaned on the newest feature, and most drafted rules were descriptions."""
    from conftest import between

    repository(tmp_path, FILES)
    assert run(tmp_path, "init") == 0
    (scout,) = [
        str(r.config.system_instruction)
        for r in fake_provider.requests
        if str(r.config.system_instruction).startswith(SCOUT)
    ]
    brief = " ".join(between(scout, "brief").split())
    assert "the whole repository, not one feature of it" in brief
    assert "as a rule new code must follow" in brief and "one sentence" in brief


# The Agent Skill: how an assistant uses adk-spec, read by GitHub Copilot and Claude Code from the repository.
SKILL = "/".join(SKILL_PARTS)


def test_init_writes_a_skill_an_assistant_reads_in_the_form_the_standard_asks(tmp_path, capsys) -> None:
    """The owner's choice, 23 November 2026, after the third audit: `init` writes an Agent Skill, which both GitHub
    Copilot and Claude Code read from `.claude/skills/`, so an assistant knows how to use adk-spec with nothing set up.
    The form is agentskills.io's: a name that is its folder's, lowercase and hyphens, and a description of 1,024
    characters at most."""
    repository(tmp_path, FILES)
    assert run(tmp_path, "init", "--no-explore") == 0
    assert f"wrote     {SKILL}" in capsys.readouterr().out
    text = read_text(tmp_path / SKILL)
    head, _, body = text.removeprefix("---\n").partition("\n---\n")
    fields = dict(line.split(": ", 1) for line in head.splitlines())
    assert fields["name"] == SKILL_PARTS[2] == "adk-spec"
    assert 0 < len(fields["description"]) <= 1024
    for said in ("adk-spec status", "--no-input", "tasks.md", "- [x]", "adk-spec approve", "--override"):
        assert said in body, said


def test_a_refresh_keeps_a_skill_a_person_edited_and_says_so(tmp_path, capsys) -> None:
    """The skill is the person's once they edit it: a refresh keeps it, in one line (the audit of 25 November, C3)."""
    assert run(tmp_path, "init", "--no-explore") == 0
    write_text(tmp_path / SKILL, read_text(tmp_path / SKILL) + "Mine.\n")
    capsys.readouterr()
    assert run(tmp_path, "init", "--refresh", "--no-explore") == 0
    assert read_text(tmp_path / SKILL).endswith("Mine.\n")
    assert f"kept      {SKILL}: edited, so the new text was not written" in capsys.readouterr().out


def test_a_refresh_replaces_a_skill_adk_spec_wrote_with_its_text_now(tmp_path, capsys, monkeypatch) -> None:
    """The audit of 25 November (C3): written once, an install never had a better skill. A text adk-spec shipped is
    known by its hash, and replaced; nothing is written into the file to know it by."""
    import hashlib

    from adk_spec.workspace import skill

    older = "---\nname: adk-spec\ndescription: an older text\n---\n"
    monkeypatch.setattr(skill, "SHIPPED", skill.SHIPPED | {hashlib.sha256(older.encode()).hexdigest()})
    assert run(tmp_path, "init", "--no-explore") == 0
    write_text(tmp_path / SKILL, older)
    capsys.readouterr()
    assert run(tmp_path, "init", "--refresh", "--no-explore") == 0
    assert read_text(tmp_path / SKILL) == skill.SKILL_TEXT and f"replaced  {SKILL}" in capsys.readouterr().out
    assert run(tmp_path, "init", "--refresh", "--no-explore") == 0
    assert SKILL not in capsys.readouterr().out, "the text it has now is said no more"


def test_every_skill_text_adk_spec_wrote_is_known_by_its_hash() -> None:
    """Change the skill's text, and add its new hash: every one shipped stays, so a refresh knows each as its own."""
    import hashlib

    from adk_spec.workspace.skill import SHIPPED, SKILL_TEXT

    assert hashlib.sha256(SKILL_TEXT.encode()).hexdigest() in SHIPPED and len(SHIPPED) >= 4


def test_the_skill_is_no_part_of_the_code_a_reading_or_verify_sees(tmp_path) -> None:
    """Found by the code review: written untracked, the skill was listed with the repository's code, so a reading
    could take its rules for the code's own, and `verify` judged it as new work. A skill of the person's still is."""
    from adk_spec.workspace.git import diff, files

    base = repository(tmp_path, FILES)
    assert run(tmp_path, "init", "--no-explore") == 0
    write_text(tmp_path / ".claude/skills/release/SKILL.md", "---\nname: release\ndescription: mine\n---\n")
    listed = files(tmp_path, exclude=())
    assert SKILL not in listed and ".claude/skills/release/SKILL.md" in listed
    assert "adk-spec/SKILL.md" not in diff(tmp_path, base, exclude=())


def test_a_refresh_writes_the_skill_where_a_workspace_made_before_it_has_none(tmp_path, capsys, fake_provider) -> None:
    repository(tmp_path, FILES)
    reads_the_tests(fake_provider)
    assert run(tmp_path, "init", "--no-explore") == 0
    (tmp_path / SKILL).unlink()
    capsys.readouterr()
    assert run(tmp_path, "init", "--refresh") == 0
    assert (tmp_path / SKILL).is_file() and f"wrote     {SKILL}" in capsys.readouterr().out


def test_init_says_no_test_command_is_set_until_one_is(tmp_path, capsys) -> None:
    """The audit of 25 November (U8): `verify` said so only after the work was done, its verdicts then resting on the
    diff alone."""
    assert run(tmp_path, "init", "--no-explore") == 0
    assert "tests     none named: set [verify] test in .spec/config.toml\n" in capsys.readouterr().out


def test_init_says_nothing_of_the_test_command_once_one_is_set(tmp_path, capsys) -> None:
    """Found by the code review of phase 22: only the unset case was held."""
    assert run(tmp_path, "init", "--no-explore") == 0
    config = tmp_path / ".spec/config.toml"
    config.write_text(config.read_text(encoding="utf-8") + '\n[verify]\ntest = ["pytest"]\n', encoding="utf-8")
    capsys.readouterr()
    assert run(tmp_path, "init", "--refresh", "--no-explore") == 0
    assert "tests     none named" not in capsys.readouterr().out


def test_init_with_a_config_that_does_not_read_still_ends_with_its_next_step(tmp_path, capsys) -> None:
    """Found by the code review of phase 22: asking the config for its test command stopped a refresh at its end."""
    assert run(tmp_path, "init", "--no-explore") == 0
    config = tmp_path / ".spec/config.toml"
    config.write_text(config.read_text(encoding="utf-8").replace("[project]", "[project]\nbogus = 1"), encoding="utf-8")
    capsys.readouterr()
    assert run(tmp_path, "init", "--refresh", "--no-explore") == 0
    assert "next      " in capsys.readouterr().out
