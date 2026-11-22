"""`[verify] test`: the person's own test command, found on PATH or by its absolute path, run with a timeout, and
the end of its output kept, scrubbed of secret shapes."""

from __future__ import annotations

import sys

from adk_spec.workspace import git, process
from adk_spec.workspace.tests import TAIL_MAX_CHARS, run_tests


def program(tmp_path, body: str) -> list[str]:
    """A small Python program, run by this interpreter's absolute path."""
    script = tmp_path / "check.py"
    script.write_text(body, encoding="utf-8")
    return [sys.executable, str(script)]


def test_a_passing_run(tmp_path) -> None:
    run = run_tests(tmp_path, program(tmp_path, "print('all green')"), timeout=60)
    assert run.passed and run.outcome == "passed" and "all green" in run.tail


def test_a_failing_run_says_its_exit_code(tmp_path) -> None:
    run = run_tests(tmp_path, program(tmp_path, "import sys\nprint('boom')\nsys.exit(3)"), timeout=60)
    assert not run.passed and run.outcome == "failed (exit 3)" and "boom" in run.tail


def test_a_run_past_its_time_is_stopped_and_fails(tmp_path) -> None:
    run = run_tests(tmp_path, program(tmp_path, "import time\nprint('started', flush=True)\ntime.sleep(60)"), timeout=1)
    assert not run.passed and run.outcome == "timed out after 1 s" and run.seconds < 20 and "started" in run.tail


def test_a_program_not_found_or_named_by_a_relative_path_is_not_run(tmp_path) -> None:
    """A program is found on PATH's absolute entries, or named by its absolute path: never in a folder relative to
    where the run happens, which a repository's own files could fill."""
    missing = run_tests(tmp_path, ["no-such-test-runner-anywhere"], timeout=5)
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin/tool").write_text("#!/bin/sh\necho ran\n", encoding="utf-8")
    (tmp_path / "bin/tool").chmod(0o755)
    relative = run_tests(tmp_path, ["bin/tool"], timeout=5)
    assert missing.outcome.startswith("not run: ") and not missing.passed
    assert relative.outcome.startswith("not run: ") and "ran" not in relative.tail


def test_only_the_end_of_a_long_output_is_kept(tmp_path) -> None:
    run = run_tests(tmp_path, program(tmp_path, "print('x' * 200_000)\nprint('THE END')"), timeout=60)
    assert len(run.tail) <= TAIL_MAX_CHARS and run.tail.rstrip().endswith("THE END")


def test_a_secret_the_tests_print_is_scrubbed(tmp_path) -> None:
    key = "AKIA" + "IOSFODNN7EXAMPLE"
    run = run_tests(tmp_path, program(tmp_path, f"print('aws_key = {key}')"), timeout=60)
    assert key not in run.tail and "[REDACTED" in run.tail


def test_git_finds_and_starts_its_programs_through_the_one_module() -> None:
    assert git.on_path is process.on_path
