"""Read-only git, run as a program and never through a shell.

Ported from the reference project's collector (`adk_review/collect/git.py`): the part that starts git, and nothing
of what it gathers. What that project measured, each before it was fixed, is why each rule is here:

- Git is started by its full path, found among PATH's absolute entries. Windows looks in the current folder first,
  and the current folder can be the checkout being read, whose own `git.exe` must never run.
- Its environment is the caller's with every `GIT_*` variable left out, and no config but the repository's own and
  what is fixed here. `GIT_DIR` read another repository under the requested folder's name; `GIT_DIFF_OPTS=-u0` took
  every context line out of a diff; a person's `core.fsmonitor` started a program beside a diff.
- Every call has a timeout. On Windows `git.exe` runs the real git as its child, which holds the output open, so
  the whole process tree is stopped before the output is read to its end.

Only verbs that read are used here, and `GIT_OPTIONAL_LOCKS=0` keeps even those from refreshing the index.
"""

from __future__ import annotations

import functools
import os
from collections.abc import Sequence
from pathlib import Path

from .layout import ROOT_NAME
from .process import Completed, TimedOut, on_path, run

#: How long one git command may run, in seconds.
GIT_TIMEOUT_S: float = 30
#: What a stage may be given of a diff, in characters. A diff past it is refused, never cut: half a diff would be
#: judged as the whole.
DIFF_MAX_CHARS = 200_000
#: Past this many files that git neither tracks nor ignores, a diff is refused: a virtual environment or a build
#: folder nobody ignored would be read file by file as new work.
UNTRACKED_MAX = 500
#: Settings that change what git prints, reads or runs, fixed for every call. Set through the environment, they
#: outrank every config file, the repository's own included.
_SETTLED = {
    "core.fsmonitor": "false",
    "core.attributesFile": os.devnull,
    "core.autocrlf": "input",
    "core.quotePath": "false",
    "core.precomposeUnicode": "false",
    "diff.suppressBlankEmpty": "false",
    "diff.noprefix": "false",  # a diff's paths are read by their `a/` and `b/`
    "diff.mnemonicPrefix": "false",
}
_PLAIN = ("--no-color", "--no-ext-diff", "--no-textconv", "-M")
#: The folder's own files, without this package's tree: a pathspec git reads from the folder it runs in.
_HERE = ("--", ".", f":(exclude){ROOT_NAME}")


class GitError(Exception):
    """git could not answer: a reason to say, never an empty answer to read."""


def _environment(root: Path, trust: bool = True) -> dict[str, str]:
    env = {name: value for name, value in os.environ.items() if not name.startswith("GIT_")}
    env |= {"LC_ALL": "C", "LANGUAGE": ""}  # git's messages as written, whatever the person's language
    env |= {"GIT_NO_LAZY_FETCH": "1", "GIT_NO_REPLACE_OBJECTS": "1", "GIT_OPTIONAL_LOCKS": "0"}
    env |= {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_ATTR_NOSYSTEM": "1"}
    env |= {"GIT_TERMINAL_PROMPT": "0"}
    # With a person's own config unread, so is their list of safe folders: the repository adk-spec runs in is
    # trusted, whoever owns it. Git asks about the repository's top, not about the folder a command runs in. Another
    # repository a change names is not: git's own check of who owns it holds, so on a shared machine another
    # account's repository is not opened, and nothing of its config runs.
    settled = dict(_SETTLED)
    if trust:
        settled["safe.directory"] = Path(os.path.realpath(top(root))).as_posix()
    # And so is the file of what they ignore in every repository, which is read and passed on: without it a `.env`
    # or an editor's folder they never see in `git status` would be read as new work.
    if ignored := _excludes(
        os.environ.get("HOME", ""), os.environ.get("USERPROFILE", ""), os.environ.get("XDG_CONFIG_HOME", "")
    ):
        settled |= {"core.excludesFile": ignored}
    env["GIT_CONFIG_COUNT"] = str(len(settled))
    for at, (key, value) in enumerate(settled.items()):
        env[f"GIT_CONFIG_KEY_{at}"], env[f"GIT_CONFIG_VALUE_{at}"] = key, value
    return env


def top(root: Path) -> Path:
    """The top of the repository `root` is in, found without asking git: the nearest folder at or above it that
    holds `.git`. `root` itself where none does."""
    return next((folder for folder in (root, *root.parents) if (folder / ".git").exists()), root)


@functools.cache
def _excludes(*_homes: str) -> str | None:
    """The file of patterns a person ignores in every repository, as their own git config names it, or nothing.
    Asked of git once for each home the process has had: the one setting of a person's config this layer reads."""
    program = on_path("git")
    if program is None:
        return None
    env = {name: value for name, value in os.environ.items() if not name.startswith("GIT_")}
    argv = [program, "config", "--global", "--type=path", "--get", "core.excludesFile"]
    try:
        done = run(argv, env=env | {"LC_ALL": "C"}, timeout=GIT_TIMEOUT_S)
    except OSError, TimedOut:
        return None
    return done.stdout.decode("utf-8", "replace").strip() or None


def _called(root: Path, *args: str, trust: bool = True) -> Completed[bytes]:
    """One git command in `root`, run to its end whatever its code. `GitError` where git is not found, cannot
    start, or does not answer in time."""
    verb = _verb(args)
    program = on_path("git")
    if program is None:  # Git for Windows can be installed for Git Bash alone
        raise GitError("git is not on PATH. Install git, with its folder among PATH's absolute entries")
    try:
        return run([program, "-C", str(root), *args], env=_environment(root, trust), timeout=GIT_TIMEOUT_S)
    except TimedOut:
        raise GitError(f"git {verb} did not answer within {GIT_TIMEOUT_S:g} s") from None
    except OSError as exc:  # found, and still could not start
        raise GitError(f"git {verb} could not start: {exc.strerror or exc}") from None


def _verb(args: tuple[str, ...]) -> str:
    return next((arg for arg in args if not arg.startswith("-")), "")


def _refusal(done: Completed[bytes]) -> str:
    """Why git refused, in its own first line. Its advice (`hint: ...`) comes first at times, and is never the
    reason."""
    said = done.stderr.decode("utf-8", "replace").split("\n")
    lines = [line.strip() for line in said if line.strip() and not line.startswith("hint:")]
    return lines[0] if lines else f"exit {done.returncode}"


def git(root: Path, *args: str, ok: tuple[int, ...] = (0,), trust: bool = True) -> str:
    """One git command in `root`: its output as text. `GitError` where git is not found, does not answer in time,
    or ends with a code outside `ok`, with git's own first line as the reason. `trust` off for a repository other
    than the one adk-spec runs in."""
    done = _called(root, *args, trust=trust)
    if done.returncode not in ok:
        raise GitError(f"git {_verb(args)} failed: {_refusal(done)}")
    return done.stdout.decode("utf-8", "replace")


def _answered(root: Path, *args: str, no: tuple[int, ...] = (), trust: bool = True) -> str | None:
    """A question git answers with its output, or with no: an exit code of `no`, or its refusal where `root` is in
    no repository at all. Any other refusal is raised, never read as a no: a repository git will not open, say for
    whose it is, is there."""
    done = _called(root, *args, trust=trust)
    if done.returncode == 0:
        return done.stdout.decode("utf-8", "replace").strip()
    why = _refusal(done)
    if done.returncode in no or "not a git repository" in why:
        return None
    raise GitError(f"git {_verb(args)} failed: {why}")


def is_repository(root: Path, *, trust: bool = True) -> bool:
    """Whether `root` is inside a git work tree."""
    return _answered(root, "rev-parse", "--is-inside-work-tree", trust=trust) == "true"


def resolves(root: Path, ref: str, *, trust: bool = True) -> str | None:
    """The full ID of the commit `ref` names in `root`, or nothing where it names none. A name that starts with a
    hyphen is an option to git and a revision to nobody."""
    if not ref or ref.startswith("-"):
        return None
    return _answered(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}", no=(1,), trust=trust) or None


def head(root: Path, *, trust: bool = True) -> str | None:
    """The commit checked out in `root`, or nothing: no repository, or no commit yet."""
    return resolves(root, "HEAD", trust=trust)


def _here(exclude: Sequence[str]) -> tuple[str, ...]:
    """What limits a git command to the files under the folder it runs in: none of `.spec/`, and none a person
    excluded. Each of `exclude` is read as a `.gitignore` reads the common patterns, and never as less: `as_globs`
    says how. Handed to git as written, `*.pem` kept only the top folder's keys out, and `vendor/**` nothing of a
    `Vendor/` on a system where the two are one folder."""
    return (*_HERE, *(f":(exclude,glob,icase){one}" for one in as_globs(exclude)))


def as_globs(exclude: Sequence[str]) -> tuple[str, ...]:
    """Each of `exclude` as the globs it is read as, from the workspace's root, as `.gitignore` reads it: one with a
    slash before its end, as a path from the root; one with none, or with a slash at its end alone, at any depth;
    either one as a file, or a folder and all it holds. Matched in either case. What git is handed, and what the
    installed libraries are held to, so that one pattern keeps a path out of both. Found by the third audit: `secrets/`
    was taken for a path from the root, and `config/secrets/b.txt` reached every command."""
    globs: list[str] = []
    for pattern in exclude:
        bare = pattern.rstrip("/")
        if not bare:
            continue
        base = bare if "/" in bare else f"**/{bare}"
        globs += [base] if base.endswith("/**") else [base, f"{base}/**"]
    return tuple(globs)


def _listed(root: Path, *which: str, exclude: Sequence[str], trust: bool = True) -> list[str]:
    listed = git(root, "ls-files", "-z", *which, *_here(exclude), trust=trust)
    return sorted(path for path in listed.split("\0") if path)


def files(root: Path, *, exclude: Sequence[str], trust: bool = True) -> list[str]:
    """Every file under `root` that git tracks or would: nothing it ignores, nothing of `.spec/`, and nothing a
    person excluded. Paths from `root`, with forward slashes. `exclude` has no default, here or in any reader of
    the repository: a caller that forgot it would read what a person asked to keep out, and no test would fail."""
    return sorted(set(_listed(root, "--cached", "--others", "--exclude-standard", exclude=exclude, trust=trust)))


#: How many lines of one file a search gives back.
GREP_A_FILE = 5


def grep(root: Path, term: str, *, exclude: Sequence[str], trust: bool = True) -> list[str]:
    """Each `path:line:text` git finds for `term` among the text files it tracks or would track under `root`:
    nothing it ignores, nothing of `.spec/`, nothing a person excluded, and `GREP_A_FILE` lines of a file at most.
    `term` is a fixed string, never a pattern, its letters matched in either case."""
    asked = ("-n", "-I", "-F", "-i", "--untracked", "--no-color", f"--max-count={GREP_A_FILE}", "-e", term)
    return [line for line in git(root, "grep", *asked, *_here(exclude), ok=(0, 1), trust=trust).split("\n") if line]


def diff(root: Path, base: str, *, exclude: Sequence[str], prefix: str = "", trust: bool = True) -> str:
    """`base` against the working tree under `root`, as one unified diff with paths from `root`. A file git does
    not track yet reads as added: new work is new files, and a person may not have added them. `.spec/` is left
    out. `GitError` where `base` names no commit, or too many files are neither tracked nor ignored."""
    commit = resolves(root, base, trust=trust)
    if commit is None:
        raise GitError(f"`{base}` names no commit in {root}")
    # Paths as `a/` and `b/` say, whatever a person's settings say, and under `prefix` for another repository's diff.
    named = (f"--src-prefix=a/{prefix}", f"--dst-prefix=b/{prefix}")
    changed = git(root, "diff", *_PLAIN, *named, "--relative", commit, *_here(exclude), trust=trust)
    new = _listed(root, "--others", "--exclude-standard", exclude=exclude, trust=trust)
    if len(new) > UNTRACKED_MAX:
        raise GitError(
            f"{len(new):,} files under {root} are neither tracked nor ignored. Add them to git, or ignore what is "
            "no source, such as a virtual environment or a build folder"
        )
    added = [
        git(root, "diff", *_PLAIN, *named, "--no-index", "--", "/dev/null", path, ok=(0, 1), trust=trust)
        for path in new
    ]
    return changed + "".join(added)
