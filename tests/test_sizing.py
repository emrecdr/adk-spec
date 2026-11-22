"""Sizing a request by rule: a short bug fix that names no risk is lean, and the model sizes everything else: a
request that may owe no spec, a long one, and one that may be strict."""

from __future__ import annotations

import pytest

from adk_spec.domain.sizing import tier_by_rule as sized


@pytest.mark.parametrize(
    "request_",
    [
        "Fix the crash when the cart is empty.",
        "Correct the wrong total shown after a refactor.",
        "fix: the export page fails",
        "Fix the error in the author list.",  # found by the cleanup review: "author" is no auth
    ],
)
def test_a_short_bug_fix_that_names_no_risk_is_lean(request_) -> None:
    assert sized(request_) == ("lean", "a short bug fix")


@pytest.mark.parametrize(
    "request_",
    [
        "Let users sign in with a passkey.",  # short, and no fix
        "Fix " + "the sign-in flow so that it supports passkeys and backup codes and " * 6,  # a fix verb, and long
        "x " * 400,  # found by an outside review: a long request may be strict, which only the model can say
        "Update the docs.",  # a request that may owe no spec at all
        "Fix the typo in the README's install section.",
        "Fix the wrong wording in the error message.",
        "Add typo-tolerant fuzzy search to the product catalog",
        "Fix login and add SSO support via SAML and OIDC",
        "Fix the button colour on the sign-in page.",  # a fix with no sign of a fault
        "Rewrite the README so that it explains the install, the new commands and how to add support. " * 7,
        # Found by an outside review and the cleanup review: a fix that touches security, money or data.
        "Fix authentication token validation bug",
        "Fix the crash when a password reset link expires.",
        "Fix the error in the payment retry when the card fails.",
        "Fix the wrong permission check on the admin page.",
        "Fix the crash in the data migration of old invoices.",
        "Fix the error when a secret is read from the vault.",
        "Fix data loss when the export fails.",
        "Fix the SQL injection error in search.",
        "Fix the wrong refund amount bug.",
        "Fix the crash when the login session cookie expires.",
        # Found by the code review: sign-in, single sign-on, keys and prices.
        "Fix the crash on the sign-in page.",
        "Fix the OAuth callback error.",
        "Fix the SSO redirect error.",
        "Fix the wrong price at checkout.",
        "Fix the error when an API key is missing.",
        "Fix the crash when a passkey is missing.",
        "Fix the error in the MFA prompt.",
    ],
)
def test_anything_else_is_sized_by_the_model(request_) -> None:
    assert sized(request_) is None
