"""Sizing a request by rule: a short bug fix that names no risk is lean, and the model sizes everything else: a
request that may owe no spec, a long one, and one that may be strict."""

from __future__ import annotations

import pytest

from adk_spec.domain.sizing import tier_by_rule as sized

FEATURE = "Add passkey sign-in, support backup codes and replace the old password reset flow. " * 3


@pytest.mark.parametrize(
    "request_",
    ["Fix the crash when the cart is empty.", "Correct the wrong total shown after a refund.", "fix: login fails"],
)
def test_a_short_bug_fix_is_lean(request_) -> None:
    assert sized(request_) == ("lean", "a short bug fix")


def test_a_long_request_is_sized_by_the_model_which_alone_may_call_it_strict() -> None:
    """Found by an outside review: a long request was sized standard by rule, and the model, which alone can call a
    change strict, was never asked."""
    assert sized("x " * 400) is None and sized(FEATURE) is None


@pytest.mark.parametrize(
    "request_",
    [
        "Fix authentication token validation bug",  # found by the outside review: a security fault, sized lean
        "Fix the crash when a password reset link expires.",
        "Fix the error in the payment retry when the card fails.",
        "Fix the wrong permission check on the admin page.",
        "Fix the crash in the data migration of old invoices.",
        "Fix the error when a secret is read from the vault.",
    ],
)
def test_a_fix_that_names_a_risk_is_sized_by_the_model(request_) -> None:
    assert sized(request_) is None


@pytest.mark.parametrize(
    "request_",
    [
        "Let users sign in with a passkey.",  # short, and no fix: the model sizes it
        "Fix " + "the sign-in flow so that it supports passkeys and backup codes and " * 6,  # a fix verb, and long
        "Update the docs.",  # a request that may owe no spec at all
        # Found by the review: each of these owes no spec, or is a feature, and a rule took it as a lean fix.
        "Fix the typo in the README's install section.",
        "Fix the wrong wording in the error message.",
        "Add typo-tolerant fuzzy search to the product catalog",
        "Fix login and add SSO support via SAML and OIDC",
        "Fix the button colour on the sign-in page.",  # a fix with no sign of a fault: the model says
        ("Rewrite the README so that it explains the install, the new commands and how to add support. " * 7),
    ],
)
def test_anything_else_is_sized_by_the_model(request_) -> None:
    assert sized(request_) is None
