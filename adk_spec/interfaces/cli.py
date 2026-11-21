"""The `adk-spec` command. `main` is a function of its arguments and returns the exit code; `run` is the process
boundary, which sets the console's encoding once and turns Ctrl-C into a sentence.

Nothing heavy is imported at the top: a handler imports the engine inside itself, so `--version`, a usage error and
every command that calls no model start without it.
"""

from __future__ import annotations

import argparse
import sys
from importlib import metadata
from typing import NoReturn

EXIT_OK = 0
#: A gate refused, or findings at the bar.
EXIT_FINDINGS = 1
#: A usage or configuration error, before anything is spent.
EXIT_USAGE = 2
#: The engine or the provider failed.
EXIT_ENGINE = 3
EXIT_INTERRUPTED = 130

PROG = "adk-spec"


class _Parser(argparse.ArgumentParser):
    """argparse's, its every error ending with where to look next."""

    def error(self, message: str) -> NoReturn:
        super().error(f"{message}\n{PROG}: --help lists every command and flag")


def _parser() -> argparse.ArgumentParser:
    parser = _Parser(prog=PROG, description="Spec-driven development on Google ADK.")
    parser.add_argument("--version", action="version", version=f"{PROG} {metadata.version('adk-spec')}")
    return parser


def main(argv: list[str]) -> int:
    parser = _parser()
    parser.parse_args(argv)
    parser.print_help()
    return EXIT_USAGE


def run() -> int:
    """The process boundary of the installed `adk-spec`."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")  # a Windows console is not UTF-8 by default
    try:
        return main(sys.argv[1:])
    except KeyboardInterrupt:
        print(f"{PROG}: interrupted", file=sys.stderr)
        return EXIT_INTERRUPTED
