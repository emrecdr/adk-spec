# Delta: notifications

## ADDED Requirements

### REQ-NOTIFICATIONS-003: Notify user of new device sign-in

The system SHALL notify a user through all configured channels whenever a sign-in is detected from a device not previously associated with their account.

#### Scenario: Sign-in from new device

- GIVEN a user with one or more notification channels configured
- AND the current device is not among those previously used by the user
- WHEN the user completes a new device sign-in
- THEN the system sends a notification to all their configured channels
- AND the notification includes identifying details of the device (e.g., device type, browser, location, and sign-in time)
