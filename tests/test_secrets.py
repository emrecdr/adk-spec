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
        ("PuTTY-User-Key-File-" + "3: ssh-ed25519\nEncryption: none\n", True),  # PuTTY's own key file
        ("+PuTTY-User-Key-File-" + "2: ssh-rsa\n", True),
        ('PREFIX = "PuTTY-User-Key-File-' + '3: "\n', False),
        ("def login(user):\n    return password(user)\n", False),
    ],
)
def test_a_text_holds_a_key_where_a_line_begins_with_a_private_keys_first_line(text: str, held: bool) -> None:
    """A key's own file has its first line at a line's start. Code that names that line in a string is still read.
    Every key it finds holds one of the words a large file is searched for first: found by the fourth audit, the two
    were lists of their own, and a key a new pattern found would have been passed over by the search."""
    from adk_spec.domain.secrets import KEY_WORDS

    assert holds_a_key(text) is held
    assert not held or any(word in text.encode() for word in KEY_WORDS)


#: A private key's lines, as a person pastes part of one: base64, sixty-four characters a line.
KEY_BODY = [
    "b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW",
    "QyNTUxOQAAACDZ2ZmZ2ZmZ2ZmZ2ZmZ2ZmZ2ZmZ2ZmZ2ZmZ2ZmZ2ZmZ2ZmZ2QAAAJg",
]
PUTTY_BODY = [
    "AAAAC3NzaC1lZDI1NTE5AAAAIGZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZm",
    "AAAAIGZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZm",
]


@pytest.mark.parametrize(
    "text",
    [
        "Brief.\n-----BEGIN OPENSSH PRIVATE KEY-----\n" + "\n".join(KEY_BODY) + "\nmore prose after.\n",
        "Brief.\n-----BEGIN RSA PRIVATE KEY-----\n" + "\n".join(KEY_BODY) + "\n",
        "PuTTY-User-Key-File-3: ssh-ed25519\nEncryption: none\nComment: k\nPublic-Lines: 1\n"
        + PUTTY_BODY[0]
        + "\nPrivate-Lines: 1\n"
        + PUTTY_BODY[1]
        + "\nmore prose after.\n",
    ],
)
def test_a_key_with_no_footer_has_its_body_scrubbed_too(text: str) -> None:
    """Found by an outside audit: a key pasted without its footer lost its header to the scrub, and every line of its
    body went to the model and into the recordings."""
    scrubbed, _count = scrub(text)
    assert not any(line in scrubbed for line in (*KEY_BODY, *PUTTY_BODY))
    assert "more prose after." in scrubbed or not text.endswith("more prose after.\n")
    held, _count = scrub_lines(text)
    assert not any(line in held for line in (*KEY_BODY, *PUTTY_BODY)) and held.count("\n") == text.count("\n")


def test_a_footerless_key_of_many_lines_is_scrubbed_at_once() -> None:
    """The review's measure, kept: a header with key lines and no footer once took 45 s to scrub."""
    import time

    text = "-----BEGIN PRIVATE KEY-----\n" + (KEY_BODY[0] + "\n") * 2_000 + "the prose after it.\n"
    started = time.perf_counter()
    scrubbed, _count = scrub(text)
    assert time.perf_counter() - started < 1.0 and KEY_BODY[0] not in scrubbed and "the prose after it." in scrubbed


def test_a_header_only_mentioned_hides_no_code_after_it() -> None:
    """Found by review: with no footer, every short line after a header was taken for a key line, and a diff of
    code that only names a header lost its lines from the model."""
    diff = '+KEY = "-----BEGIN RSA PRIVATE KEY-----"\n+    return\n+    pass\n+print(done)\n'
    scrubbed, _count = scrub(diff)
    assert "+    return\n+    pass\n+print(done)" in scrubbed
    held, _count = scrub_lines(diff)
    assert "+    return" in held


def test_a_pgp_key_with_no_footer_hides_its_body_past_its_version_line() -> None:
    """Found by an outside audit: with no footer, an armour header other than Proc-Type or DEK-Info ended the key's
    lines, and the body after GnuPG's `Version:` line reached the model."""
    key = "-----BEGIN PGP PRIVATE KEY BLOCK-----\nVersion: GnuPG v2\n\nlQOYBGVvZXN0AQgAxyz0123456789abcdefABCDEF\n"
    for scrubbed, _count in (scrub(key), scrub_lines(key)):
        assert "lQOYBGVvZXN0" not in scrubbed


def test_a_key_quoted_in_markdown_hides_its_body() -> None:
    """Found by an outside audit: a key quoted with `>`, as a pasted issue or review holds it, had its header hidden
    and its body sent, with a footer or without."""
    body = "b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQ"
    for key in (
        f"> -----BEGIN OPENSSH PRIVATE KEY-----\n> {body}\n> {body}\n",
        f"> -----BEGIN OPENSSH PRIVATE KEY-----\n> {body}\n> -----END OPENSSH PRIVATE KEY-----\n",
        f"+> -----BEGIN OPENSSH PRIVATE KEY-----\n+> {body}\n+> > {body}\n",
    ):
        for scrubbed, _count in (scrub(key), scrub_lines(key)):
            assert body not in scrubbed, key


def test_a_file_quoting_a_key_is_known_to_hold_one() -> None:
    """Found by review: the whole-file check, which withholds a file and its diff from the model, still took a key's
    first line as the scrub did before quotes, so a hunk from the middle of a quoted key, with no header, was sent."""
    assert holds_a_key("Pasted from the issue:\n\n> -----BEGIN OPENSSH PRIVATE KEY-----\n> b3BlbnNzaC1rZXk\n")
    assert holds_a_key("+> > PuTTY-User-Key-File-3: ssh-ed25519\n")
    assert not holds_a_key('KEY = "-----BEGIN RSA PRIVATE KEY-----"\n')


def test_a_comment_line_after_a_header_named_in_code_is_not_taken_for_the_key() -> None:
    """Found by review: PGP's armour fields, allowed after every header to close the audit's bypass, took a line of code
    or prose opening with `Comment:` after a header only named, and hid it from the model."""
    code = '+KEY = "-----BEGIN RSA PRIVATE KEY-----"\n+\n+    Comment: this line of code is the change\n+x = 1\n'
    prose = "> The header `-----BEGIN RSA PRIVATE KEY-----` opens it.\n>\n> Comment: this is prose\n"
    for text, kept in ((code, "Comment: this line of code is the change"), (prose, "Comment: this is prose")):
        for scrubbed, _count in (scrub(text), scrub_lines(text)):
            assert kept in scrubbed


@pytest.mark.parametrize("mark", ["# ", "// ", " * ", "; ", "-- ", "% ", "+# ", "+    // ", "+-- "])
def test_a_key_behind_a_comment_mark_hides_its_body_and_its_file(mark) -> None:
    """Found by review: a key commented out in code, as a fixture or a config keeps one, had its header hidden and its
    body sent, and the file holding it was not withheld."""
    body = "b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQ"
    header, footer = "-----BEGIN OPENSSH PRIVATE KEY-----", "-----END OPENSSH PRIVATE KEY-----"
    for key in (f"{mark}{header}\n{mark}{body}\n{mark}{body}\n", f"{mark}{header}\n{mark}{body}\n{mark}{footer}\n"):
        for scrubbed, _count in (scrub(key), scrub_lines(key)):
            assert body not in scrubbed, key
        assert holds_a_key(key)


def test_a_key_opened_on_a_block_comments_first_line_is_known_and_hidden() -> None:
    """Found by review: a header after `/*`, its body behind ` * `, was not known to the whole-file check, and a hunk of
    its body alone reached the model."""
    body = "b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQ"
    key = f"/* -----BEGIN OPENSSH PRIVATE KEY-----\n * {body}\n * {body}\n */\n"
    assert holds_a_key(key)
    for scrubbed, _count in (scrub(key), scrub_lines(key)):
        assert body not in scrubbed


def test_a_commented_pgp_key_hides_its_body_past_its_blank_line() -> None:
    """A PGP key's armour ends at a blank line, a bare `#` where the key is commented out."""
    body = "lQOYBGVvZXN0AQgAxyz0123456789abcdefABCDEF"
    key = f"# -----BEGIN PGP PRIVATE KEY BLOCK-----\n# Version: GnuPG v2\n#\n# {body}\n# {body}\n"
    for scrubbed, _count in (scrub(key), scrub_lines(key)):
        assert body not in scrubbed


def test_code_after_a_header_only_named_keeps_its_comment_lines() -> None:
    """Found by review: a comment's mark taken as a quote's is, `#endif`, `// TODO`, ` */` or a bare `#` after a header
    named in a string were taken for the key's lines, and hidden from every stage."""
    named = (
        'BEGIN = "-----BEGIN RSA PRIVATE KEY-----"\n#endif\n// TODO\n */\n# noqa\n'
        'END = "-----END RSA PRIVATE KEY-----"\n'
    )
    bare = '+KEY = "-----BEGIN RSA PRIVATE KEY-----"\n+#\n+// \n+ *\n+x = 1\n'
    for text, kept in ((named, ("#endif", "// TODO", " */", "# noqa")), (bare, ("+#\n", "+// ", "+ *", "+x = 1"))):
        for scrubbed, _count in (scrub(text), scrub_lines(text)):
            assert all(line in scrubbed for line in kept), scrubbed


@pytest.mark.parametrize(
    "secret",
    [
        "//registry.npmjs.org/:_authToken=0b1c2d3e-4f5a-" + "6b7c-8d9e-0f1a2b3c4d5e",
        "//npm.example.com/:_auth=dXNlcjpwYXNzMTIzNDU2Nzg=",
        "//pkgs.dev.azure.com/org/_packaging/feed/npm/registry/:_password=cGFzczEyMzQ1Njc4OTA=",
        "//registry.npmjs.org/:_password=aHVudGVyaHVudGVy",
        '//x.example.com/:_auth="YWJjOmRlZjQ1Ng1234=="',
    ],
)
def test_an_npmrc_registry_credential_is_hidden(secret: str) -> None:
    """Found by an outside audit: a registry line of `.npmrc` matched no shape, and a tracked one reached a model.
    Found by the code review: a value with no digit, or in quotes as npm reads them, still did; the key names a
    credential, so no digit is asked of its value."""
    hidden, count = scrub(f"+{secret}\n")
    assert count == 1 and secret.split("=", 1)[1] not in hidden and "[REDACTED]" in hidden


def test_an_npmrc_line_that_names_a_variable_is_kept() -> None:
    line = "//registry.npmjs.org/:_authToken=${NPM_TOKEN}\n"
    assert scrub(line) == (line, 0)


#: A value as a `.env`, a compose file or a script holds one: eight characters or more, holding a digit.
VALUE = "hunter2" + "pass9"


@pytest.mark.parametrize(
    "line",
    [
        f"DB_PASSWORD={VALUE} # prod",
        f"password: {VALUE}  # rotate",
        f"  - POSTGRES_PASSWORD={VALUE}",
        f"+  - SECRET_KEY={VALUE}",
        f"set API_TOKEN={VALUE}",
    ],
)
def test_a_credential_line_with_a_comment_or_a_list_mark_is_hidden(line: str) -> None:
    """Found by the audit of 25 November: a value followed by a comment, on a compose file's list item or after
    Windows' `set` matched no shape, and a tracked one reached a model and a committed report."""
    hidden, count = scrub(f"{line}\n")
    assert VALUE not in hidden and count == 1


@pytest.mark.parametrize("line", [f"mysql --password={VALUE} -h db", f"docker login --token {VALUE} registry"])
def test_a_secret_option_of_a_command_is_hidden(line: str) -> None:
    """Found by the audit of 25 November: an option of a command, in a script or a CI file, matched no shape."""
    hidden, count = scrub(f"{line}\n")
    assert VALUE not in hidden and count == 1 and hidden.startswith(line.split(VALUE)[0])


@pytest.mark.parametrize(
    "line",
    [
        "curl --token $TOKEN https://x",
        "login --password <pass>",
        "serve --max-tokens 4096",
        "token = get_token(request)  # why it is read here",
        "API_TOKEN=  # set in CI",
    ],
)
def test_an_option_or_a_line_holding_no_value_is_kept(line: str) -> None:
    assert scrub(f"{line}\n") == (f"{line}\n", 0)


#: A key's last line, built from parts so that no line of this file is one.
FOOTER = "-----END RSA " + "PRIVATE KEY-----"


@pytest.mark.parametrize(
    "text",
    [
        f'KEY = (\n    "{BEGINS}\\n"\n    "{KEY_BODY[0]}\\n"\n    "{FOOTER}\\n"\n)\n',  # concatenated literals
        f'KEY = """{BEGINS}\n{KEY_BODY[0]}\n{FOOTER}"""\n',  # a triple-quoted string
        f'deploy:\n  key: "{BEGINS}\\n{KEY_BODY[0]}\\n{FOOTER}"\n',  # a YAML value holding `\n`
        f"const key = '{BEGINS}\\n' +\n  '{KEY_BODY[0]}\\n' +\n  '{FOOTER}';\n",  # JavaScript's `+`
        f'+    "{BEGINS}\\n"\n+    "{KEY_BODY[0]}\\n"\n',  # the lines a diff adds of the first
    ],
)
def test_a_key_held_in_a_string_is_withheld(text: str) -> None:
    """Found by the audit of 25 November: a key a test holds in a string had its header hidden and its body sent, as
    `holds_a_key` asked for the header at a line's start; the file is now shown in no piece."""
    assert holds_a_key(text)


def test_code_naming_a_header_then_a_long_path_is_read() -> None:
    code = f'HEADER = "{BEGINS}"\nLOADER = "src/main/java/com/example/security/KeyLoader"\nFOOTER = "{FOOTER}"\n'
    assert not holds_a_key(code)
