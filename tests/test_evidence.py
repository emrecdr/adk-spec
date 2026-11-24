"""Evidence: the lines `verify` proved each requirement with, kept beside the change and then beside the living
spec, and a requirement whose lines are gone from the code flagged as suspect."""

from __future__ import annotations

import json

import pytest
from conftest import on_the_fake, run
from test_verify import approved_in_a_repository, implemented

from adk_spec.domain.evidence_md import QUOTE_MAX, QUOTES_A_REQUIREMENT, Proof, kept, parse_evidence, render_evidence
from adk_spec.domain.verify import Verdict

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
