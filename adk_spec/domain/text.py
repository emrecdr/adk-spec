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


#: A quote shorter than this, once its spaces are settled, points at nothing: `the` is in every file.
QUOTE_MIN_CHARS = 8


def flat(text: str) -> str:
    """`text` on one line, every run of whitespace read as one space."""
    return " ".join(text.split())


def plain(text: str) -> str:
    """A model's wording as it may be printed and written: on one line, every character that is no printable one,
    an escape or a bell among them, read as a space."""
    return flat("".join(char if char.isprintable() else " " for char in text))


def quoted_at(quote: str, text: str) -> int | None:
    """The line of `text`, counted from 1, where `quote` starts, or nothing where `text` does not hold it. The two
    are compared with every run of whitespace read as one space, so a line break or an indent a model changed does
    not lose a quote, and a quote may run over lines. One too short to point at anything is in no text.

    This is the one test of whether what a model points to is there: a finding's quote in a file, and a verdict's
    in the lines of a diff."""
    wanted = flat(quote)
    if len(wanted) < QUOTE_MIN_CHARS:
        return None
    starts: list[tuple[int, int]] = []  # where each line that holds a word starts in the flat text, and its number
    pieces: list[str] = []
    offset = 0
    for number, line in enumerate(lines_of(normalise(text)), 1):
        if piece := flat(line):
            starts.append((offset, number))
            pieces.append(piece)
            offset += len(piece) + 1
    at = " ".join(pieces).find(wanted)
    if at < 0:
        return None
    return max(number for start, number in starts if start <= at)
