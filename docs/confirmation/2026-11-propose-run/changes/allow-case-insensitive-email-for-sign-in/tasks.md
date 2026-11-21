# Tasks

## 1. Case-insensitive email for sign-in

- [ ] T001 [REQ-AUTH-001] Add or update sign-in tests to cover case-insensitive email matching on valid credentials.
  - files: tests/auth/test_signin.py
  - verify: pytest tests/auth/test_signin.py --tb=short
- [ ] T002 [REQ-AUTH-001] Update sign-in logic to normalize (lowercase) input emails before authentication checks.
  - files: auth/signin.py
  - verify: pytest tests/auth/test_signin.py --tb=short
