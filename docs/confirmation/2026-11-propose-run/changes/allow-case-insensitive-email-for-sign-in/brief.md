# Allow Case-Insensitive Email for Sign-in

## Why

Users expect email input for authentication to be case-insensitive; rejecting capitalized emails is a common frustration and harms usability.

## What changes

Sign-in will treat user-entered email addresses as case-insensitive, normalizing input before comparison to stored values.

## Non-goals

Does not affect how email addresses are stored or used elsewhere beyond authentication.

## Capabilities

- auth

## Impact

Authentication code handling sign-in is affected; user experience improves for users typing mixed-case emails.

## Assumptions

The system stores email addresses in lower-case form on registration. [NEEDS CLARIFICATION: Are sign-ups also case-sensitive?]
