"""How often a check or a verification finds what the labelled set plants:
`uv run python -m scripts.measure [--runs N] [--case NAME] [--out FILE]`.

What code finds is found every run. What a model finds varies, so each case is built anew and run N times on the arm
the environment names, and the table says for each planted fault in how many runs it was caught; the blocking
findings on nothing planted, an upper bound on the false ones; the model's findings left out for quoting text that
is not there; and the tokens and the time. A measurement holds for the model it ran on, which the report names
beside this package's commit.

Each run calls a model with the account the environment names. The script says how many calls it is about to make
before the first.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import re
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from adk_spec.domain.context_md import SECTIONS
from adk_spec.domain.convert import pointed_at
from adk_spec.domain.drafts import FindingDraft, FindingsDraft
from adk_spec.domain.text import lines_of, plain
from adk_spec.interfaces import cli
from adk_spec.workspace.files import read_text
from adk_spec.workspace.git import GitError, head
from adk_spec.workspace.layout import CHANGES, CONTEXT, Workspace, findings_of
from adk_spec.workspace.runs import listed, read

from .cases import CASES, Case

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Seen:
    """One thing a run found: a finding of code or of the model, or a verdict."""

    code: str
    path: str
    text: str
    blocking: bool


@dataclass(frozen=True)
class Score:
    caught: int
    missed: int
    false_blocking: int


@dataclass
class Row:
    """One case over its runs."""

    name: str
    command: str
    runs: int
    #: For each planted fault of the case, in how many runs it was caught.
    caught: list[int]
    false_blocking: int = 0
    tokens: int = 0
    seconds: float = 0.0
    #: Runs whose command did not end in a report: a refusal, or the engine's failure.
    failed: int = 0
    #: Each blocking finding that matched nothing planted, in its own words, for a person to read: a false finding,
    #: or a fault nobody planted.
    strays: list[str] = field(default_factory=list)
    #: Each planted fault a run did not catch, with what that run found.
    missed: list[str] = field(default_factory=list)
    #: Each finding of the model's that was left out for quoting text that is not in the file it names: it may be
    #: the planted fault, quoted a word off.
    left_out: list[str] = field(default_factory=list)


def scored(case: Case, seen: list[Seen]) -> Score:
    """What one run's findings are worth against a case: each planted fault caught or missed, and each blocking
    finding that is about nothing planted."""
    caught = sum(any(wanted.met_by(one) for one in seen) for wanted in case.expect)
    stray = sum(one.blocking and not any(wanted.met_by(one) for wanted in case.expect) for one in seen)
    return Score(caught, len(case.expect) - caught, stray)


def observed(case: Case, root: Path, change: str) -> tuple[list[Seen], list[Seen], int, float]:
    """What a run of `case` left: what was found, each of the model's findings that quoted nothing real, and the
    tokens and seconds of its model calls."""
    workspace = Workspace.find(root)
    loaded = workspace.load_change(change)
    kept = [read(path) for path in listed(workspace)]
    passes = ("explore", "plan") if case.command == "plan" else (case.command,)  # a plan reads the code first
    calls = [call for held in kept if held.command in passes for call in held.calls]
    tokens, seconds = sum(call.tokens for call in calls), sum(call.seconds for call in calls)
    if case.command == "plan":
        return _stated(workspace.home / CHANGES / change / CONTEXT), [], tokens, seconds
    if case.command == "verify":
        verdicts = loaded.change.state.verification.verdicts if loaded.change.state.verification else {}
        return [Seen(f"verdict.{verdict}", req, "", False) for req, verdict in verdicts.items()], [], tokens, seconds
    found = findings_of(loaded, workspace.specs()[0])
    seen = [Seen(one.code, one.path or "", one.message, one.severity == "ERROR") for one in found]
    texts = workspace.approval_texts(change)
    left_out: list[Seen] = []
    answer = next((call.answer for call in reversed(calls) if call.answer and not call.error), None)
    for one in _findings(answer):
        code, critical = f"check.{one.kind}", one.severity == "critical"
        if (at := pointed_at(one, texts)) is None:  # the command left this one out, by the same test
            left_out.append(Seen(code, one.file.strip(), f"quoted `{one.quote}`: {one.message}", critical))
        else:  # the quote is kept here beside the message: a planted fault is named by either
            seen.append(Seen(code, at[0], f"{one.quote} {one.message}", critical))
    return seen, left_out, tokens, seconds


#: A statement as `context.md` holds one: the file and the line it rests on, and what it says.
_STATEMENT = re.compile(r"- `(?P<path>[^`]+):\d+` (?P<note>.*)")


def _stated(context: Path) -> list[Seen]:
    """Each statement a reading kept, read back from the `context.md` it wrote: its kind from the heading it
    stands under. None where no file was written."""
    kinds = {heading: kind for kind, heading in SECTIONS}
    seen: list[Seen] = []
    kind = None
    for line in lines_of(read_text(context)) if context.is_file() else ():
        if line.startswith("## "):
            kind = kinds.get(line.removeprefix("## "))
        elif kind and (found := _STATEMENT.fullmatch(line)):
            seen.append(Seen(f"context.{kind}", found["path"], found["note"], False))
    return seen


def _findings(answer: str | None) -> list[FindingDraft]:
    """The findings of a check's last answer, or none: a run that failed its gate ended on an answer off its
    schema, which is counted as a failed run and is nothing to read."""
    try:
        return FindingsDraft.model_validate_json(answer).findings if answer else []
    except ValidationError:
        return []


#: How much of a finding's own words a list under the table keeps.
WORDS_MAX = 400


def _said(run: int, one: Seen) -> str:
    """A finding in its own words, as one line of a list under the table."""
    return f"run {run + 1}: `{one.code}` {plain(one.path)}: {plain(one.text)[:WORDS_MAX]}"


def measured(case: Case, *, runs: int, folder: Path) -> Row:
    """`case` built anew and run `runs` times, each in a folder of its own under `folder`."""
    row = Row(case.name, case.command, runs, [0] * len(case.expect))
    for run in range(runs):
        root = folder / f"{case.name}-{run}"
        root.mkdir(parents=True)
        change = case.build(root)
        quiet = io.StringIO()
        with contextlib.redirect_stdout(quiet), contextlib.redirect_stderr(quiet):
            code = cli.main(["--root", str(root), case.command, change])
        row.failed += code not in (cli.EXIT_OK, cli.EXIT_FINDINGS)
        seen, left_out, tokens, seconds = observed(case, root, change)
        for at, wanted in enumerate(case.expect):
            caught = any(wanted.met_by(one) for one in seen)
            row.caught[at] += caught
            if not caught:
                codes = wanted.codes if isinstance(wanted.codes, str) else " or ".join(wanted.codes)
                found = "; ".join(f"{one.code} on {one.path}" for one in seen) or "nothing"
                row.missed.append(f"run {run + 1}: wanted {codes} on {' or '.join(wanted.paths)}; found {found}")
        row.false_blocking += scored(case, seen).false_blocking
        strays = [one for one in seen if one.blocking and not any(wanted.met_by(one) for wanted in case.expect)]
        row.strays += [_said(run, one) for one in strays]
        row.left_out += [_said(run, one) for one in left_out]
        row.tokens += tokens
        row.seconds += seconds
    return row


def rendered(rows: list[Row], *, model: str, commit: str | None, at: str) -> str:
    """The measurement as a page: what was measured, on what, and a row a case."""
    runs = rows[0].runs if rows else 0
    lines = [
        "# How often the labelled set's faults are caught",
        "",
        f"Measured {at} on {model}, {runs} runs a case, at commit {commit[:12] if commit else 'none'}.",
        "",
        "| Case | Command | Caught | Blocking on nothing planted | Left out, no such quote | Tokens a run "
        "| Seconds a run | Failed |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        caught = ", ".join(f"{times}/{row.runs}" for times in row.caught) or "nothing planted"
        lines.append(
            f"| `{row.name}` | {row.command} | {caught} | {row.false_blocking} | {len(row.left_out)} | "
            f"{row.tokens // row.runs:,} | {row.seconds / row.runs:.1f} | {row.failed} |"
        )
    lines += [
        "",
        "Caught: in how many runs a finding on the planted fault's file named it; one figure a planted fault.",
        "Blocking on nothing planted: blocking findings that match no planted fault, over all runs; an upper bound on",
        "the false ones, since a model may find a real fault nobody planted.",
        "",
    ]
    sections = (
        ("Blocking on nothing planted", "strays"),
        ("Missed", "missed"),
        ("Left out, no such quote", "left_out"),
    )
    for heading, held in sections:
        listed = [f"- `{row.name}`, {said}" for row in rows for said in getattr(row, held)]
        if listed:
            lines += [f"## {heading}", "", *listed, ""]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="measure", description=__doc__)
    parser.add_argument("--runs", type=int, default=3, help="how often each case is run (default 3)")
    parser.add_argument("--case", help="one case of the set, by its name")
    parser.add_argument("--out", type=Path, help="write the report here, where it is otherwise printed")
    args = parser.parse_args(argv)
    cases = [case for case in CASES if args.case in (None, case.name)]
    if not cases:
        print(
            f"measure: no case is named `{args.case}`. The cases: {', '.join(case.name for case in CASES)}",
            file=sys.stderr,
        )
        return 2
    from adk_spec.orchestration.explore import ROLES as READING
    from adk_spec.orchestration.models import require_ready, serving

    cli._load_env()  # the checkout's .env, as the commands read it
    if why := require_ready(roles=("check", "verify", *READING, "design", "tasks")):
        print(f"measure: {why}", file=sys.stderr)
        return 2
    # A case code decides costs no call; a plan reads the code first: a scout, a survey or more, a review, then the
    # tasks.
    calls = args.runs * sum(0 if case.by_code else 4 if case.command == "plan" else 1 for case in cases)
    print(
        f"measuring {len(cases)} cases, {args.runs} runs each, on {serving('check')}: about {calls} model calls",
        flush=True,
    )
    # A file held open on Windows, by a virus scanner say, must not cost the report of calls already paid for.
    with tempfile.TemporaryDirectory(prefix="adk-spec-measure-", ignore_cleanup_errors=True) as folder:
        rows = []
        for case in cases:
            rows.append(measured(case, runs=args.runs, folder=Path(folder)))
            caught = ", ".join(f"{times}/{args.runs}" for times in rows[-1].caught) or "nothing planted"
            print(f"  {case.name}: {caught}", flush=True)
    try:
        commit = head(ROOT)
    except GitError:
        commit = None
    at = datetime.now(UTC).isoformat(timespec="seconds")
    report = rendered(rows, model=serving("check"), commit=commit, at=at)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report, encoding="utf-8", newline="\n")
        print(f"wrote {args.out}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
