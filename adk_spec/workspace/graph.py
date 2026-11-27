"""The code graph a reading has beside the code: codegraph's (shared with adk-review), built from this repository's
Python files as a reading may be shown them, scrubbed, a key's file withheld.

The owner, 27 November 2026: use it to cross-check, to validate and to improve the output, never as the only source of
truth about the code. So what it ranks is a hint beside the tree of paths, and what it finds is a lead a stage confirms
by reading: files ranked for a request that no round read, the tests that import the files a reading found, and a
member a statement names that its class defines nowhere. Ranking is adk-spec's own policy, kept here on top of the
graph's facts: adk-review ranks nothing."""

from __future__ import annotations

import builtins
import contextlib
import math
import re
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path

from codegraph import Graph, Symbol, build, store
from codegraph.extract import PYTHON
from codegraph.model import stem_of
from codegraph.words import words_of

from ..domain.model import Statement
from ..domain.text import counted, first_of

#: As many files as one round of the reading reads.
RANKED_SHOWN = 12
#: The files a plan is told the reach of, and how many importers and tests of each are named.
REACH_FILES = 8
REACH_NAMED = 5
#: How many names a ranked file's reason gives, and how many undefined members the review is told of.
NAMES_SAID = 3
UNDEFINED_SAID = 8
#: Past this much Python a repository gets no graph, and its reading runs as before: measured, reading, scrubbing and
#: parsing cost about 0.4 s a megabyte, all before the first model call.
GRAPH_MAX_BYTES = 10_000_000
#: Words a request is full of and a name seldom holds, adk-spec's own template words among them: as the rarest, they
#: would weigh the most (the code review of phase 29: "change" and "request" ranked `Change` first for every request).
_COMMON = frozenset(
    [
        "a",
        "add",
        "all",
        "also",
        "an",
        "and",
        "any",
        "are",
        "as",
        "at",
        "be",
        "by",
        "can",
        "change",
        "changes",
        "each",
        "every",
        "for",
        "from",
        "given",
        "has",
        "in",
        "into",
        "is",
        "it",
        "its",
        "make",
        "must",
        "new",
        "no",
        "not",
        "of",
        "on",
        "one",
        "only",
        "or",
        "request",
        "requested",
        "shall",
        "should",
        "so",
        "that",
        "the",
        "then",
        "there",
        "this",
        "to",
        "use",
        "was",
        "what",
        "when",
        "which",
        "who",
        "will",
        "with",
    ]
)
_MEMBER = re.compile(r"`([A-Z]\w*)\.([A-Za-z_]\w*)`")
#: Each repository's graph, built once a command however many sources ask: by its root and its Python files.
_BUILT: dict[tuple[str, tuple[str, ...]], Graph] = {}


def built(paths: Iterable[str], lines: Callable[[str], list[str] | str], *, commit: str) -> Graph:
    """The graph of the Python files among `paths`, each as `lines` gives it, which is how a reading may show it: a file
    `lines` will not give (a key's, a link, past what a reading reads) is no part of it. `commit` labels what it was
    built from."""
    sources: dict[str, str] = {}
    for path in paths:
        if path.endswith(PYTHON) and isinstance(held := lines(path), list):
            sources[path] = "\n".join(held)
    return build(sources, commit=commit)


def kept(graph: Graph, root: Path) -> Graph:
    """`graph`, kept in `<root>/.codegraph/` too, where every tool looks: the owner asked that each tool use the same
    generated graph. It is a hint for another tool, so a write that fails changes nothing here and says nothing."""
    with contextlib.suppress(store.StoreError):
        store.save(graph, root)
    return graph


def shared(root: str, paths: Sequence[str], make: Callable[[], Graph]) -> Graph:
    """The graph of the repository at `root`, made once a command: a plan that read the code asks for the one its
    reading built (the code review of phase 29: it was built twice). The last two are kept."""
    key = (root, tuple(paths))
    if key not in _BUILT:
        while len(_BUILT) >= 2:
            _BUILT.pop(next(iter(_BUILT)))
        _BUILT[key] = make()
    return _BUILT[key]


def empty() -> Graph:
    return build({}, commit="none")


def ranked(graph: Graph, text: str, limit: int = RANKED_SHOWN) -> list[tuple[str, str]]:
    """The files to read first for `text`, each with why: by the rare words of the request that the names they define
    share, then on through their imports, by a personalised PageRank kept near those files. With no `text`, the most
    imported files, which `init`'s reading is shown. Tests are left out: their names are sentences, and measured on
    adk-spec they outweighed the code in every request's matches."""
    tests = {file.path for file in graph.files if file.test}
    if not text.strip():
        return _hubs(graph, tests, limit)
    names = _matched(graph, text, tests)
    if not names:
        return []
    seeds = {path: held[0][0] for path, held in names.items()}
    scores = _pagerank(graph, seeds)
    order = sorted(
        (path for path, score in scores.items() if score > 0 and path not in tests),
        key=lambda one: (-round(scores[one], 9), one),
    )
    return [(path, _reason(graph, path, names, seeds)) for path in order[:limit]]


def ranked_text(found: Sequence[tuple[str, str]]) -> str:
    """The ranked files as a stage is shown them, a line each."""
    return "\n".join(f"- {path}: {reason}" for path, reason in found)


def reach_text(graph: Graph, paths: Sequence[str]) -> str:
    """For each of the first files a reading found, what imports it and the tests that import it: leads for the tasks,
    which keep the importers working and run those tests. A test matched by its name alone is left out, as a task's
    check would rest on the graph alone. A file with neither is left out."""
    known = {file.path for file in graph.files if file.parsed}
    tests = {file.path for file in graph.files if file.test}
    lines = []
    for path in [one for one in dict.fromkeys(paths) if one in known][:REACH_FILES]:
        said = []
        if users := graph.importers(path):
            said.append(f"imported by {first_of(users, REACH_NAMED)}")
        if testing := [one for one in graph.importers(path, tests=True) if one in tests]:
            said.append(f"tested by {first_of(testing, REACH_NAMED)}")
        if said:
            lines.append(f"- {path}: {'; '.join(said)}")
    return "\n".join(lines)


def undefined(graph: Graph, statements: Sequence[Statement]) -> list[tuple[int, str]]:
    """Each `Class.member` a statement's note names where the class is this repository's and neither it nor a base it
    inherits defines the member, with the statement's number: a lead for the review, which may dispute it. Only that
    form: measured by the code review of phase 29, any other backticked name (an attribute, a parameter, a file) read as
    defined nowhere. A risk is left out, as it may name what is missing."""
    classes: dict[str, list[Symbol]] = {}
    for symbol in graph.symbols:
        if symbol.kind == "class":
            classes.setdefault(symbol.qualname.rsplit(".", 1)[-1], []).append(symbol)
    found: list[tuple[int, str]] = []
    for number, one in enumerate(statements, 1):
        for cls, member in [] if one.kind == "risk" else dict.fromkeys(_MEMBER.findall(one.note)):
            if cls in classes and member not in vars(builtins) and not _member_of(graph, classes[cls], member):
                found.append((number, f"{cls}.{member}"))
    return found[:UNDEFINED_SAID]


def _member_of(graph: Graph, held: Sequence[Symbol], member: str) -> bool:
    """Whether any class of that name, or a base it inherits from this repository, defines `member`."""
    todo, seen = [one.id for one in held], set()
    while todo:
        if (cls := todo.pop()) in seen:
            continue
        seen.add(cls)
        path, _, qualname = cls.partition("::")
        if any(one.path == path and one.qualname == f"{qualname}.{member}" for one in graph.symbols):
            return True
        todo += [base for base in graph.parents(cls) if "::" in base]
    return False


def _matched(graph: Graph, text: str, tests: set[str]) -> dict[str, list[tuple[float, str]]]:
    """Each file's names that share words with `text`, best first, each scored by how rare its shared words are among
    the code's names: a smoothed inverse document frequency, so a word every name holds still counts a little. A
    section's heading is left out, as adk-spec writes its own around a request, and the words of its own title are
    common ones; so is a dunder, `__init__`, which is Python's name, not the code's, and matched "init" in every
    request saying it."""
    held = [
        (symbol, set(words_of(symbol.qualname)) | set(words_of(stem_of(symbol.path))))
        for symbol in graph.symbols
        if symbol.path not in tests and not _dunder(symbol.qualname.rsplit(".", 1)[-1])
    ]
    spread = Counter(word for _symbol, words in held for word in words)
    said = "\n".join(line for line in text.split("\n") if not line.lstrip().startswith("##"))  # a title counts
    wanted = set(words_of(said)) - _COMMON
    names: dict[str, list[tuple[float, str]]] = {}
    for symbol, words in held:
        if shared_words := wanted & words:
            score = math.fsum(math.log(1 + len(held) / spread[word]) for word in sorted(shared_words))
            names.setdefault(symbol.path, []).append((round(score, 9), symbol.qualname))
    return {path: sorted(found, key=lambda one: (-one[0], one[1])) for path, found in names.items()}


def _reason(graph: Graph, path: str, names: Mapping[str, list[tuple[float, str]]], seeds: Mapping[str, float]) -> str:
    if path in names:
        return "defines " + ", ".join(f"`{name}`" for _score, name in names[path][:NAMES_SAID])
    near = [one.target for one in graph.imports if one.local and one.path == path and one.target in seeds]
    if near:
        return f"imports {min(near)}"
    return f"imported by {counted(len(graph.importers(path)), 'file')}"


def _hubs(graph: Graph, tests: set[str], limit: int) -> list[tuple[str, str]]:
    """The files most files import, each with how many: a package's `__init__.py`, run on the way to what it holds, is
    no hub of its own."""
    counts = {
        file.path: len(graph.importers(file.path))
        for file in graph.files
        if file.parsed and file.path not in tests and stem_of(file.path) != "__init__"
    }
    order = sorted((path for path, count in counts.items() if count), key=lambda one: (-counts[one], one))
    return [(path, f"imported by {counted(counts[path], 'file')}") for path in order[:limit]]


def _pagerank(
    graph: Graph, seeds: Mapping[str, float], *, damping: float = 0.5, iterations: int = 30
) -> dict[str, float]:
    """A walk that follows imports, both ways, and restarts at `seeds` by weight. It restarts often (0.5), so the rank
    stays near the files the request named: measured on adk-spec, the file asked about stood a place or more higher
    than at the usual 0.85. Fixed iterations and sorted orders, so the same answer every time, on every system."""
    links: dict[str, dict[str, float]] = {}
    for one in graph.imports:
        if one.local:
            for source, target, weight in ((one.path, one.target, 1.0), (one.target, one.path, 0.5)):
                held = links.setdefault(source, {})
                held[target] = held.get(target, 0.0) + weight
    nodes = sorted(file.path for file in graph.files)
    total = math.fsum(seeds[one] for one in sorted(seeds))
    restart = {node: seeds.get(node, 0.0) / total for node in nodes}
    out = {node: math.fsum(links.get(node, {}).values()) for node in nodes}
    adjacent = {node: sorted(links.get(node, {}).items()) for node in nodes}
    rank = dict(restart)
    for _ in range(iterations):
        dangling = math.fsum(rank[node] for node in nodes if not out[node])
        step = {node: (1 - damping + damping * dangling) * restart[node] for node in nodes}
        for node in nodes:
            for target, weight in adjacent[node]:
                step[target] += damping * rank[node] * weight / out[node]
        rank = step
    return rank


def _dunder(name: str) -> bool:
    return name.startswith("__") and name.endswith("__")
