# Delta: auth

## ADDED Requirements

### REQ-AUTH-004: Track known devices

The system SHALL track known devices for each user by device ID, fingerprint, and user agent.

#### Scenario: Associate device on first sign-in

- WHEN a user signs in from a device not previously associated with their account
- THEN the system records a new device entry for that user, containing at minimum: device ID, fingerprint, and user agent
