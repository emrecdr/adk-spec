"""A repository's source read for a stage that asked for it: through git's own list of files, and within caps.

What a model names is never trusted. A path is used only where it is, to the letter, one git lists."""

from __future__ import annotations

import os

import pytest
from conftest import repository

from adk_spec.workspace import source
from adk_spec.workspace.git import diff, grep
from adk_spec.workspace.source import Source

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
    assert found.shown.startswith(f"=== search: {KEY_LINE} (5 lines)"), "the word is the model's own; no line is shown"
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
