"""Evidence: the lines `verify` proved each requirement with, kept beside the change and then beside the living
spec, and a requirement whose lines are gone from the code flagged as suspect."""

from __future__ import annotations

import json

import pytest
from conftest import on_the_fake, repository, run, seeded
from test_verify import AFTER, approved_in_a_repository, implemented, verified_in_a_repository

from adk_spec.domain.evidence_md import (
    QUOTE_MAX,
    QUOTES_A_REQUIREMENT,
    Proof,
    folded,
    kept,
    parse_evidence,
    render_evidence,
)
from adk_spec.domain.text import quoted_at
from adk_spec.domain.verify import Verdict
from adk_spec.workspace.files import read_text, write_text

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


def test_a_quote_over_a_secret_is_kept_as_the_diff_showed_it() -> None:
    """Phase 18: a quote over a secret is looked for as it was shown, scrubbed, so it is kept as evidence like any."""
    said = [Verdict("REQ-AUTH-004", "met", (("src/auth.py", "token = [REDACTED:generic_secret]"),), "r")]
    (one,) = kept(said, added=frozenset({"REQ-AUTH-004"}), change="passkeys", at=AT, repositories={})
    assert one.quote == "token = [REDACTED:generic_secret]"


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
    verified_in_a_repository(tmp_path)
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
    """The seeded change verified in a repository with every requirement met, and archived."""
    verified_in_a_repository(root)
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
    verified_in_a_repository(tmp_path)
    mine = tmp_path / CHANGE_EVIDENCE
    write_text(mine, mine.read_text(encoding="utf-8").replace(" | 20", " | 19"))  # another verification's time
    assert run(tmp_path, "archive", "passkeys") == 0
    assert not (tmp_path / LIVING_EVIDENCE).exists()


def test_a_living_evidence_file_that_does_not_read_is_left_as_it_is(tmp_path, capsys) -> None:
    verified_in_a_repository(tmp_path)
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


def test_a_config_that_does_not_read_stops_neither_validate_nor_status(tmp_path) -> None:
    """Found by the code review: the evidence check read the config first, and a fault in it, or none at all, stopped
    `validate` and `status` where no evidence was kept."""
    seeded(tmp_path)
    write_text(tmp_path / ".spec/config.toml", "[review]\nfrom = 'a newer adk-spec'\n")
    assert run(tmp_path, "validate") in (0, 1) and run(tmp_path, "status") == 0
    (tmp_path / ".spec/config.toml").unlink()
    assert run(tmp_path, "validate") in (0, 1) and run(tmp_path, "status") == 0


def test_a_long_quote_is_never_cut_too_short_to_find() -> None:
    """Found by the code review: cut at its one early space, `x = <300 characters>` was kept as `x =`, which no text
    holds, and its requirement read as suspect at once."""
    line = "x = " + "A" * 300
    said = [Verdict("REQ-AUTH-004", "met", (("src/auth.py", line),), "r")]
    (one,) = kept(said, added=frozenset({"REQ-AUTH-004"}), change="passkeys", at=AT, repositories={})
    assert len(one.quote) <= QUOTE_MAX and quoted_at(one.quote, line) is not None


def test_a_requirement_no_longer_in_the_living_spec_is_not_suspect(tmp_path, capsys) -> None:
    """Found by the code review: lines left in a living evidence file for a requirement since removed were reported
    as suspect, with advice to verify a change that keeps it."""
    seeded(tmp_path)
    repository(tmp_path)
    lines = [
        proof("REQ-AUTH-009", quote="def retired_long_ago():"),
        proof("REQ-AUTH-002", quote="def never_written():"),
    ]
    write_text(tmp_path / LIVING_EVIDENCE, render_evidence("auth", lines))
    gone = [line for line in validated(tmp_path, capsys)[1].splitlines() if "spec.evidence-gone" in line]
    assert len(gone) == 1 and "REQ-AUTH-002" in gone[0]


@pytest.mark.parametrize(
    ("folder", "path"),
    [
        (".", "../outside.txt"),
        (".", "/etc/hosts"),
        ("/", "etc/hosts"),
        ("..", "outside.txt"),
        (".", "src/a\x00.py"),  # a NUL stopped `status` with a traceback
        (".", "C:x.py"),  # a drive-relative path passed the guard on Windows
        ("C:/elsewhere", "x.py"),
    ],
)
def test_an_evidence_line_reaching_outside_its_repository_is_not_checked(tmp_path, folder, path) -> None:
    """Found by the code review: a line naming `..` or an absolute path was read wherever it pointed, so a pull
    request could learn, from a note, whether a string is in a file on the runner."""
    from adk_spec.workspace.evidence import holds

    root = tmp_path / "repo"
    seeded(root)
    repository(root)
    write_text(tmp_path / "outside.txt", "nothing of the quote\n")
    assert holds(root, proof(repository=folder, path=path, quote="SECRET=abc is here"), ()) is None


def test_evidence_of_a_verification_of_an_earlier_version_is_not_folded(tmp_path) -> None:
    """Found by the code review: a lean change revised after its verification, then approved again, folded the
    quotes that proved its earlier version."""
    approved_in_a_repository(tmp_path, tier="lean")
    implemented(tmp_path)
    assert run(tmp_path, "verify", "passkeys") == 0
    brief = tmp_path / ".spec/changes/passkeys/brief.md"
    write_text(brief, read_text(brief) + "\nRevised after the verification.\n")
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer") == 0
    assert run(tmp_path, "archive", "passkeys") == 0
    assert not (tmp_path / LIVING_EVIDENCE).exists()


def test_a_lean_change_approved_again_as_it_stands_keeps_its_evidence(tmp_path) -> None:
    """Found by the code review: approved again with nothing edited, after its verify, a lean change lost its evidence
    at archive, the verification read as older than the approval."""
    approved_in_a_repository(tmp_path, tier="lean")
    implemented(tmp_path)
    assert run(tmp_path, "verify", "passkeys") == 0
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer") == 0
    assert run(tmp_path, "archive", "passkeys") == 0
    assert (tmp_path / LIVING_EVIDENCE).is_file()


def test_no_kept_line_where_there_was_no_evidence_to_add(tmp_path, capsys) -> None:
    """Found by the code review: an archive with nothing to add or take out said it had left the evidence file."""
    from samples import BRIEF, tasks_for
    from test_review import MENTION

    ws = seeded(tmp_path)
    folder = ws.new_change("unlock", "lean")  # adds a requirement, verified by no one: nothing to fold
    write_text(folder / "brief.md", BRIEF)
    write_text(folder / "tasks.md", tasks_for("REQ-AUTH-005"))
    write_text(folder / "specs" / "auth" / "spec.md", MENTION)
    assert run(tmp_path, "approve", "unlock", "--by", "reviewer") == 0
    write_text(tmp_path / LIVING_EVIDENCE, "someone wrote this by hand\n")
    capsys.readouterr()
    assert run(tmp_path, "archive", "unlock") == 0
    assert LIVING_EVIDENCE not in capsys.readouterr().out


def test_a_change_modifying_a_requirement_with_no_proof_takes_its_old_lines_out(tmp_path) -> None:
    """Found by the cleanup review: a change with no proof of its own for a requirement it modifies left that
    requirement's old lines in the living evidence, where they stood for a statement no longer there."""
    from samples import BRIEF, tasks_for
    from test_review import OTHER

    ws = seeded(tmp_path)
    folder = ws.new_change("stricter", "lean")  # modifies REQ-AUTH-002, verified by no one
    write_text(folder / "brief.md", BRIEF)
    write_text(folder / "tasks.md", tasks_for("REQ-AUTH-002"))
    write_text(folder / "specs" / "auth" / "spec.md", OTHER)
    before = [proof("REQ-AUTH-002", quote="failures >= 5"), proof("REQ-AUTH-001", quote="return password(user)")]
    write_text(tmp_path / LIVING_EVIDENCE, render_evidence("auth", before))
    assert run(tmp_path, "approve", "stricter", "--by", "reviewer") == 0
    assert run(tmp_path, "archive", "stricter") == 0
    read, _unread = parse_evidence(read_text(tmp_path / LIVING_EVIDENCE))
    assert [one.req for _line, one in read] == ["REQ-AUTH-001"]


def test_a_quote_cut_inside_a_stand_in_holds_while_its_line_stands(tmp_path) -> None:
    """Found by phase 17's reviews: evidence quoted from a scrubbed diff, cut through `[REDACTED:...]`, read as suspect
    for ever, the stand-in never being in the code as it stands; it is looked for as the diff was shown too."""
    from adk_spec.workspace.evidence import holds

    key = "AKIA" + "IOSFODNN7EXAMPLE"
    write_text(tmp_path / "src/conf.py", f'KEY = "{key}"\n')
    cut = proof(quote='KEY = "[REDACTE', path="src/conf.py")
    assert holds(tmp_path, cut, ()) is True
