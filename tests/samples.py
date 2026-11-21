"""Canonical sample files, shared by the tests of the grammars, the validator, the merge and the command."""

SPEC = """\
# auth

## Purpose

Sign-in and session handling.

## Requirements

### REQ-AUTH-001: Sign in with email

The system SHALL let a registered user sign in with email and password.

#### Scenario: Valid credentials

- WHEN the user submits a valid email and password
- THEN the system starts a session

### REQ-AUTH-002: Lock after failures

The system MUST lock an account after five failed attempts.

#### Scenario: Too many failures

- GIVEN four failed attempts
- WHEN a fifth attempt fails
- THEN the account is locked
- AND the user is told why

## Retired

- REQ-AUTH-003: Remember me (removed by drop-remember-me)
"""

DELTA = """\
# Delta: auth

## ADDED Requirements

### REQ-AUTH-004: Sign in with a passkey

The system SHALL let a user sign in with a passkey.

#### Scenario: Registered passkey

- WHEN the user presents a registered passkey
- THEN the system starts a session

## MODIFIED Requirements

### REQ-AUTH-002: Lock after failures

The system MUST lock an account after three failed attempts.

#### Scenario: Too many failures

- WHEN a third attempt fails
- THEN the account is locked

## REMOVED Requirements

### REQ-AUTH-001: Sign in with email

Reason: Passwords are retired in favour of passkeys.
"""

BRIEF = """\
# Sign in with a passkey

## Why

Passwords are the top source of account takeovers.

## What changes

Users can register a passkey and sign in with it.

## Non-goals

No change to session length.

## Capabilities

- auth

## Impact

The sign-in page and the session service.

## Assumptions

Browsers in scope support WebAuthn.
"""

TASKS = """\
# Tasks

## 1. Passkey sign-in

- [ ] T001 [REQ-AUTH-004] Write the failing passkey sign-in test
  - files: tests/test_passkey.py
  - verify: uv run pytest tests/test_passkey.py
- [x] T002 [P] [REQ-AUTH-004, REQ-AUTH-002] Implement the passkey handler
  - files: src/auth/passkey.py, src/auth/lockout.py
  - verify: uv run pytest tests/test_passkey.py tests/test_lockout.py
- [ ] T003 Update the sign-in page copy
  - verify: read the page
"""


def tasks_for(*ids: str) -> str:
    """A task list that serves each of `ids` with one task: what a change needs to pass the coverage of its own
    requirements, where a test is about something else."""
    tasks = [
        f"- [ ] T{n:03d} [{req}] Do the work of {req}\n  - verify: read the result\n" for n, req in enumerate(ids, 1)
    ]
    return "# Tasks\n\n## 1. Work\n\n" + "".join(tasks)
