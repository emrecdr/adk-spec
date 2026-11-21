# Notify user on sign-in from a new device

## Why

To quickly alert users of potentially unauthorized sign-ins, improving their ability to detect and respond to account security breaches.

## What changes

When a user successfully signs in from a device not previously seen for their account, an email notification will automatically be sent to inform them of new device access.

## Non-goals

No interface for users to review or manage known devices; no in-app or SMS notifications; does not modify authentication method or introduce two-factor authentication.

## Capabilities

- auth
- notifications

## Impact

Adds logic for device recognition and sends email notifications to users; this may surface new types of support requests related to account security incidents but does not change existing account management or UI workflows.

## Assumptions

If a device cannot be uniquely identified, it will be treated as new. Email is the only notification channel unless otherwise specified. Users will not be able to manage or view their known devices list, per answer on device management UI.
