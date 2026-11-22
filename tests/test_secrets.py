"""Known secret shapes are scrubbed from every model request, of every command, and so from every recording.

The shapes and the scrub are the reference project's, ported as they stand. A secret here is built from its parts,
so that no line of this file is one."""

from __future__ import annotations

import pytest
from conftest import on_the_fake, run, seeded

from adk_spec.domain.secrets import holds_a_key, scrub, scrub_lines
from adk_spec.workspace.files import read_text
from adk_spec.workspace.layout import Workspace
from adk_spec.workspace.runs import listed

AWS_KEY = "AKIA" + "IOSFODNN7EXAMPLE"
GITHUB_TOKEN = "ghp_" + "a1B2c3D4" * 5
KEY_BODY = "MIIEowIBAAKCAQEA7x1yQ9"
KEY_BLOCK = "-----BEGIN RSA " + f"PRIVATE KEY-----\n{KEY_BODY}\n-----END RSA " + "PRIVATE KEY-----"
PASSWORD, URL_PASSWORD, BEARER = "hunter2-" + "hunter2", "s3cret" + "pass9", "abcdef1234567890" + "abcdef"
SHAPES = [
    (f"aws_key = {AWS_KEY}", AWS_KEY),
    (f"GITHUB_TOKEN={GITHUB_TOKEN}", GITHUB_TOKEN),
    (KEY_BLOCK, KEY_BODY),
    (f'password = "{PASSWORD}"', PASSWORD),
    (f"postgres://app:{URL_PASSWORD}@db.internal/x", URL_PASSWORD),
    (f"Authorization: Bearer {BEARER}", BEARER),
]


@pytest.mark.parametrize(("text", "secret"), SHAPES)
def test_a_known_secret_shape_is_replaced(text: str, secret: str) -> None:
    scrubbed, count = scrub(f"before\n{text}\nafter")
    assert secret not in scrubbed and "[REDACTED" in scrubbed and count >= 1
    assert scrubbed.startswith("before\n") and scrubbed.endswith("\nafter"), "what stands around it is kept"


def test_code_that_names_a_secret_and_holds_none_is_left_alone() -> None:
    code = "token = get_token(request)\nclass TokenBucket: ...\ndef rotate(api_key: str) -> None: ...\n"
    assert scrub(code) == (code, 0)


def test_scrubbing_twice_changes_nothing_more() -> None:
    once, count = scrub("\n".join(text for text, _secret in SHAPES))
    assert count == len(SHAPES) and scrub(once) == (once, 0)


def test_what_a_model_is_sent_and_what_is_recorded_hold_no_secret(tmp_path, monkeypatch, fake_provider) -> None:
    """Every request of every command passes the scrub first: the recorder and the provider read what it left."""
    on_the_fake(monkeypatch)
    seeded(tmp_path)
    request = f"Rotate {AWS_KEY} out of the sign-in config."
    assert run(tmp_path, "propose", request, "--tier", "lean", "--id", "rotate") == 0
    sent = [str(r.config.system_instruction) for r in fake_provider.requests]
    assert sent and all(AWS_KEY not in text for text in sent) and "[REDACTED:aws_access_key_id]" in sent[0]
    recordings = listed(Workspace.find(tmp_path))
    assert recordings and all(AWS_KEY not in read_text(path) for path in recordings)


def test_a_scrub_that_fails_sends_nothing(tmp_path, monkeypatch, capsys, fake_provider) -> None:
    from adk_spec.orchestration import plugins

    def broken(_text: str) -> tuple[str, int]:
        raise RuntimeError("the scrub broke")

    on_the_fake(monkeypatch)
    seeded(tmp_path)
    monkeypatch.setattr(plugins, "scrub", broken)
    assert run(tmp_path, "propose", "Let users sign in with a passkey.", "--tier", "lean", "--id", "unsent") == 3
    assert fake_provider.requests == [], "nothing unscrubbed is sent"
    assert "REDACTION_FAILED" in capsys.readouterr().err and not (tmp_path / ".spec/changes/unsent").exists()


@pytest.mark.parametrize(("text", "secret"), SHAPES)
def test_a_scrub_that_keeps_lines_hides_the_same_shapes_with_every_line_at_its_number(text: str, secret: str) -> None:
    """Text a model is shown is also the text its quotes are looked for in, so a line must keep its number after a
    shape that ran over several lines, a private key's block, was replaced by one mark."""
    whole = f"before\n{text}\nafter\nlast"
    scrubbed, count = scrub_lines(whole)
    assert secret not in scrubbed and "[REDACTED" in scrubbed and count >= 1
    assert len(scrubbed.split("\n")) == len(whole.split("\n")), "no line moved"
    assert scrubbed.split("\n")[0] == "before" and scrubbed.split("\n")[-2:] == ["after", "last"]


def test_a_scrub_that_keeps_lines_leaves_text_with_no_secret_as_it_is() -> None:
    code = "token = get_token(request)\n\nclass TokenBucket: ...\n"
    assert scrub_lines(code) == (code, 0)


BEGINS = "-----BEGIN RSA " + "PRIVATE KEY-----"
BODY = "MIIEow0BAAKCAQEA7x1yQ9"


@pytest.mark.parametrize(
    ("text", "held"),
    [
        (f"{BEGINS}\n{BODY}\n", True),  # a key's own file
        (f"+{BEGINS}\n+{BODY}\n", True),  # a line a diff adds
        (f"-{BEGINS}\n", True),  # and one it removes
        (f"deploy:\n  key: |\n    {BEGINS}\n    {BODY}\n", True),  # a block in a YAML file
        ("-----BEGIN OPENSSH " + "PRIVATE KEY-----\n", True),
        ("-----BEGIN PGP " + "PRIVATE KEY BLOCK-----\n", True),
        (f'HEADER = "{BEGINS}"\n', False),  # code that names the line and holds no key
        ("-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A\n", False),
        ("-----BEGIN CERTIFICATE-----\n", False),
        ("def login(user):\n    return password(user)\n", False),
    ],
)
def test_a_text_holds_a_key_where_a_line_begins_with_a_private_keys_first_line(text: str, held: bool) -> None:
    """A key's own file has its first line at a line's start. Code that names that line in a string is still read."""
    assert holds_a_key(text) is held
