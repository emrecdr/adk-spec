"""Sizing a request by rules: a short fix is lean, a long feature standard, and the model sizes everything else."""

from __future__ import annotations

import pytest

from adk_spec.domain.sizing import tier_by_rule as sized

FEATURE = "Add passkey sign-in, support backup codes and replace the old password reset flow. " * 3


@pytest.mark.parametrize(
    "request_",
    ["Fix the typo in the README's install section.", "Rename the --no-input flag to --quiet.", "fix: a typo in help"],
)
def test_a_short_fix_is_lean(request_) -> None:
    assert sized(request_) == ("lean", "a short fix")


def test_a_long_request_or_one_naming_features_is_standard() -> None:
    assert sized("x " * 400) == ("standard", "a request of some length") == sized(FEATURE)


@pytest.mark.parametrize(
    "request_",
    [
        "Let users sign in with a passkey.",  # short, and no fix: the model sizes it
        "Fix " + "the sign-in flow so that it supports passkeys and backup codes and " * 6,  # a fix verb, and long
        "Update the docs.",  # a request that may owe no spec at all: never decided by a rule
    ],
)
def test_anything_else_is_sized_by_the_model(request_) -> None:
    assert sized(request_) is None
