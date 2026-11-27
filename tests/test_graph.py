"""The code graph beside the reading: built from what a reading may show, ranked by adk-spec's own policy, and only
ever a hint or a lead a stage confirms by reading (the owner, 27 November 2026: never the only source of truth)."""

from __future__ import annotations

from codegraph import build
from conftest import repository

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


def test_the_reach_names_who_imports_and_tests_the_files_a_reading_found() -> None:
    said = reach_text(build(FILES, commit="c"), ["app/engine.py", "app/store.py", "gone.py"])
    assert said == "- app/engine.py: imported by app/cli.py, app/web.py; tested by tests/test_engine.py"


def test_a_statement_naming_what_the_code_defines_nowhere_is_a_lead() -> None:
    graph = build({**FILES, "app/agent.py": "from google.adk import LlmAgent\nimport json\n"}, commit="c")
    note = "`Engine.start` begins it, `Engine.stop` ends it; `LlmAgent` and `json.loads` are a library's, `run` a word"
    statements = [
        Statement(kind="exists", path="app/agent.py", line=1, quote="import json", note=note),
        Statement(kind="risk", path="app/agent.py", line=1, quote="import json", note="`Nowhere.at_all` may break"),
    ]
    assert undefined(graph, statements) == [(1, "Engine.stop")]


def test_a_definition_is_read_by_its_file_and_name(tmp_path) -> None:
    repository(tmp_path, FILES)
    got = Source.of(tmp_path, exclude=()).gathered(["app/engine.py::Engine.start", "app/engine.py::Engine.fly"], [], [])
    assert got.read == ("app/engine.py (lines 2 to 3 of 3)",)
    assert "    def start(self):\n        return 1" in got.shown and "class Engine" not in got.shown
    assert any("Engine.fly" in one and "no such definition" in one for one in got.left_out)


def test_within_names_the_enclosing_definition_where_the_file_agrees(tmp_path) -> None:
    """Indentation named the nearest block, an `if`; the graph names the function, and only where the file's own line
    there is a definition's."""
    source = "def decide(user):\n    if user:\n        return password()\n    return None\n"
    repository(tmp_path, {"app/auth.py": source, "notes.txt": "a\n  b\n"})
    held = Source.of(tmp_path, exclude=())
    assert held.within("app/auth.py", 3) == "def decide(user):"
    assert held.within("notes.txt", 2) == "a", "a file the graph does not hold keeps the indentation rule"


def test_a_dunder_method_shares_no_word_with_a_request() -> None:
    """Measured on adk-spec: every `__init__` matched "init", and a research script ranked first for "at init"."""
    files = {**FILES, "app/config.py": "class Config:\n    def __init__(self):\n        pass\n"}
    assert ranked(build(files, commit="c"), "Write the entry at init") == []
