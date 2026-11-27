"""The code graph beside the reading: built from what a reading may show, ranked by adk-spec's own policy, and only
ever a hint or a lead a stage confirms by reading (the owner, 27 November 2026: never the only source of truth)."""

from __future__ import annotations

import pytest
from codegraph import build, store
from conftest import _git, repository

from adk_spec.domain.model import Statement
from adk_spec.workspace.graph import ranked, ranked_text, reach_text, undefined
from adk_spec.workspace.source import Source

KEY = "-----BEGIN RSA " + "PRIVATE KEY-----\nMIIEowIBAAKCAQEA7x1yQ9\n"
FILES = {
    "app/__init__.py": "",
    "app/engine.py": "class Engine:\n    def start(self):\n        return 1\n",
    "app/cli.py": "from app.engine import Engine\n\ndef main():\n    return Engine().start()\n",
    "app/web.py": "from app.engine import Engine\n",
    "app/store.py": "def save(record):\n    return record\n",
    "tests/test_engine.py": "from app.engine import Engine\n\ndef test_the_engine_starts_the_run(): pass\n",
}


def test_the_graph_holds_only_what_a_reading_may_show(tmp_path) -> None:
    repository(tmp_path, {**FILES, "app/keys.py": f'KEY = """\n{KEY}"""\n\ndef secret(): pass\n', "docs/a.md": "# A\n"})
    graph = Source.of(tmp_path, exclude=()).graph()
    assert graph is not None
    names = {symbol.id for symbol in graph.symbols}
    assert "app/engine.py::Engine.start" in names and not any(one.startswith("app/keys.py") for one in names)
    assert {file.path for file in graph.files} == set(FILES), "a key's file and a document are no part of it"


def test_files_are_ranked_for_a_request_by_the_names_they_define_with_tests_left_out() -> None:
    found = ranked(build(FILES, commit="c"), "Start the engine on every run")
    assert found[0] == ("app/engine.py", "defines `Engine.start`, `Engine`")
    assert all(not path.startswith("tests/") for path, _reason in found)
    assert "app/store.py" not in dict(found), "a file that shares no word and imports nothing near is not ranked"


def test_a_request_no_name_shares_a_word_with_ranks_nothing() -> None:
    assert ranked(build(FILES, commit="c"), "Write the release notes") == []


def test_with_no_request_the_most_imported_files_come_first() -> None:
    """What `init`'s reading is shown: the hubs, a hint for the profile the model checks."""
    found = ranked(build(FILES, commit="c"), "")
    assert found == [("app/engine.py", "imported by 2 files")]
    assert ranked_text(found) == "- app/engine.py: imported by 2 files"


def test_the_reach_names_who_imports_and_the_tests_that_import_the_files_a_reading_found() -> None:
    """A test matched by its name alone is not named: a task's check would rest on the graph alone."""
    files = {**FILES, "tests/test_store.py": "def test_save(): pass\n"}
    said = reach_text(build(files, commit="c"), ["app/engine.py", "app/store.py", "gone.py"])
    assert said == "- app/engine.py: imported by app/cli.py, app/web.py; tested by tests/test_engine.py"


def test_a_member_its_class_defines_nowhere_is_a_lead_and_no_other_name_is() -> None:
    """Only `Class.member`, where the class is this repository's: any other backticked name (an attribute, a parameter,
    a file) read as defined nowhere (the code review of phase 29). A member a base class defines is defined."""
    files = {**FILES, "app/fast.py": "from app.engine import Engine\n\nclass Fast(Engine):\n    pass\n"}
    note = (
        "`Engine.start` begins it and `Engine.stop` ends it; `Fast.start` is inherited; `self._here`, `change_id`, "
        "`pyproject.toml`, `LlmAgent.run` and `json.loads` are no class's member here"
    )
    statements = [
        Statement(kind="exists", path="app/cli.py", line=1, quote="x", note=note),
        Statement(kind="risk", path="app/cli.py", line=1, quote="x", note="`Engine.gone` may break"),
    ]
    assert undefined(build(files, commit="c"), statements) == [(1, "Engine.stop")]


def test_a_definition_is_read_by_its_file_and_name_and_an_unknown_one_whole(tmp_path) -> None:
    """The graph finds the lines; where it knows no such definition, the file is read whole: it never refuses a read
    (the code review of phase 29)."""
    repository(tmp_path, FILES)
    got = Source.of(tmp_path, exclude=()).gathered(["app/engine.py::Engine.start"], [], [])
    assert got.read == ("app/engine.py (lines 2 to 3 of 3)",)
    assert "    def start(self):\n        return 1" in got.shown and "class Engine" not in got.shown
    got = Source.of(tmp_path, exclude=()).gathered(["app/engine.py::Engine.fly", "gone.py::f"], [], [])
    assert got.read == ("app/engine.py (whole)",) and any(
        "gone.py::f: git lists no such file" in one for one in got.left_out
    )


def test_within_names_the_definition_a_line_stands_in_by_the_files_own_text(tmp_path) -> None:
    """Indentation named the nearest `if`; a person names the function. The code graph named the outer function for a
    closure, and the class for a method under a decorator of several lines (the code review of phase 29)."""
    source = (
        "def decide(user):\n    if user:\n        return password()\n\n"
        "def outer():\n    def inner(x):\n        if x:\n            return x\n    return inner\n\n"
        "class Api:\n    @app.get(\n        '/x',\n    )\n"
        "    def handle(self, x):\n        if x:\n            return x\n"
    )
    repository(tmp_path, {"app/auth.py": source, "notes.txt": "a\n  b\n"})
    held = Source.of(tmp_path, exclude=())
    assert held.within("app/auth.py", 3) == "def decide(user):"
    assert held.within("app/auth.py", 8) == "def inner(x):"
    assert held.within("app/auth.py", 17) == "def handle(self, x):"
    assert held.within("notes.txt", 2) == "a", "no definition: the block it stands in, as before"


def test_a_repository_past_the_cap_gets_no_graph_and_one_graph_serves_a_command(tmp_path, monkeypatch) -> None:
    """Measured by the code review of phase 29: a large tree cost seconds before the first call, and plan built the
    graph twice."""
    from adk_spec.workspace import graph, source

    repository(tmp_path, FILES)
    made = []
    monkeypatch.setattr(
        graph, "build", lambda sources, commit: made.append(len(sources)) or build(sources, commit=commit)
    )
    first, second = Source.of(tmp_path, exclude=()), Source.of(tmp_path, exclude=())
    assert first.graph() is second.graph() and made == [len([one for one in FILES if one.endswith(".py")])]
    repository(tmp_path / "big", FILES)
    monkeypatch.setattr(source, "GRAPH_MAX_BYTES", 10)
    assert Source.of(tmp_path / "big", exclude=()).graph().symbols == ()


def test_the_requests_own_words_rank_never_the_template_around_them() -> None:
    """Found by the code review of phase 29: "change" and "request" from adk-spec's own headings ranked `Change`
    first for every request."""
    files = {
        "app/git.py": "def grep_search(term, timeout):\n    pass\n",
        "app/change.py": "class Change:\n    request = 1\n",
    }
    found = ranked(
        build(files, commit="c"), "# A change is requested\n\n## The request\n\nAdd a timeout to the git grep search"
    )
    assert [path for path, _reason in found] == ["app/git.py"]


def test_a_graph_exactly_a_commits_is_kept_where_every_tool_looks(tmp_path) -> None:
    """The owner: whichever tool builds it, the graph is kept in one place, `.codegraph/` under the project, so each
    tool uses the same one. It is labelled by its commit (agreed with adk-review, amb #721-#736), so only a graph that
    is exactly the commit's is kept: a narrower one, or one of unsaved work, would pass for it (the code review of
    phase 30)."""
    commit = repository(tmp_path, FILES)
    graph = Source.of(tmp_path, exclude=()).graph()
    assert graph.commit == commit and store.load(tmp_path) == graph
    assert _git(tmp_path, "status", "--porcelain") == "", "the folder ignores itself"
    (tmp_path / "app/new.py").write_text("NEW = 1\n", encoding="utf-8")
    assert "app/new.py" in {file.path for file in Source.of(tmp_path, exclude=()).graph().files}
    assert store.load(tmp_path) == graph, "a graph of unsaved work is not kept, and the commit's stands"


@pytest.mark.parametrize(
    ("extra", "exclude"),
    [({"app/keys.py": f'KEY = """\n{KEY}"""\n'}, ()), ({}, ("app/store.py",))],
    ids=["a key's file withheld", "a file the person excluded"],
)
def test_a_graph_narrower_than_its_commits_is_not_kept(tmp_path, extra, exclude) -> None:
    repository(tmp_path, {**FILES, **extra})
    assert Source.of(tmp_path, exclude=exclude).graph().files
    assert not (tmp_path / ".codegraph").exists()


def test_a_graph_that_cannot_be_kept_changes_nothing_and_says_nothing(tmp_path) -> None:
    repository(tmp_path, FILES)
    (tmp_path / ".codegraph").write_bytes(b"mine\n")
    assert Source.of(tmp_path, exclude=()).graph().symbols
    assert (tmp_path / ".codegraph").read_bytes() == b"mine\n"


def test_no_graph_is_kept_past_what_a_graph_is_built_for(tmp_path, monkeypatch) -> None:
    """An empty graph would tell another tool the repository holds no code."""
    repository(tmp_path, FILES)
    monkeypatch.setattr("adk_spec.workspace.source.GRAPH_MAX_BYTES", 10)
    assert not Source.of(tmp_path, exclude=()).graph().files
    assert not (tmp_path / ".codegraph").exists()
