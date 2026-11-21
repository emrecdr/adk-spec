"""Every model call a command makes is kept under `.spec/runs/`: what was sent, what came back, and how the command
ended. A recording is what a stage is later measured on, and what a fake replays."""

from __future__ import annotations

import pytest
from conftest import on_the_fake, run, seeded

from adk_spec.workspace.config import ConfigError
from adk_spec.workspace.files import read_text, write_text
from adk_spec.workspace.layout import Workspace
from adk_spec.workspace.runs import listed, read

REQUEST = "Let users sign in with a passkey."
DELTAS = "You write the requirement deltas"
LIMITS = '[project]\ndefault_tier = "lean"\n\n[limits]\n'


@pytest.fixture(autouse=True)
def _fake_arm(monkeypatch) -> None:
    on_the_fake(monkeypatch)


def kept(root) -> list:
    return [read(path) for path in listed(Workspace.find(root))]


def test_each_call_is_recorded_with_what_was_sent_and_what_came_back(tmp_path, fake_provider) -> None:
    seeded(tmp_path)
    fake_provider.answers_each_time(DELTAS, iter(["not json", None]))
    assert run(tmp_path, "propose", REQUEST, "--id", "kept") == 0
    (held,) = kept(tmp_path)
    assert (held.command, held.change, held.outcome, held.model) == ("propose", "kept", "written", "fake on gemini")
    assert [call.stage for call in held.calls] == ["triage", "brief", "deltas", "deltas"]
    assert held.calls[2].answer == "not json" and held.calls[2].findings is None
    assert "did not fit its schema" in held.calls[3].findings, "what the gate told the stage is kept beside the call"
    assert REQUEST in held.calls[0].instruction and held.calls[0].tokens == 120


@pytest.mark.usefixtures("fake_provider")
def test_a_run_refused_at_the_ceiling_is_recorded_and_writes_nothing_else(tmp_path) -> None:
    seeded(tmp_path)
    write_text(tmp_path / ".spec/config.toml", LIMITS + "max_tokens = 200\n")
    assert run(tmp_path, "propose", REQUEST, "--id", "capped") == 3
    (held,) = kept(tmp_path)
    assert held.outcome.startswith("failed: deltas: CEILING") and held.change == "capped"
    assert [call.stage for call in held.calls] == ["triage", "brief", "deltas"]
    assert held.calls[-1].answer is None, "the call was refused before it was sent"
    assert not (tmp_path / ".spec/changes/capped").exists()


def test_a_providers_error_is_kept_in_its_own_words(tmp_path, fake_provider) -> None:
    seeded(tmp_path)
    fake_provider.raises_when(DELTAS, RuntimeError("the provider fell over"))
    assert run(tmp_path, "propose", REQUEST, "--tier", "lean", "--id", "broken") == 3
    (held,) = kept(tmp_path)
    assert held.outcome.startswith("failed:") and "the provider fell over" in held.calls[-1].error


def test_an_interrupted_run_is_recorded_too(tmp_path, fake_provider) -> None:
    seeded(tmp_path)
    fake_provider.raises_when(DELTAS, KeyboardInterrupt())
    with pytest.raises(KeyboardInterrupt):
        run(tmp_path, "propose", REQUEST, "--tier", "lean", "--id", "stopped")
    (held,) = kept(tmp_path)
    assert held.outcome == "interrupted" and [call.stage for call in held.calls] == ["brief", "deltas"]


def test_a_recording_is_ignored_by_git_and_holds_no_key(tmp_path, monkeypatch, fake_provider) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "a-secret-key-value")
    seeded(tmp_path)
    assert run(tmp_path, "propose", REQUEST, "--tier", "lean", "--id", "kept") == 0
    (path,) = listed(Workspace.find(tmp_path))
    assert read_text(tmp_path / ".spec/runs/.gitignore") == "*\n"
    assert "a-secret-key-value" not in read_text(path) and len(fake_provider.requests) == 2


def test_only_the_newest_runs_are_kept(tmp_path, fake_provider) -> None:
    seeded(tmp_path)
    write_text(tmp_path / ".spec/config.toml", LIMITS + "keep_runs = 2\n")
    for name in ("one", "two", "three"):
        assert run(tmp_path, "propose", REQUEST, "--tier", "lean", "--id", name) == 0
    assert [held.change for held in kept(tmp_path)] == ["three", "two"]
    assert len(fake_provider.requests) == 6


def test_keeping_no_runs_writes_none(tmp_path, fake_provider) -> None:
    seeded(tmp_path)
    write_text(tmp_path / ".spec/config.toml", LIMITS + "keep_runs = 0\n")
    assert run(tmp_path, "propose", REQUEST, "--tier", "lean", "--id", "unkept") == 0
    assert not (tmp_path / ".spec/runs").exists() and len(fake_provider.requests) == 2


@pytest.mark.parametrize("value", ["-1", '"many"', "1.5", "true"])
def test_a_number_of_runs_that_is_none_is_refused_by_name(tmp_path, value) -> None:
    ws = seeded(tmp_path)
    write_text(tmp_path / ".spec/config.toml", LIMITS + f"keep_runs = {value}\n")
    with pytest.raises(ConfigError, match="keep_runs"):
        ws.config()


def test_plan_is_recorded_under_its_change(tmp_path, fake_provider) -> None:
    seeded(tmp_path)
    assert run(tmp_path, "plan", "passkeys", "--replace") == 0
    (held,) = kept(tmp_path)
    assert (held.command, held.change, held.outcome) == ("plan", "passkeys", "written")
    assert [call.stage for call in held.calls] == ["tasks"] and len(fake_provider.requests) == 1


def test_a_recording_replays_to_the_same_files(tmp_path, fake_provider) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    seeded(first)
    fake_provider.answers_each_time(DELTAS, iter(["not json", None]))
    assert run(first, "propose", REQUEST, "--id", "kept") == 0
    (recorded,) = kept(first)
    fake_provider.clear()
    fake_provider.answers_from(recorded)
    seeded(second)
    assert run(second, "propose", REQUEST, "--id", "kept") == 0
    for file in ("brief.md", "specs/auth/spec.md"):
        assert read_text(second / ".spec/changes/kept" / file) == read_text(first / ".spec/changes/kept" / file)
    (again,) = kept(second)
    assert [(c.stage, c.answer) for c in again.calls] == [(c.stage, c.answer) for c in recorded.calls]


def test_init_ignores_the_lock(tmp_path) -> None:
    assert read_text(Workspace.init(tmp_path).home / ".gitignore") == ".lock\n"
