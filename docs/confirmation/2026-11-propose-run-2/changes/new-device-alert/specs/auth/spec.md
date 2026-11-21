# Delta: auth

## MODIFIED Requirements

### REQ-AUTH-001: Sign in with email

The system SHALL let a registered user sign in with email and password and trigger a notification upon sign-in from a previously unseen device.

#### Scenario: Valid credentials

- WHEN the user submits a valid email and password
- THEN the system starts a session

#### Scenario: Sign-in from new device

- GIVEN the user submits a valid email and password
- AND the device is not recognized as previously used for their account
- WHEN sign-in succeeds
- THEN a notification is triggered for new device access
