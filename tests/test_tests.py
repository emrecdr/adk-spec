"""`[verify] test`: the person's own test command, found on PATH or by its absolute path, run with a timeout, and
the end of its output kept, scrubbed of secret shapes."""

from __future__ import annotations

import os
import signal
import sys
import time

import pytest

from adk_spec.workspace import process, tests
from adk_spec.workspace.tests import CUT_MARK, TAIL_MAX_CHARS, run_tests


def program(tmp_path, body: str) -> list[str]:
    """A small Python program, run by this interpreter's absolute path."""
    script = tmp_path / "check.py"
    script.write_text(body, encoding="utf-8")
    return [sys.executable, str(script)]


def test_a_passing_run(tmp_path) -> None:
    run = run_tests(tmp_path, program(tmp_path, "print('all green')"), timeout=60)
    assert run.outcome == "passed" and "all green" in run.tail and CUT_MARK not in run.tail


def test_a_failing_run_says_its_exit_code(tmp_path) -> None:
    run = run_tests(tmp_path, program(tmp_path, "import sys\nprint('boom')\nsys.exit(3)"), timeout=60)
    assert run.outcome == "failed (exit 3)" and "boom" in run.tail


def test_a_run_past_its_time_is_stopped_and_fails(tmp_path) -> None:
    run = run_tests(tmp_path, program(tmp_path, "import time\nprint('started', flush=True)\ntime.sleep(60)"), timeout=1)
    assert (
        run.outcome == "timed out after 1 s" and run.seconds is not None and run.seconds < 20 and "started" in run.tail
    )


def test_a_program_not_found_or_named_by_a_relative_path_is_not_run(tmp_path) -> None:
    """A program is found on PATH's absolute entries, or named by its absolute path: never in a folder relative to
    where the run happens, which a repository's own files could fill."""
    missing = run_tests(tmp_path, ["no-such-test-runner-anywhere"], timeout=5)
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin/tool").write_text("#!/bin/sh\necho ran\n", encoding="utf-8")
    (tmp_path / "bin/tool").chmod(0o755)
    relative = run_tests(tmp_path, ["bin/tool"], timeout=5)
    assert missing.outcome.startswith("not run: ") and missing.seconds is None
    assert relative.outcome.startswith("not run: ") and "ran" not in relative.tail


def test_only_the_end_of_a_long_output_is_kept(tmp_path) -> None:
    run = run_tests(tmp_path, program(tmp_path, "print('x' * 200_000)\nprint('THE END')"), timeout=60)
    assert len(run.tail) <= TAIL_MAX_CHARS and run.tail.rstrip().endswith("THE END")
    assert run.tail.startswith(CUT_MARK), "phase 18: verify was given the end with no mark of the cut"


def test_a_secret_the_tests_print_is_scrubbed(tmp_path) -> None:
    key = "AKIA" + "IOSFODNN7EXAMPLE"
    run = run_tests(tmp_path, program(tmp_path, f"print('aws_key = {key}')"), timeout=60)
    assert key not in run.tail and "[REDACTED" in run.tail


def test_a_run_past_its_time_is_not_held_by_a_process_that_left_its_session(tmp_path, monkeypatch) -> None:
    """A test that starts a server in a session of its own leaves it holding the output: waited for with no limit,
    it kept verify waiting as long as the server lived."""
    monkeypatch.setattr(process, "DRAIN_S", 0.5)  # the wait is bounded all the same (the audit of 25 November, A8)
    code = (
        "import subprocess, sys, time\n"
        "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'], start_new_session=True)\n"
        "print('started', flush=True)\n"
        "time.sleep(60)"
    )
    run = run_tests(tmp_path, program(tmp_path, code), timeout=1)
    assert run.outcome == "timed out after 1 s" and run.seconds is not None and run.seconds < 15
    assert "started" in run.tail, "what it wrote before it was stopped is kept"


POSIX = pytest.mark.skipif(os.name == "nt", reason="a process tree is stopped by taskkill on Windows")


def gone(pid_file, *, within: float = 5.0) -> bool:
    """Whether the process whose ID `pid_file` holds has ended, waiting a little for it."""
    pid = int(pid_file.read_text(encoding="utf-8"))
    end = time.monotonic() + within
    while time.monotonic() < end:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.1)
    return False


LEFT_RUNNING = (
    "import subprocess, sys\n"
    "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'],"
    " stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
    "open('child.pid', 'w').write(str(child.pid))\n"
)


@POSIX
def test_a_run_that_passed_leaves_nothing_running(tmp_path) -> None:
    run = run_tests(tmp_path, program(tmp_path, LEFT_RUNNING + "print('done')"), timeout=30)
    assert run.outcome == "passed" and gone(tmp_path / "child.pid")


def test_a_run_is_judged_by_its_own_exit_while_a_child_holds_its_output(tmp_path) -> None:
    code = (
        "import subprocess, sys\n"
        "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(6)'])\n"
        "print('done', flush=True)\n"
    )
    run = run_tests(tmp_path, program(tmp_path, code), timeout=3)
    assert run.outcome == "passed" and "done" in run.tail


@POSIX
def test_an_interrupt_stops_the_run_and_what_it_started(tmp_path) -> None:
    def interrupted(*_args) -> None:
        raise KeyboardInterrupt

    previous = signal.signal(signal.SIGALRM, interrupted)
    signal.setitimer(signal.ITIMER_REAL, 1.5)
    try:
        with pytest.raises(KeyboardInterrupt):
            run_tests(tmp_path, program(tmp_path, LEFT_RUNNING + "import time\ntime.sleep(37)"), timeout=60)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
    assert gone(tmp_path / "child.pid")


def test_only_a_window_of_a_never_ending_output_is_held(tmp_path) -> None:
    code = "import sys\nfor n in range(200):\n    sys.stdout.write('x' * 10_000 + '\\n')\nprint('THE END')"
    kept = process.run_kept(program(tmp_path, code), env=os.environ, timeout=60, keep=4_000)
    assert len(kept.output) <= 4_000 and kept.output.rstrip().endswith(b"THE END") and kept.cut


def test_a_batch_file_is_never_run(tmp_path, monkeypatch) -> None:
    """Windows runs a .cmd or .bat through cmd.exe, which reads its words again: `&` and `%VAR%` would act."""
    batch = tmp_path / "npm.cmd"
    batch.write_text("@echo ran\n", encoding="utf-8")
    monkeypatch.setattr(tests, "on_path", lambda _name, _path=None: str(batch))
    run = run_tests(tmp_path, ["npm", "test"], timeout=5)
    assert run.outcome.startswith("not run: npm") and "cmd.exe" in run.outcome and run.seconds is None


def test_output_that_holds_a_private_key_is_withheld_whole(tmp_path) -> None:
    """pytest writes `E   ` before each line of a failure: the key's shape is no longer one the scrub knows."""
    head, foot = "-----BEGIN " + "PRIVATE KEY-----", "-----END " + "PRIVATE KEY-----"
    lines = [head, "MIIEvQIBADANBgkqhkiG9w0BAQEFAASC", "AgEAAoIBAQC7VJTUt9Us8cKjMzEfYyji", foot]
    code = "\n".join(f"print('E       {line}')" for line in lines)
    run = run_tests(tmp_path, program(tmp_path, code), timeout=60)
    assert "MIIEvQ" not in run.tail and "private key" in run.tail


def test_a_value_cut_off_by_the_stop_is_scrubbed(tmp_path) -> None:
    code = 'import sys, time\nsys.stdout.write("password = \'abc123secret")\nsys.stdout.flush()\ntime.sleep(30)'
    run = run_tests(tmp_path, program(tmp_path, code), timeout=1)
    assert run.outcome == "timed out after 1 s" and "abc123secret" not in run.tail


def test_a_cut_window_starts_at_a_whole_line() -> None:
    assert tests._from_a_line("half-token\nwhole\n", cut=True) == "whole\n"
    assert tests._from_a_line("whole\n", cut=False) == "whole\n"


def test_a_run_is_given_the_persons_environment_not_adk_specs_own(tmp_path, monkeypatch) -> None:
    """Measured live: run from its checkout by `uv run`, adk-spec's own virtual environment stood first on PATH and in
    VIRTUAL_ENV, and a plain `pytest` would have been adk-spec's, not the project's."""
    own, project = tmp_path / "adk-spec/.venv", tmp_path / "project"  # adk-spec's own, outside the project
    (own / "bin").mkdir(parents=True)
    project.mkdir()
    monkeypatch.setattr(sys, "prefix", str(own))
    monkeypatch.setattr(sys, "base_prefix", "/usr")
    monkeypatch.setenv("VIRTUAL_ENV", str(own))
    monkeypatch.setenv("PATH", os.pathsep.join([str(own / "bin"), os.environ["PATH"]]))
    code = "import os\nprint('venv', os.environ.get('VIRTUAL_ENV'))\nprint('path', os.environ['PATH'])"
    run = run_tests(project, program(tmp_path, code), timeout=60)
    assert "venv None" in run.tail and str(own / "bin") not in run.tail


def test_a_virtual_environment_beside_the_project_in_a_monorepo_is_kept(tmp_path, monkeypatch) -> None:
    """Found by the review: a `.venv` at the top of a monorepo, `.spec/` in one service below it, was stripped."""
    own, project = tmp_path / "mono/.venv", tmp_path / "mono/services/api"
    (own / "bin").mkdir(parents=True)
    project.mkdir(parents=True)
    monkeypatch.setattr(sys, "prefix", str(own))
    monkeypatch.setattr(sys, "base_prefix", "/usr")
    monkeypatch.setenv("VIRTUAL_ENV", str(own))
    monkeypatch.setenv("PATH", os.pathsep.join([str(own / "bin"), os.environ["PATH"]]))
    code = "import os\nprint('venv', os.environ.get('VIRTUAL_ENV'))"
    assert f"venv {own}" in run_tests(project, program(tmp_path, code), timeout=60).tail


def test_a_virtual_environment_inside_the_project_is_the_projects_own_and_is_kept(tmp_path, monkeypatch) -> None:
    """Found by the cleanup review: adk-spec installed in the project's own `.venv` took the project's pytest away."""
    own = tmp_path / ".venv"
    (own / "bin").mkdir(parents=True)
    monkeypatch.setattr(sys, "prefix", str(own))
    monkeypatch.setattr(sys, "base_prefix", "/usr")
    monkeypatch.setenv("VIRTUAL_ENV", str(own))
    monkeypatch.setenv("PATH", os.pathsep.join([str(own / "bin"), os.environ["PATH"]]))
    code = "import os\nprint('venv', os.environ.get('VIRTUAL_ENV'))\nprint('path', os.environ['PATH'])"
    run = run_tests(tmp_path, program(tmp_path, code), timeout=60)
    assert f"venv {own}" in run.tail and str(own / "bin") in run.tail


def test_on_windows_a_run_that_ended_is_not_stopped_again(tmp_path, monkeypatch) -> None:
    """Found by an outside review: taskkill finds a tree by its root, so after a normal exit it stopped nothing."""
    stopped = []
    monkeypatch.setattr(process, "WINDOWS", True)
    monkeypatch.setattr(process, "_stopped", lambda _proc, windows: stopped.append(windows))
    monkeypatch.setattr(process, "DRAIN_S", 0.2)  # its stop is a stand-in: the run is not waited out (A8)
    run_tests(tmp_path, program(tmp_path, "print('ok')"), timeout=60)
    assert stopped == []
    run_tests(tmp_path, program(tmp_path, "import time\ntime.sleep(2)"), timeout=0.5)
    assert stopped == [True], "a run past its time is stopped, on Windows too"


def test_a_path_entry_that_cannot_be_resolved_is_kept_as_it_was(tmp_path) -> None:
    """Found by an outside review: an entry `resolve` cannot read, as an unmounted drive on Windows, stopped verify."""
    assert tests._not_own("/a\0b", tmp_path / ".venv")


def test_a_program_that_ended_and_was_waited_for_is_not_stopped(monkeypatch) -> None:
    """Found by review: its number may already be another process's, which a stop would end."""
    stopped = []
    monkeypatch.setattr(process, "_stopped", lambda _proc, windows: stopped.append(windows))
    started = process.started([sys.executable, "-c", "pass"], env=os.environ)
    process.waited(started, 60)
    process.stop(started)
    assert stopped == []


def test_the_tests_are_not_given_the_keys_adk_spec_read_from_its_own_env_file(tmp_path, monkeypatch) -> None:
    """Found by the third audit: `verify` loaded the checkout's `.env` into its own environment, and handed it whole
    to the project's test command, code an agent may just have written: the provider's key with it. A variable the
    person's shell set stays, since `.env` never overrides one."""
    monkeypatch.setenv("FROM_THE_SHELL", "kept")
    code = "import os\nprint('file', os.environ.get('FROM_THE_FILE'))\nprint('shell', os.environ.get('FROM_THE_SHELL'))"
    monkeypatch.setenv("FROM_THE_FILE", "a key")
    run = run_tests(tmp_path, program(tmp_path, code), timeout=60, without=frozenset({"FROM_THE_FILE"}))
    assert "file None" in run.tail and "shell kept" in run.tail


def test_the_cli_says_which_variables_its_env_file_added(tmp_path, monkeypatch) -> None:
    """What `verify` keeps from the tests: the names `.env` added, never one the shell had set."""
    from adk_spec.interfaces import cli

    env = tmp_path / ".env"
    env.write_text("FROM_THE_FILE=a key\nFROM_THE_SHELL=from the file\n", encoding="utf-8")
    monkeypatch.setenv("FROM_THE_SHELL", "kept")
    monkeypatch.delenv("FROM_THE_FILE", raising=False)
    try:
        assert cli._loaded(env) == {"FROM_THE_FILE"} and os.environ["FROM_THE_SHELL"] == "kept"
    finally:
        os.environ.pop("FROM_THE_FILE", None)
