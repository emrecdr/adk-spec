# Design

## Context

Currently, the authentication (auth) system fulfills requirements for email/password sign-in and account locking after failed attempts. The notifications system covers password-change and marketing messages. There is no support for device tracking, nor for user notifications on new device sign-ins. Device recognition relies on a combination of device ID, fingerprint, and user agent. Notification channels are already configured per user. Coding standards, domain context, and repository organization are stable and must not be changed outside the scope of this feature. Non-goals explicitly rule out any change to device removal UX, session duration, or channel management UI.

## Goals

- Device tracking per user for device ID, fingerprint, and user agent on first sign-in from a new device.
- Detect and distinguish new device sign-ins from previous ones reliably.
- Trigger timely notification to the user, through all their configured notification channels, containing device/browser/location/time details.
- No changes to device management UI, session expiry, or channel management workflows.
- No requirement to notify administrators or support; only end users are alerted.

## Decisions

1. Device Tracking Storage: Chosen to use the current auth-backed user datastore for device records per user, as opposed to a separate service, to minimize implementation and maintain alignment with existing user/session flows. Explored using a separate microservice but rejected for added operational complexity outside scope and no significant scaling benefit at this time.
2. Device Identification: Will track devices via the combination of device ID, fingerprint, and user agent, using the existing approach for consistency and to avoid introducing a new mechanism without known weaknesses. Considered using only device ID or adding IP geolocation to the core identifier, but single-value approaches are weaker and location is best surfaced as an extra notification detail (see below).
3. Notification Trigger: The notification is triggered after successful sign-in and recognition that this device is new. Considered only alerting on suspicious behavior, but the requirement mandates any new device sign-in. Triggering before session establishment was rejected due to ambiguity if the sign-in would succeed (e.g., 2FA in future).
4. Notification Content: The notification will include device type (parsed from fingerprint/user agent), browser, location (if inferrable), and sign-in time. Considered omitting location or relying only on raw metadata, but parsed/clear content best supports the user’s awareness and remediation ability.
5. Notification Channeling: The notification is sent to all configured channels. No option to target only certain channels, per requirement. Considered batching or throttling but rejected in favor of real-time alerts for every new device occurrence.
6. Admin Notification: End-user only, not admins or support, as clarified by scoping and to concentrate on personal account security.

## Risks

- Device fingerprinting inconsistency across browsers or devices could cause false positives—users may be notified of a "new device" on upgrades or browser changes. The risk is limited by the current device tracking fidelity and improved by continued tuning.
- Privacy concern if location inference is imprecise; the risk is limited by including a caveat ("Approximate location") or enabling opt-out (out of scope for now).
- Increased support desk burden due to more alerts. Limited by user-initiated configuration and possible help documentation.
- Notification delivery failures (e.g., email issues) could leave users uninformed. Mitigated by using all configured channels, but there remains possibility of all channels failing (unchanged from existing notification requirements).
- Data storage growth as device entries accumulate per user; bounded by possible future housekeeping strategies, but unchecked in this phase per scope.
