"""Text normalisation, fingerprints and the identifier grammar: the same answer on every system."""

from __future__ import annotations

import pytest

from adk_spec.domain.ids import capability_of, next_requirement_id, number_of, requirement_id, slug_problem
from adk_spec.domain.text import lines_of, normalise, sha256_of


def test_crlf_a_bom_and_trailing_spaces_fingerprint_as_their_lf_twin() -> None:
    lf = "### REQ-AUTH-001: Sign in\n\nThe system SHALL sign in.\n"
    twins = (lf.replace("\n", "\r\n"), "\ufeff" + lf, lf.replace("in.\n", "in.  \n"), lf + "\n\n")
    assert {sha256_of(twin) for twin in twins} == {sha256_of(lf)}
    assert sha256_of(lf).startswith("sha256:") and len(sha256_of(lf)) == 71


def test_normalise_ends_in_one_newline_and_leaves_nothing_empty_changed() -> None:
    assert normalise("a\r\nb\r\n\r\n\n") == "a\nb\n" and normalise("a\rb") == "a\nb\n" and normalise("") == ""


def test_lines_break_at_a_newline_alone() -> None:
    assert lines_of("a\x0cb\u2028c\nd") == ["a\x0cb\u2028c", "d"]


@pytest.mark.parametrize("slug", ["auth", "billing-export", "oauth-2", "a1", "a"])
def test_a_slug_is_lowercase_ascii_words_joined_by_hyphens(slug: str) -> None:
    assert slug_problem(slug) is None


@pytest.mark.parametrize(
    "slug",
    ["", "Auth", "auth_export", "-auth", "auth-", "2fa", "auth--x", "é", "a" * 41, "con", "nul", "com1", "aux", "prn"],
)
def test_a_slug_no_folder_holds_safely_is_refused_with_its_reason(slug: str) -> None:
    assert isinstance(slug_problem(slug), str)


def test_a_requirement_id_carries_its_capability_and_number() -> None:
    assert requirement_id("billing-export", 7) == "REQ-BILLING-EXPORT-007"
    assert capability_of("REQ-BILLING-EXPORT-007") == "billing-export" and number_of("REQ-BILLING-EXPORT-007") == 7
    assert capability_of("REQ-OAUTH-2-001") == "oauth-2" and requirement_id("auth", 1000) == "REQ-AUTH-1000"
    assert capability_of("FR-001") is None and capability_of("REQ-auth-001") is None


def test_the_next_id_never_reuses_a_number() -> None:
    taken = ["REQ-AUTH-001", "REQ-AUTH-004", "REQ-BILLING-009"]
    assert next_requirement_id("auth", taken) == "REQ-AUTH-005"
    assert next_requirement_id("search", taken) == "REQ-SEARCH-001"
