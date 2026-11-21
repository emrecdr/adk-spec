# notifications

## Purpose

Messages the system sends a user about their account.

## Requirements

### REQ-NOTIFICATIONS-001: Email on password change

The system SHALL email a user when the password of their account is changed.

#### Scenario: Password changed

- WHEN a user changes their password
- THEN the system sends an email to the account's address
- AND the email names the time of the change

### REQ-NOTIFICATIONS-002: Opt out of marketing

The system MUST NOT send a marketing message to a user who has opted out.

#### Scenario: Opted out

- GIVEN a user who has opted out of marketing
- WHEN a marketing campaign is sent
- THEN the user receives no message
