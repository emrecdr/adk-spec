"""The workspace's path policy and its text files: the same refusals and the same bytes on every system."""

from __future__ import annotations

import ast
import os
import stat

import pytest
from conftest import PACKAGE

from adk_spec.workspace.files import NotTextError, read_text, write_all, write_text
from adk_spec.workspace.paths import PathError, inside

E_ACUTE = chr(0xE9)


PARTS = ("", ".", "..", "a/b", "a\\b", "x\x00y", "con", "NUL.md", "auth.", "auth ", "a:b", "a*b", "a?b")


@pytest.mark.parametrize("part", [*PARTS, 'a"b', "a<b", "a|b", "CONIN$"])
def test_a_part_no_system_holds_safely_is_refused_on_every_system(tmp_path, part: str) -> None:
    with pytest.raises(PathError):
        inside(tmp_path, "specs", part)


def test_a_name_that_differs_from_a_neighbour_only_by_case_is_refused(tmp_path) -> None:
    (tmp_path / "specs" / "auth").mkdir(parents=True)
    with pytest.raises(PathError, match="auth"):
        inside(tmp_path, "specs", "Auth")
    assert inside(tmp_path, "specs", "auth") == tmp_path / "specs" / "auth"
    assert inside(tmp_path, "specs", "billing", "spec.md") == tmp_path / "specs" / "billing" / "spec.md"


def test_a_link_on_the_way_is_refused_before_it_is_followed(tmp_path) -> None:
    outside, root = tmp_path / "outside", tmp_path / "repo"
    outside.mkdir()
    root.mkdir()
    try:
        (root / "specs").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("this account may not make a symbolic link, which Windows holds to a privilege")
    with pytest.raises(PathError, match="link"):
        inside(root, "specs", "auth")


def test_what_is_written_is_utf8_with_lf_and_one_final_newline(tmp_path) -> None:
    write_text(tmp_path / "a" / "b.md", E_ACUTE + "\r\nx  ")
    assert (tmp_path / "a" / "b.md").read_bytes() == (E_ACUTE + "\nx\n").encode("utf-8")


def test_a_bom_and_crlf_are_read_as_their_lf_twin(tmp_path) -> None:
    (tmp_path / "s.md").write_bytes(b"\xef\xbb\xbf# auth\r\nx\r\n")
    assert read_text(tmp_path / "s.md") == "# auth\nx\n"


def test_a_file_that_is_not_utf8_is_named_and_never_decoded_wrong(tmp_path) -> None:
    (tmp_path / "s.md").write_bytes("# auth\n".encode("utf-16"))
    with pytest.raises(NotTextError, match="UTF-8"):
        read_text(tmp_path / "s.md")


def _held_open(*_args):
    raise PermissionError("another process holds the file")


def test_a_write_that_fails_leaves_the_old_file_and_no_temporary_one(tmp_path, monkeypatch) -> None:
    write_text(tmp_path / "s.md", "old")
    monkeypatch.setattr(os, "replace", _held_open)
    with pytest.raises(PermissionError):
        write_text(tmp_path / "s.md", "new")
    assert (tmp_path / "s.md").read_text(encoding="utf-8") == "old\n"
    assert [p.name for p in tmp_path.iterdir()] == ["s.md"]


def test_write_all_replaces_nothing_when_one_text_cannot_be_written(tmp_path) -> None:
    write_text(tmp_path / "a.md", "old")
    (tmp_path / "blocked").write_text("a file where a folder is needed", encoding="utf-8")
    with pytest.raises(OSError):  # noqa: PT011 -- which OSError it is differs by system
        write_all({tmp_path / "a.md": "new", tmp_path / "blocked" / "b.md": "new"})
    assert (tmp_path / "a.md").read_text(encoding="utf-8") == "old\n"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["a.md", "blocked"]


def test_write_all_writes_every_text(tmp_path) -> None:
    write_all({tmp_path / "a.md": "one", tmp_path / "deep" / "b.md": "two"})
    assert (tmp_path / "a.md").read_text(encoding="utf-8") == "one\n"
    assert (tmp_path / "deep" / "b.md").read_text(encoding="utf-8") == "two\n"


def test_every_text_file_call_in_the_package_names_its_encoding() -> None:
    offenders = []
    for path in sorted(PACKAGE.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "attr", getattr(node.func, "id", ""))
            own = isinstance(node.func, ast.Name) and name != "open"  # the package's own read_text and write_text
            binary = any(isinstance(a, ast.Constant) and isinstance(a.value, str) and "b" in a.value for a in node.args)
            named = any(k.arg == "encoding" for k in node.keywords)
            if name in ("read_text", "write_text", "open") and not (own or binary or named):
                offenders.append(f"{path.relative_to(PACKAGE)}:{node.lineno}")
    assert offenders == [], offenders


def test_write_all_puts_back_what_it_replaced_when_a_later_replace_fails(tmp_path, monkeypatch) -> None:
    """Found by review: the second of three replaces failed, as on a file Windows holds open, and the first stayed."""
    write_text(tmp_path / "a.md", "old a")
    write_text(tmp_path / "b.md", "old b")
    real, asked, held = os.replace, [], []

    def second_fails(source, target):
        asked.append(target)
        if len(asked) == 2:
            held.append(target)
        if target in held:  # held open, as Windows holds a file: every try at it fails, the retries too
            raise PermissionError("another process holds the file")
        return real(source, target)

    monkeypatch.setattr(os, "replace", second_fails)
    with pytest.raises(PermissionError):
        write_all({tmp_path / "a.md": "new a", tmp_path / "b.md": "new b", tmp_path / "c.md": "new c"})
    assert (tmp_path / "a.md").read_text(encoding="utf-8") == "old a\n"
    assert (tmp_path / "b.md").read_text(encoding="utf-8") == "old b\n"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["a.md", "b.md"]


@pytest.mark.skipif(os.name == "nt", reason="a Windows file has no owner, group and other modes")
def test_a_written_file_is_as_readable_as_any_file_this_account_makes(tmp_path) -> None:
    """Found by review: every file came out owner-only, the temporary file's mode, and a rewrite narrowed a file."""
    kept = tmp_path / "kept.md"
    kept.write_text("x", encoding="utf-8")
    kept.chmod(0o664)
    mask = os.umask(0o022)
    try:
        write_text(tmp_path / "new.md", "x")
        write_text(kept, "y")
    finally:
        os.umask(mask)
    assert stat.S_IMODE((tmp_path / "new.md").stat().st_mode) == 0o644
    assert stat.S_IMODE(kept.stat().st_mode) == 0o664
