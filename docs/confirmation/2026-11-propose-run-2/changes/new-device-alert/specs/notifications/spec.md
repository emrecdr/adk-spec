# Delta: notifications

## ADDED Requirements

### REQ-NOTIFICATIONS-003: Email on new device sign-in

The system SHALL email a user when their account is signed in from a device not previously seen, specifying the time and device information, if available.

#### Scenario: New device access notification

- GIVEN a user signs in successfully
- AND the device is not previously recognized for this account
- WHEN the sign-in occurs
- THEN the system sends an email to the account's address about the new device sign-in
- AND the email specifies the time and device-related information, if available
