"""Evidence: the lines `verify` proved each requirement with, kept beside the change and then beside the living
spec, and a requirement whose lines are gone from the code flagged as suspect."""

from __future__ import annotations

import json

import pytest
from conftest import on_the_fake, run, seeded
from test_verify import AFTER, approved_in_a_repository, implemented

from adk_spec.domain.evidence_md import (
    QUOTE_MAX,
    QUOTES_A_REQUIREMENT,
    Proof,
    folded,
    kept,
    parse_evidence,
    render_evidence,
)
from adk_spec.domain.verify import Verdict
from adk_spec.workspace.files import write_text

AT = "2026-11-24T10:00:00+00:00"
CHANGE_EVIDENCE = ".spec/changes/passkeys/evidence.md"


@pytest.fixture(autouse=True)
def _fake_arm(monkeypatch) -> None:
    on_the_fake(monkeypatch)


def proof(req: str = "REQ-AUTH-004", quote: str = "return passkey(user)", **held) -> Proof:
    held = {"repository": ".", "path": "src/auth.py", "change": "passkeys", "at": AT, **held}
    return Proof(req=req, quote=quote, **held)


def test_evidence_reads_back_as_it_was_written() -> None:
    proofs = [
        proof(quote="print(`tick`)"),
        proof("REQ-AUTH-002", quote="a | b or c"),
        proof("REQ-AUTH-002", repository="../api", path="api/x.py", quote="def x():"),
    ]
    read, unread = parse_evidence(render_evidence("auth", proofs))
    assert [one for _line, one in read] == sorted(
        proofs, key=lambda one: (one.req, one.repository, one.path, one.quote)
    )
    assert unread == []


def test_evidence_with_a_line_deleted_still_reads() -> None:
    text = render_evidence("auth", [proof(), proof("REQ-AUTH-002", quote="failures >= 3")])
    lines = text.splitlines()
    deleted = "\n".join(line for line in lines if "failures" not in line) + "\n"
    read, unread = parse_evidence(deleted)
    assert [one.req for _line, one in read] == ["REQ-AUTH-004"] and unread == []


def test_a_line_off_the_grammar_is_named_not_fatal() -> None:
    text = render_evidence("auth", [proof()]) + "- REQ-AUTH-002 a line someone wrote\n"
    read, unread = parse_evidence(text)
    assert len(read) == 1 and unread == [len(text.splitlines())]


def test_only_met_verdicts_of_what_a_change_adds_or_modifies_are_kept() -> None:
    said = [
        Verdict("REQ-AUTH-004", "met", (("src/auth.py", "return passkey(user)"),), "r"),
        Verdict("REQ-AUTH-002", "unmet", (), "r"),
        Verdict("REQ-AUTH-001", "met", (("src/auth.py", "return password(user)"),), "r"),
    ]
    added = frozenset({"REQ-AUTH-004", "REQ-AUTH-002"})
    assert [one.req for one in kept(said, added=added, change="passkeys", at=AT, repositories={})] == ["REQ-AUTH-004"]


def test_a_quote_over_a_secret_is_not_kept() -> None:
    said = [Verdict("REQ-AUTH-004", "met", (("src/auth.py", "token = [REDACTED:generic_secret]"),), "r")]
    assert kept(said, added=frozenset({"REQ-AUTH-004"}), change="passkeys", at=AT, repositories={}) == []


def test_another_repositorys_path_is_kept_with_its_folder() -> None:
    said = [Verdict("REQ-AUTH-004", "met", (("api/x.py", "def x():"),), "r")]
    (one,) = kept(said, added=frozenset({"REQ-AUTH-004"}), change="passkeys", at=AT, repositories={"api": "../api"})
    assert (one.repository, one.path) == ("../api", "x.py")


def test_quotes_are_capped_in_length_and_number() -> None:
    long = " ".join(["word"] * 100)
    evidence = tuple(("src/auth.py", f"{n} {long}") for n in range(5))
    said = [Verdict("REQ-AUTH-004", "met", evidence, "r")]
    proofs = kept(said, added=frozenset({"REQ-AUTH-004"}), change="passkeys", at=AT, repositories={})
    assert len(proofs) == QUOTES_A_REQUIREMENT == 3
    assert all(len(one.quote) <= QUOTE_MAX == 240 and not one.quote.endswith(" ") for one in proofs)


def test_verify_keeps_the_changes_evidence(tmp_path, capsys) -> None:
    approved_in_a_repository(tmp_path)
    implemented(tmp_path)
    assert run(tmp_path, "verify", "passkeys") == 0
    read, unread = parse_evidence((tmp_path / CHANGE_EVIDENCE).read_text(encoding="utf-8"))
    assert unread == [] and {one.req for _line, one in read} == {"REQ-AUTH-004", "REQ-AUTH-002"}
    assert any(one.quote == "return passkey(user)" for _line, one in read)
    assert {one.at for _line, one in read} == {
        json.loads((tmp_path / ".spec/changes/passkeys/change.json").read_text())["verification"]["at"]
    }
    capsys.readouterr()
    assert run(tmp_path, "status", "--json") == 0
    assert "archive" in json.loads(capsys.readouterr().out)["changes"][0]["next"], "the evidence voided nothing"


LIVING_EVIDENCE = ".spec/specs/auth/evidence.md"


def archived(root) -> None:
    """The seeded change approved in a repository, implemented, verified with every requirement met, and archived."""
    approved_in_a_repository(root)
    implemented(root)
    assert run(root, "verify", "passkeys") == 0
    assert run(root, "archive", "passkeys") == 0


def validated(root, capsys, *flags: str) -> tuple[int, str]:
    capsys.readouterr()
    code = run(root, "validate", *flags)
    return code, capsys.readouterr().out


def test_archive_folds_the_verified_evidence_beside_the_living_spec(tmp_path) -> None:
    archived(tmp_path)
    read, unread = parse_evidence((tmp_path / LIVING_EVIDENCE).read_text(encoding="utf-8"))
    assert unread == [] and {one.req for _line, one in read} == {"REQ-AUTH-004", "REQ-AUTH-002"}


def test_a_later_change_replaces_a_requirements_evidence() -> None:
    living = [proof(), proof("REQ-AUTH-002", quote="failures >= 3"), proof("REQ-AUTH-009", quote="gone soon")]
    later = [proof("REQ-AUTH-002", quote="failures >= 4", change="stricter")]
    merged = folded(living, later, replaced=frozenset({"REQ-AUTH-002"}), removed=frozenset({"REQ-AUTH-009"}))
    assert [(one.req, one.quote) for one in merged] == [
        ("REQ-AUTH-002", "failures >= 4"),
        ("REQ-AUTH-004", "return passkey(user)"),
    ]


def test_evidence_of_a_superseded_verification_is_not_folded(tmp_path) -> None:
    approved_in_a_repository(tmp_path)
    implemented(tmp_path)
    assert run(tmp_path, "verify", "passkeys") == 0
    mine = tmp_path / CHANGE_EVIDENCE
    write_text(mine, mine.read_text(encoding="utf-8").replace(" | 20", " | 19"))  # another verification's time
    assert run(tmp_path, "archive", "passkeys") == 0
    assert not (tmp_path / LIVING_EVIDENCE).exists()


def test_a_living_evidence_file_that_does_not_read_is_left_as_it_is(tmp_path, capsys) -> None:
    approved_in_a_repository(tmp_path)
    implemented(tmp_path)
    assert run(tmp_path, "verify", "passkeys") == 0
    edited = "# Evidence: auth\n\nsomeone wrote this by hand\n"
    write_text(tmp_path / LIVING_EVIDENCE, edited)
    capsys.readouterr()
    assert run(tmp_path, "archive", "passkeys") == 0
    assert (tmp_path / LIVING_EVIDENCE).read_text(encoding="utf-8") == edited
    assert f"kept      {LIVING_EVIDENCE}: " in capsys.readouterr().out


def test_a_quote_gone_from_the_code_makes_its_requirement_suspect(tmp_path, capsys) -> None:
    archived(tmp_path)
    strict, _out = validated(tmp_path, capsys, "--strict")
    write_text(tmp_path / "src/auth.py", AFTER.replace("return passkey(user)", "return webauthn(user)"))
    code, out = validated(tmp_path, capsys)
    (gone,) = [line for line in out.splitlines() if "spec.evidence-gone" in line]
    assert code == 0 and gone.startswith("INFO") and "REQ-AUTH-004" in gone
    assert validated(tmp_path, capsys, "--strict")[0] == strict, "a suspect is a note: it fails no CI"
    assert run(tmp_path, "status") == 0
    assert "auth: 1 requirement suspect (adk-spec validate lists them)" in capsys.readouterr().out


def test_a_quote_moved_to_another_file_is_not_suspect(tmp_path, capsys) -> None:
    archived(tmp_path)
    write_text(tmp_path / "src/auth.py", AFTER.replace("return passkey(user)", "return login(user)"))
    write_text(tmp_path / "src/login.py", "def login(user):\n    return passkey(user)\n")
    assert "spec.evidence-gone" not in validated(tmp_path, capsys)[1]


def test_a_file_with_crlf_endings_still_holds_its_quote(tmp_path, capsys) -> None:
    archived(tmp_path)
    (tmp_path / "src/auth.py").write_bytes(AFTER.replace("\n", "\r\n").encode())
    assert "spec.evidence-gone" not in validated(tmp_path, capsys)[1]


def test_another_repository_that_is_not_there_is_not_checked(tmp_path, capsys) -> None:
    seeded(tmp_path)
    away = proof(repository="../api", path="x.py", quote="def nowhere_to_be_found():")
    write_text(tmp_path / LIVING_EVIDENCE, render_evidence("auth", [away]))
    assert "spec.evidence-gone" not in validated(tmp_path, capsys)[1]


def test_an_evidence_line_off_the_grammar_is_a_note(tmp_path, capsys) -> None:
    seeded(tmp_path)
    write_text(tmp_path / LIVING_EVIDENCE, render_evidence("auth", [proof()]) + "a line written by hand\n")
    (note,) = [line for line in validated(tmp_path, capsys)[1].splitlines() if "spec.evidence-unreadable" in line]
    assert note.startswith("INFO") and LIVING_EVIDENCE in note
