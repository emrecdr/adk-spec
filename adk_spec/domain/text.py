"""Text as every system reads it alike: one line break, no byte-order mark, no trailing blanks, and a fingerprint
taken after all three. A file saved on Windows with CRLF line ends then hashes as its LF twin does on macOS."""

from __future__ import annotations

import hashlib

BOM = "\ufeff"


def normalise(text: str) -> str:
    """`text` with a leading byte-order mark dropped, CRLF and a lone CR turned into LF, trailing spaces and tabs
    dropped from each line, and exactly one final newline. Nothing stays nothing."""
    unix = text.removeprefix(BOM).replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip(" \t") for line in unix.split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n" if lines else ""


def lines_of(text: str) -> list[str]:
    """The lines of `text`, broken at a newline alone: `str.splitlines` also breaks at a form feed and at U+2028,
    which put every later line one off. A final newline ends the last line and starts no empty one."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def sha256_of(text: str) -> str:
    """The fingerprint of `text`: `sha256:` and the hex digest of its normalised form in UTF-8."""
    return "sha256:" + hashlib.sha256(normalise(text).encode("utf-8")).hexdigest()
