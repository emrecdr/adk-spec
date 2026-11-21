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
