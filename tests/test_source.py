"""A repository's source read for a stage that asked for it: through git's own list of files, and within caps.

What a model names is never trusted. A path is used only where it is, to the letter, one git lists."""

from __future__ import annotations

import os
import shutil

import pytest
from conftest import repository

from adk_spec.workspace import context, source
from adk_spec.workspace import git as git_layer
from adk_spec.workspace.context import tree_text
from adk_spec.workspace.git import diff, grep
from adk_spec.workspace.source import Source, SourceError

APP = "def login(user):\n    return password(user)\n\n\ndef logout(user):\n    return None\n"
FILES = {"src/app.py": APP, "src/auth/session.py": "def start_session(user):\n    return Session(user)\n"}


def made(root, files: dict[str, str] | None = None) -> Source:
    repository(root, files or FILES)
    return Source.of(root, exclude=())


def test_a_file_git_lists_is_read_whole_and_one_past_the_cap_is_cut_and_says_so(tmp_path, monkeypatch) -> None:
    long = "".join(f"line {n}\n" for n in range(1, 401))
    held = made(tmp_path, {**FILES, "src/long.py": long})
    monkeypatch.setattr(source, "FILE_MAX_CHARS", 200)
    got = held.gathered(["src/app.py", "src/long.py"], [], [])
    assert got.texts["src/app.py"] == APP.rstrip("\n") and "src/app.py (whole)" in got.read
    assert "=== src/app.py (whole)\ndef login(user):" in got.shown
    (cut,) = [said for said in got.read if said.startswith("src/long.py")]
    assert cut.startswith("src/long.py (lines 1 to ") and cut.endswith(" of 400)")
    assert "line 1\n" in got.shown and "line 400" not in got.shown and got.left_out == ()


def test_a_line_range_reads_those_lines_at_their_own_numbers(tmp_path) -> None:
    held = made(tmp_path)
    got = held.gathered(["src/app.py:5-6"], [], [])
    assert got.read == ("src/app.py (lines 5 to 6 of 6)",)
    assert "=== src/app.py (lines 5 to 6 of 6)\ndef logout(user):\n    return None" in got.shown
    assert got.texts["src/app.py"].split("\n")[4] == "def logout(user):", "a quote found there is found at line 5"
    assert "def login" not in got.texts["src/app.py"]


@pytest.mark.parametrize(
    "asked",
    [
        "../outside.txt",
        "/etc/hosts",
        ".spec/config.toml",
        "ignored/secret.txt",
        "src/../../outside.txt",
        "SRC/app.py",
        "",
    ],
)
def test_a_path_git_does_not_list_is_not_read(tmp_path, asked: str) -> None:
    (tmp_path / "outside.txt").write_text("OUTSIDE\n", encoding="utf-8")
    root = tmp_path / "repo"
    root.mkdir()
    (root / ".gitignore").write_text("ignored/\n", encoding="utf-8")
    (root / "ignored").mkdir()
    (root / "ignored/secret.txt").write_text("IGNORED\n", encoding="utf-8")
    (root / ".spec").mkdir()
    (root / ".spec/config.toml").write_text("SPEC\n", encoding="utf-8")
    held = made(root)
    got = held.gathered([asked], [], [])
    assert got.texts == {} and got.read == () and got.shown == ""
    assert len(got.left_out) == 1 and "git lists no such file" in got.left_out[0]


def test_a_symbolic_link_is_never_read(tmp_path) -> None:
    (tmp_path / "outside.txt").write_text("OUTSIDE\n", encoding="utf-8")
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    try:
        os.symlink(tmp_path / "outside.txt", root / "src/link.txt")
        os.symlink(root / "src/app.py", root / "src/inside.py")
    except OSError:
        pytest.skip("this system does not let a test make a symbolic link")
    held = made(root)
    assert "src/link.txt" in held.paths, "git lists the link itself"
    got = held.gathered(["src/link.txt", "src/inside.py"], [], [])
    assert got.texts == {} and "OUTSIDE" not in got.shown
    assert all("a symbolic link is not read" in said for said in got.left_out) and len(got.left_out) == 2


def test_a_file_that_is_no_text_is_left_out(tmp_path) -> None:
    root = tmp_path
    (root / "src").mkdir()
    (root / "src/logo.bin").write_bytes(bytes([0xFF, 0xFE, 0x00, 0x41]))
    held = made(root)
    got = held.gathered(["src/logo.bin"], [], [])
    assert got.texts == {} and "is not text" in got.left_out[0]


def test_a_folder_lists_what_git_lists_under_it_within_the_cap(tmp_path, monkeypatch) -> None:
    held = made(tmp_path, {**FILES, **{f"docs/page{n:02}.md": "x\n" for n in range(12)}})
    monkeypatch.setattr(source, "FOLDER_MAX_PATHS", 5)
    got = held.gathered([], ["src", "docs/", "nowhere", "../.."], [])
    assert "=== src/ (2 files)\nsrc/app.py\nsrc/auth/session.py" in got.shown
    assert "=== docs/ (12 files, the first 5 listed)\ndocs/page00.md" in got.shown and "docs/page05.md" not in got.shown
    assert len(got.left_out) == 2 and all("git lists nothing under it" in said for said in got.left_out)


def test_a_search_is_a_fixed_string_and_its_lines_can_be_quoted(tmp_path) -> None:
    held = made(tmp_path)
    got = held.gathered([], [], ["start_session", ".*", "$(touch pwned)"])
    assert "=== search: start_session (1 line)\nsrc/auth/session.py:1:def start_session(user):" in got.shown
    assert "=== search: .* (0 lines)" in got.shown and "=== search: $(touch pwned) (0 lines)" in got.shown
    assert not (tmp_path / "pwned").exists()
    assert got.texts["src/auth/session.py"].split("\n")[0] == "def start_session(user):"
    assert grep(tmp_path, "PASSWORD", exclude=()) == ["src/app.py:2:    return password(user)"], (
        "letters match in either case"
    )


def test_a_round_holds_no_more_than_its_caps(tmp_path, monkeypatch) -> None:
    held = made(tmp_path, {f"src/f{n:02}.py": f"VALUE_{n} = {n}\n" * 3 for n in range(20)})
    monkeypatch.setattr(source, "FILES_A_ROUND", 3)
    monkeypatch.setattr(source, "SEARCHES_A_ROUND", 1)
    monkeypatch.setattr(source, "SEARCH_MAX_LINES", 4)
    got = held.gathered([f"src/f{n:02}.py" for n in range(6)], [], ["VALUE_", "other"])
    assert len(got.read) == 3 and "3 more files asked for than a round reads" in got.left_out
    assert "1 more search asked for than a round makes" in got.left_out
    block = got.shown.split("=== search: VALUE_")[1].split("\n===")[0]
    assert "the first 4 shown" in block and len(block.strip().split("\n")) == 1 + 4, "a header and four lines"
    monkeypatch.setattr(source, "ROUND_MAX_CHARS", 60)
    tight = held.gathered(["src/f00.py", "src/f01.py", "src/f02.py"], [], [])
    assert len(tight.read) < 3 and any("past what a round reads" in said for said in tight.left_out)


# Found by the cleanup review: a private key's body was shown.

KEY_LINE = "BAAKCAQEA7x1yQ9"
PEM = "-----BEGIN RSA " + "PRIVATE KEY-----\n" + "".join(f"MIIEow{n}{KEY_LINE}\n" for n in range(6))
PEM += "-----END RSA " + "PRIVATE KEY-----\n"


def test_a_private_keys_body_is_never_shown_whole_by_range_or_by_search(tmp_path) -> None:
    """Each line was scrubbed alone before the whole text was: the header line was hidden first, so the block that
    starts with it was no longer known for one, and its body was shown. A range of lines, and a line a search
    found, were cut out of the file before anything was scrubbed at all."""
    held = made(tmp_path, {**FILES, "deploy/key.py": "# the deploy key\nKEY = '''" + PEM + "'''\nafter = 1\n"})
    whole = held.gathered(["deploy/key.py"], [], [])
    ranged = held.gathered(["deploy/key.py:3-6"], [], [])
    found = held.gathered([], [], [KEY_LINE])
    for got in (whole, ranged, found):
        assert "MIIEow" not in got.shown and all("MIIEow" not in text for text in got.texts.values())
    assert found.shown.startswith(f"=== search: {KEY_LINE} (0 lines)"), "a hit on a hidden line is not counted"
    lines = whole.texts["deploy/key.py"].split("\n")
    assert lines[0] == "# the deploy key" and lines[10] == "after = 1", "the line after the block keeps its number"
    assert "[REDACTED" in whole.shown


def test_a_file_that_cannot_be_opened_and_a_search_git_refuses_are_left_out_and_are_no_error(
    tmp_path, monkeypatch
) -> None:
    """Found by the cleanup review: the reader raised where it promises to leave out. One locked file ended a
    whole reading."""
    from adk_spec.workspace.git import GitError

    held = made(tmp_path)
    locked = tmp_path / "src/app.py"
    locked.chmod(0)
    try:
        if os.access(locked, os.R_OK):
            pytest.skip("this account reads a file whatever its mode")
        got = held.gathered(["src/app.py", "src/auth/session.py"], [], [])
    finally:
        locked.chmod(0o644)
    assert got.read == ("src/auth/session.py (whole)",) and "src/app.py: could not be read" in got.left_out[0]

    def refused(*_args, **_kwargs):
        raise GitError("git grep failed: a bad pattern")

    monkeypatch.setattr(source, "grep", refused)
    got = held.gathered([], [], ["login"])
    assert got.shown == "" and "search for login: git grep failed" in got.left_out[0]


def test_a_file_that_holds_a_private_key_is_never_shown_however_it_is_asked_for(tmp_path) -> None:
    """A key's block is known by its first and last line together, so a key with no last line is hidden by no
    scrub. A file where a line begins a private key is left out whole, and named."""
    no_last_line = PEM.rsplit("-----END", 1)[0]
    names_it = 'HEADER = "' + PEM.split("\n")[0] + '"\n'
    held = made(tmp_path, {**FILES, "deploy/key.pem": no_last_line, "src/pem.py": names_it})
    whole = held.gathered(["deploy/key.pem"], [], [])
    ranged = held.gathered(["deploy/key.pem:3-4"], [], [])
    found = held.gathered([], [], [KEY_LINE])
    for got in (whole, ranged, found):
        assert "MIIEow" not in got.shown and got.texts == {} and got.read == ()
    said = ("deploy/key.pem: holds a private key, which is never shown",)
    assert whole.left_out == said and ranged.left_out == said
    assert held.gathered(["src/pem.py"], [], []).read == ("src/pem.py (whole)",), "code that names the line is read"


def test_a_diff_loses_the_part_of_each_file_that_holds_a_private_key(tmp_path) -> None:
    """A diff shows a file in pieces, and a piece from the middle of a key holds neither its first line nor its
    last: no scrub knows it for a key. The file is known by how it stands, or by a first line the diff itself
    shows, and its part of the diff is left out whole."""
    commit = repository(tmp_path, {**FILES, "keys/live.pem": PEM, "keys/old.pem": PEM.replace("MIIEow", "MIIOld")})
    (tmp_path / "keys/live.pem").write_text(PEM.replace("MIIEow3", "MIINew3"), encoding="utf-8", newline="\n")
    (tmp_path / "keys/old.pem").unlink()
    (tmp_path / "src/app.py").write_text(APP.replace("password", "passkey"), encoding="utf-8", newline="\n")
    whole = diff(tmp_path, commit, exclude=())
    assert "MIINew3" in whole and "-----BEGIN" not in whole.split("keys/old.pem")[0], "a piece from a key's middle"
    kept, held = Source.of(tmp_path, exclude=()).without_keys(whole)
    assert held == ("keys/live.pem", "keys/old.pem")
    assert "return passkey(user)" in kept and "MII" not in kept and "keys/" not in kept
    assert Source.of(tmp_path, exclude=()).without_keys(kept) == (kept, ()), "a diff that holds no key is as it was"


def test_a_listed_file_whose_folder_became_a_link_is_not_read_through_it(tmp_path) -> None:
    """git lists a tracked file still after its folder was replaced by a link to another folder. Read through the
    link, it is the other folder's file: one git ignores, or one a person excluded."""
    root = tmp_path / "repo"
    repository(root, {**FILES, "conf/settings.py": "DEBUG = False\n", ".gitignore": "private/\n"})
    (root / "private").mkdir()
    (root / "private/settings.py").write_text("IGNORED = 'kept out of git'\n", encoding="utf-8")
    shutil.rmtree(root / "conf")
    try:
        os.symlink("private", root / "conf", target_is_directory=True)
    except OSError:
        pytest.skip("this system does not let a test make a symbolic link")
    held = Source.of(root, exclude=())
    assert "conf/settings.py" in held.paths, "git lists it still"
    got = held.gathered(["conf/settings.py"], [], ["IGNORED"])
    assert got.texts == {} and "kept out of git" not in got.shown
    assert got.left_out == ("conf/settings.py: a symbolic link is not read",)


def test_a_search_does_not_say_whether_a_hidden_value_holds_a_word(tmp_path) -> None:
    """git searches a file as it stands, and its line is shown as scrubbed. A hit on a hidden value, counted and
    shown with its line number, tells a model that the value holds the word: asked often enough, the value."""
    held = made(tmp_path, {**FILES, "settings.py": 'DEBUG = False\nDB_PASSWORD = "winter-otter-4471"\n'})
    got = held.gathered([], [], ["winter-otter", "winter-badger", "DB_PASSWORD"])
    assert "=== search: winter-otter (0 lines)" in got.shown and "=== search: winter-badger (0 lines)" in got.shown
    assert '=== search: DB_PASSWORD (1 line)\nsettings.py:2:DB_PASSWORD = "[REDACTED]"' in got.shown


def test_a_search_never_shows_another_line_for_the_one_git_found(tmp_path) -> None:
    """git counts a file's lines by line feeds alone, and the reader takes a lone carriage return for a line's end
    too: in such a file git's number names another line. A line that does not hold the word is not the one found."""
    held = made(tmp_path, {"a.py": "x = 1\ny = 2\nprogress = 'a\rb'\nneedle_here = 2\n"})
    got = held.gathered([], [], ["needle_here"])
    assert "a.py:4:b'" not in got.shown and "a.py" not in got.texts


def test_two_readings_of_a_line_keep_the_longer_one() -> None:
    """A search holds the first characters of a long line, and a later reading of the file the whole line: a quote
    of the line's end is then found in what was kept."""
    cut, whole = "x = 1\nvalue = compute(a,", "x = 1\nvalue = compute(a, b, c)\nlast = 2"
    assert source.merged(cut, whole) == whole == source.merged(whole, cut)


def test_a_range_no_number_can_hold_is_left_out_and_is_no_error(tmp_path) -> None:
    held = made(tmp_path)
    got = held.gathered(["src/app.py:" + "9" * 5000 + "-5"], [], [])
    assert got.texts == {} and len(got.left_out) == 1 and got.left_out[0].endswith("git lists no such file")


def test_what_was_left_out_for_room_is_named_to_the_stage_and_may_be_asked_for_again(tmp_path, monkeypatch) -> None:
    """A file past what a round reads is not refused for good: the round says so where the stage reads it, and
    names it among what may be asked for again."""
    monkeypatch.setattr(source, "ROUND_MAX_CHARS", 120)
    got = made(tmp_path).gathered(["src/app.py", "src/auth/session.py"], [], [])
    assert got.read == ("src/app.py (whole)",) and got.deferred == ("src/auth/session.py",)
    assert got.shown.endswith("=== not shown, for room. Ask again for what is still needed: src/auth/session.py")
    monkeypatch.setattr(source, "FILES_A_ROUND", 1)
    assert made(tmp_path / "b").gathered(["src/app.py", "src/auth/session.py"], [], []).deferred == (
        "src/auth/session.py",
    )


# A change's other repositories: each read under its name, by the same rules as the first.

API = {
    "src/routes.py": "def sign_in(request):\n    return start_session(request.user)\n",
    "README.md": "# The API\n",
}


def two(tmp_path, api: dict[str, str] | None = None) -> Source:
    """A workspace repository and an API repository beside it, read as one source."""
    repository(tmp_path / "app", FILES)
    repository(tmp_path / "api", api or API)
    return Source.of(tmp_path / "app", exclude=(), others={"api": "../api"})


def test_another_repository_is_read_under_its_name(tmp_path) -> None:
    held = two(tmp_path)
    assert held.paths == ["src/app.py", "src/auth/session.py", "api/README.md", "api/src/routes.py"]
    assert held.names == ("api",) and held.missing == () and set(held.commits()) == {"api"}
    got = held.gathered(["api/src/routes.py"], ["api/src"], [])
    assert got.read == ("api/src/routes.py (whole)",) and got.texts["api/src/routes.py"].startswith("def sign_in(")
    assert "=== api/src/routes.py (whole)\ndef sign_in(request):" in got.shown
    assert "=== api/src/ (1 file)\napi/src/routes.py" in got.shown


def test_a_search_finds_lines_in_every_repository(tmp_path) -> None:
    got = two(tmp_path).gathered([], [], ["start_session"])
    assert got.shown.startswith("=== search: start_session (2 lines)\n")
    assert "src/auth/session.py:1:def start_session(user):" in got.shown
    assert "api/src/routes.py:2:    return start_session(request.user)" in got.shown
    assert set(got.texts) == {"src/auth/session.py", "api/src/routes.py"}


def test_a_rounds_caps_are_shared_by_the_repositories(tmp_path, monkeypatch) -> None:
    held = two(tmp_path)
    monkeypatch.setattr(source, "ROUND_MAX_CHARS", 120)
    got = held.gathered(["src/app.py", "api/src/routes.py"], [], [])
    assert got.read == ("src/app.py (whole)",) and got.deferred == ("api/src/routes.py",)


def test_every_rule_of_phase_6_holds_in_another_repository(tmp_path) -> None:
    """git's own list, nothing ignored, the repository's own exclusions, no key file, no link on the path."""
    own = '[project]\ndefault_tier = "lean"\n\n[repository]\nexclude = ["fixtures"]\n'
    api = {**API, ".gitignore": "private/\n", "keys/live.pem": PEM, "fixtures/big.json": "{}\n"}
    api |= {".spec/config.toml": own, "conf/settings.py": "DEBUG = False\n"}
    repository(tmp_path / "app", FILES)
    repository(tmp_path / "api", api)
    (tmp_path / "api/private").mkdir()
    (tmp_path / "api/private/settings.py").write_text("PRIVATE = 1\n", encoding="utf-8")
    shutil.rmtree(tmp_path / "api/conf")
    try:
        os.symlink("private", tmp_path / "api/conf", target_is_directory=True)
    except OSError:
        pytest.skip("this system does not let a test make a symbolic link")
    held = Source.of(tmp_path / "app", exclude=(), others={"api": "../api"})
    assert not [path for path in held.paths if path.startswith(("api/fixtures/", "api/private/", "api/.spec/"))]
    got = held.gathered(["api/keys/live.pem", "api/conf/settings.py", "api/fixtures/big.json"], [], ["PRIVATE = 1"])
    assert got.texts == {} and "=== search: PRIVATE = 1 (0 lines)" in got.shown, "the word is the model's; no line"
    assert got.left_out == (
        "api/keys/live.pem: holds a private key, which is never shown",
        "api/conf/settings.py: a symbolic link is not read",
        "api/fixtures/big.json: git lists no such file",
    )


def test_a_missing_repository_or_one_whose_config_does_not_load_is_named_and_left_out(tmp_path) -> None:
    repository(tmp_path / "app", FILES)
    repository(tmp_path / "api", {**API, ".spec/config.toml": "[project]\n"})
    (tmp_path / "plain").mkdir()
    others = {"api": "../api", "web": "../web", "plain": "../plain"}
    held = Source.of(tmp_path / "app", exclude=(), others=others)
    assert held.names == () and held.paths == ["src/app.py", "src/auth/session.py"]
    assert held.missing[0].startswith("api: ") and "default_tier" in held.missing[0]
    assert held.missing[1:] == ("web: no git repository at ../web", "plain: no git repository at ../plain")


@pytest.mark.parametrize("spelled", [".", "./", "../app/src", "absolute", "link"])
def test_this_repository_by_another_spelling_is_refused(tmp_path, spelled) -> None:
    repository(tmp_path / "app", FILES)
    if spelled == "absolute":
        spelled = str(tmp_path / "app")
    elif spelled == "link":
        try:
            os.symlink(tmp_path / "app", tmp_path / "again", target_is_directory=True)
        except OSError:
            pytest.skip("this system does not let a test make a symbolic link")
        spelled = "../again"
    with pytest.raises(SourceError, match="this repository itself"):
        Source.of(tmp_path / "app", exclude=(), others={"api": spelled})


def test_a_name_that_is_a_folder_here_is_refused(tmp_path) -> None:
    repository(tmp_path / "app", FILES)
    repository(tmp_path / "api", API)
    with pytest.raises(SourceError, match="`src` is also a folder of this repository"):
        Source.of(tmp_path / "app", exclude=(), others={"src": "../api"})


def test_each_repository_folds_its_own_files_and_one_repository_reads_as_before(tmp_path, monkeypatch) -> None:
    solo = made(tmp_path / "solo")
    assert solo.tree() == tree_text(solo.paths)
    held = two(tmp_path, {**API, "docs/a.md": "a\n"})
    monkeypatch.setattr(context, "TREE_MAX_PATHS", 2)
    tree = held.tree()
    assert tree.startswith("src/app.py\nsrc/auth/session.py\n=== api (3 files)\n3 files: too many to list."), tree


def test_a_round_makes_its_searches_before_it_reads_its_files(tmp_path, monkeypatch) -> None:
    """Measured live: files taken first filled a round, and every search the scout asked for was left out."""
    long = "".join(f"line {n} of a long file\n" for n in range(1, 10))
    held = made(tmp_path, {**FILES, "src/long.py": long})
    monkeypatch.setattr(source, "ROUND_MAX_CHARS", len("=== src/long.py (whole)\n" + long) + 20)
    got = held.gathered(["src/long.py"], [], ["start_session"])
    assert "=== search: start_session (1 line)" in got.shown and got.deferred == ("src/long.py",)


def test_the_line_that_opens_a_quoted_lines_block_is_found_in_the_file_as_it_stands(tmp_path) -> None:
    """Measured live: a real quote from `_approve` was kept under a note about `propose`. The block a line stands in
    is found by code, in the whole file, also where the stage was shown a range below its opening line."""
    held = two(tmp_path)
    assert held.within("src/app.py", 2) == "def login(user):" and held.within("src/app.py", 6) == "def logout(user):"
    assert held.within("src/app.py", 1) == "" and held.within("src/nope.py", 1) == ""
    assert held.within("api/src/routes.py", 2) == "def sign_in(request):"


PPK_BODY = ["AAAAgQC" + "Z" * 57, "AAAAQQD" + "Y" * 57, "AAAAQQC" + "X" * 30]
PPK = "\n".join(
    [
        *("PuTTY-User-Key-File-" + "3: ssh-rsa", "Encryption: none", "Comment: deploy", "Public-Lines: 1"),
        *("AAAAB3NzaC1yc2E", "Private-Lines: 3", *PPK_BODY, "Private-MAC: 0123abcd", ""),
    ]
)


def test_a_putty_key_file_is_never_shown_and_its_part_of_a_diff_is_left_out(tmp_path) -> None:
    """A PuTTY key is known to the scrub by its first line. A diff of a change among its private lines shows none,
    and a key cut before its last line was shown by the reader."""
    commit = repository(tmp_path, {**FILES, "keys/deploy.ppk": PPK, "keys/cut.ppk": PPK.rsplit("Private-MAC", 1)[0]})
    (tmp_path / "keys/deploy.ppk").write_text(PPK.replace("Y" * 57, "W" * 57), encoding="utf-8", newline="\n")
    held = Source.of(tmp_path, exclude=())
    got = held.gathered(["keys/deploy.ppk", "keys/cut.ppk"], [], [])
    assert got.texts == {} and got.left_out == (
        "keys/deploy.ppk: holds a private key, which is never shown",
        "keys/cut.ppk: holds a private key, which is never shown",
    )
    kept, omitted = held.without_keys(diff(tmp_path, commit, exclude=()))
    assert omitted == ("keys/deploy.ppk",) and "AAAAQQ" not in kept


def test_finding_the_key_files_of_a_diff_scrubs_no_file(tmp_path, monkeypatch) -> None:
    """Whether a file holds a key is all a diff's filter asks: scrubbing each changed file whole for it, and throwing
    the scrubbed text away, cost a second on a large working tree, on every status of a verified change."""
    commit = repository(tmp_path, FILES)
    (tmp_path / "src/app.py").write_text(APP.replace("password", "passkey"), encoding="utf-8", newline="\n")
    held = Source.of(tmp_path, exclude=())

    def refused(*_args, **_kwargs):
        raise AssertionError("a file was scrubbed to learn whether it holds a key")

    monkeypatch.setattr(source, "scrub_lines", refused)
    text = diff(tmp_path, commit, exclude=())
    assert held.without_keys(text) == (text, ())


def test_a_repository_another_account_owns_is_left_out_and_said(tmp_path, monkeypatch) -> None:
    repository(tmp_path / "app", FILES)
    repository(tmp_path / "api", API)
    own = git_layer._environment
    monkeypatch.setattr(
        git_layer, "_environment", lambda root, trust=True: {**own(root, trust), "GIT_TEST_ASSUME_DIFFERENT_OWNER": "1"}
    )
    held = Source.of(tmp_path / "app", exclude=(), others={"api": "../api"})
    assert held.names == () and held.paths == ["src/app.py", "src/auth/session.py"]
    assert held.missing[0].startswith("api: ") and "dubious ownership" in held.missing[0]


def test_two_names_for_one_repository_are_refused(tmp_path) -> None:
    repository(tmp_path / "app", FILES)
    repository(tmp_path / "api", API)
    with pytest.raises(SourceError, match="the same repository as `a`"):
        Source.of(tmp_path / "app", exclude=(), others={"a": "../api", "b": "../api/src"})


def test_this_repository_in_other_letters_is_refused_where_the_disk_ignores_case(tmp_path) -> None:
    repository(tmp_path / "app", FILES)
    if not (tmp_path / "APP").exists():
        pytest.skip("this disk tells letter cases apart")
    with pytest.raises(SourceError, match="this repository itself"):
        Source.of(tmp_path / "app", exclude=(), others={"x": "../APP"})


def test_a_folder_inside_another_adk_spec_project_is_refused(tmp_path) -> None:
    """Its exclusions are read from the project's own `.spec/config.toml`: named by a folder inside it, the files it
    keeps out were listed and read."""
    own = '[project]\ndefault_tier = "lean"\n\n[repository]\nexclude = ["secrets"]\n'
    repository(tmp_path / "app", FILES)
    repository(tmp_path / "other", {"sub/ok.py": "x = 1\n", "sub/secrets/s.txt": "s\n", ".spec/config.toml": own})
    with pytest.raises(SourceError, match=r"inside the adk-spec project at \.\./other"):
        Source.of(tmp_path / "app", exclude=(), others={"o": "../other/sub"})


def test_the_line_that_opens_a_block_is_never_a_bracket_alone(tmp_path) -> None:
    cs = "public class Auth\n{\n    public void SignIn()\n    {\n        StartSession(user);\n    }\n}\n"
    held = made(tmp_path, {**FILES, "Auth.cs": cs})
    assert held.within("Auth.cs", 5) == "public void SignIn()" and held.within("Auth.cs", 3) == "public class Auth"


def test_a_key_in_a_large_file_or_one_not_utf8_is_withheld_from_the_diff_too(tmp_path, monkeypatch) -> None:
    """Found by the third audit: whether a file holds a key was asked only of a UTF-8 file within the read cap, so a
    hunk from a key's middle in a larger file, or in one saved as Latin-1, reached the diff `verify` sends."""
    monkeypatch.setattr(source, "FILE_MAX_BYTES", 300)
    (tmp_path / "conf").mkdir(parents=True)
    (tmp_path / "conf/latin.txt").write_bytes(("caf\xe9 = 1\n" + PEM).encode("latin-1"))
    commit = repository(tmp_path, {**FILES, "conf/big.txt": "x = 1\n" * 100 + PEM})
    for name in ("conf/big.txt", "conf/latin.txt"):
        path = tmp_path / name
        path.write_bytes(path.read_bytes().replace(b"MIIEow3", b"MIINew3"))
    whole = diff(tmp_path, commit, exclude=())
    assert whole.count("MIINew3") == 2
    kept, held = Source.of(tmp_path, exclude=()).without_keys(whole)
    assert held == ("conf/big.txt", "conf/latin.txt") and "MIINew3" not in kept


def test_a_file_read_before_as_too_large_is_still_searched_for_a_key(tmp_path, monkeypatch) -> None:
    """Found by the cleanup review: what a reading of a file said, "too large to read", was taken for the answer to
    whether it holds a key, so a file the reading had opened was never searched."""
    monkeypatch.setattr(source, "FILE_MAX_BYTES", 300)
    commit = repository(tmp_path, {**FILES, "conf/big.txt": "x = 1\n" * 100 + PEM})
    path = tmp_path / "conf/big.txt"
    path.write_text(path.read_text(encoding="utf-8").replace("MIIEow3", "MIINew3"), encoding="utf-8", newline="\n")
    held = Source.of(tmp_path, exclude=())
    assert "too large" in " ".join(held.gathered(["conf/big.txt"], [], []).left_out)
    kept, withheld = held.without_keys(diff(tmp_path, commit, exclude=()))
    assert withheld == ("conf/big.txt",) and "MIINew3" not in kept
