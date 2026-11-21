# Notify Users of New Device Sign-In

## Why

To improve account security by quickly alerting users of unauthorized or unexpected access, giving them opportunity to react to possible compromise.

## What changes

When a sign-in occurs from a device not previously associated with the user's account, the user will receive a notification through all their configured channels, alerting them to the event and providing relevant device details.

## Non-goals

No changes to device removal UI, session length policies, or notification channel management.

## Capabilities

- auth
- notifications

## Impact

Affects notification system (triggers and templates), authentication/session logic, and device tracking datastore. May increase support queries and operational monitoring requirements.

## Assumptions

Assumes device recognition is reliable using current approach (device ID + fingerprint + user agent). [NEEDS CLARIFICATION: Should admins or support staff receive notifications, or only end-users?]
