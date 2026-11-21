# Delta: auth

## MODIFIED Requirements

### REQ-AUTH-001: Sign in with email (case-insensitive)

The system SHALL let a registered user sign in with email and password, treating the email address as case-insensitive.

#### Scenario: Valid credentials, any case

- WHEN the user submits a valid email and password, regardless of case in the email
- THEN the system starts a session

### REQ-AUTH-002: Lock after failures

The system MUST lock an account after five failed attempts.

#### Scenario: Too many failures

- GIVEN four failed attempts
- WHEN a fifth attempt fails
- THEN the account is locked
- AND the user is told why
