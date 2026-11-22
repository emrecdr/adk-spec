"""Sizing a request by rules: a short bug fix is lean, a long feature standard, and the model sizes everything else,
a request that may owe no spec above all."""

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


def test_a_long_request_or_one_naming_features_is_standard() -> None:
    assert sized("x " * 400) == ("standard", "a request of some length") == sized(FEATURE)


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
