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
