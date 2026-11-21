"""The living spec's grammar: rendered canonically, parsed strictly, and fingerprinted a requirement at a time."""

from __future__ import annotations

import pytest
from samples import SPEC

from adk_spec.domain.model import GrammarError, Retired, Scenario
from adk_spec.domain.spec_md import fingerprint, parse_spec, render_requirement, render_spec
from adk_spec.domain.text import sha256_of

FENCE = "`" * 3
BOM = chr(0xFEFF)


def test_a_canonical_spec_survives_parse_and_render_unchanged() -> None:
    assert render_spec(parse_spec(SPEC)) == SPEC


def test_parse_reads_ids_names_statements_scenarios_and_the_retired() -> None:
    spec = parse_spec(SPEC)
    assert spec.capability == "auth" and spec.purpose == "Sign-in and session handling."
    assert [(r.id, r.name) for r in spec.requirements] == [
        ("REQ-AUTH-001", "Sign in with email"),
        ("REQ-AUTH-002", "Lock after failures"),
    ]
    assert spec.requirements[0].statement == "The system SHALL let a registered user sign in with email and password."
    steps = ("GIVEN four failed attempts", "WHEN a fifth attempt fails", "THEN the account is locked")
    assert spec.requirements[1].scenarios == (
        Scenario(name="Too many failures", steps=(*steps, "AND the user is told why")),
    )
    assert spec.retired == (Retired(id="REQ-AUTH-003", name="Remember me", change="drop-remember-me"),)


def test_a_hand_edited_spec_renders_to_the_canonical_form() -> None:
    messy = BOM + SPEC.replace("- WHEN", "- **when**").replace("## Purpose\n", "## Purpose\n\n\n").replace("\n", "\r\n")
    assert render_spec(parse_spec(messy)) == SPEC


def test_a_heading_inside_a_code_fence_stays_in_the_statement() -> None:
    inside = f"email and password.\n\n{FENCE}\n### not a heading\n## Retired\n{FENCE}"
    spec = parse_spec(SPEC.replace("email and password.", inside))
    assert len(spec.requirements) == 2 and "### not a heading\n## Retired" in spec.requirements[0].statement
    assert parse_spec(render_spec(spec)) == spec


def test_a_statement_keeps_its_paragraphs() -> None:
    two = SPEC.replace("email and password.", "email and password.\n\nA locked account cannot sign in.")
    assert parse_spec(two).requirements[0].statement.split("\n\n")[1] == "A locked account cannot sign in."
    assert render_spec(parse_spec(two)) == two


@pytest.mark.parametrize(
    ("broken", "line", "said"),
    [
        ("stray text\n" + SPEC, 1, "title"),
        (SPEC.replace("## Requirements", "## Requirments"), 7, "Requirments"),
        (SPEC.replace("### REQ-AUTH-001: Sign in with email", "### Sign in with email"), 9, "REQ-"),
        (SPEC.replace("- WHEN the user", "WHEN the user"), 15, "step"),
        (SPEC.replace("#### Scenario: Too many failures", "#### Notes"), 22, "Notes"),
        (SPEC.replace("- REQ-AUTH-003: Remember me (removed by drop-remember-me)", "- REQ-AUTH-003"), 31, "removed by"),
    ],
)
def test_a_spec_off_the_grammar_is_refused_with_its_line(broken: str, line: int, said: str) -> None:
    with pytest.raises(GrammarError) as caught:
        parse_spec(broken)
    assert caught.value.line == line and said in caught.value.message


def test_a_spec_missing_a_section_is_refused() -> None:
    with pytest.raises(GrammarError) as caught:
        parse_spec("# auth\n\n## Purpose\n\nSign-in.\n")
    assert "## Requirements" in caught.value.message


def test_a_fingerprint_is_of_the_canonical_block_alone() -> None:
    one, two = parse_spec(SPEC).requirements
    assert fingerprint(one) == sha256_of(render_requirement(one)) != fingerprint(two)
    assert fingerprint(parse_spec(SPEC.replace("\n", "\r\n")).requirements[0]) == fingerprint(one)
    other_purpose = SPEC.replace("Sign-in and session handling.", "Another purpose.")
    assert fingerprint(parse_spec(other_purpose).requirements[0]) == fingerprint(one)


def test_a_code_fence_that_is_never_closed_is_refused_at_its_opening_line() -> None:
    """Found by review: an unclosed fence swallowed every later requirement and the retired list, with no finding."""
    unclosed = SPEC.replace("email and password.", f"email and password.\n\n{FENCE}\nexample")
    with pytest.raises(GrammarError) as caught:
        parse_spec(unclosed)
    assert caught.value.line == 13 and "never closed" in caught.value.message


def test_text_before_the_first_section_is_refused_inside_a_fence_too() -> None:
    """Deferred by the review: fenced text between the title and the purpose parsed, and was gone on the next render."""
    with pytest.raises(GrammarError) as caught:
        parse_spec(SPEC.replace("# auth\n", f"# auth\n\n{FENCE}\nkept nowhere\n{FENCE}\n"))
    assert caught.value.line == 3
