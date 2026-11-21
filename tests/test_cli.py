"""The `adk-spec` command, run in process: what it prints, what it writes and how it exits."""

from __future__ import annotations

import pytest

from adk_spec.interfaces.cli import main


def test_version_names_the_package_and_its_version(capsys) -> None:
    with pytest.raises(SystemExit) as stopped:
        main(["--version"])
    assert stopped.value.code == 0 and capsys.readouterr().out.strip() == "adk-spec 0.1.0"


def test_a_usage_error_ends_by_naming_help(capsys) -> None:
    with pytest.raises(SystemExit) as stopped:
        main(["--no-such-flag"])
    assert stopped.value.code == 2 and "--help lists every" in capsys.readouterr().err
