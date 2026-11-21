# How often the labelled set's faults are caught

Measured 2026-11-21T20:47:31+00:00 on gpt-4.1 on copilot, 3 runs a case, at commit f18cfd23e0e5.

| Case | Command | Caught | Blocking on nothing planted | Left out, no such quote | Tokens a run | Seconds a run | Failed |
|---|---|---|---|---|---|---|---|
| `contradiction` | check | 1/3 | 2 | 1 | 1,323 | 5.6 | 0 |
| `ambiguity` | check | 3/3 | 1 | 0 | 1,245 | 11.8 | 0 |
| `no-task` | check | 3/3 | 0 | 0 | 0 | 0.0 | 0 |
| `constitution` | check | 0/3 | 2 | 1 | 1,179 | 10.8 | 0 |
| `clean` | check | nothing planted | 4 | 0 | 1,199 | 8.7 | 0 |
| `half-done` | verify | 3/3, 3/3 | 0 | 0 | 1,285 | 13.5 | 0 |

Caught: in how many runs a finding on the planted fault's file named it; one figure a planted fault.
Blocking on nothing planted: blocking findings that match no planted fault, over all runs; an upper bound on
the false ones, since a model may find a real fault nobody planted.

## Blocking on nothing planted

- `contradiction`, run 1: `check.gap` brief.md: Users can register a passkey and sign in with it. The brief promises 'Users can register a passkey' but no requirement or task covers user registration of a passkey; it only covers sign-in.
- `contradiction`, run 2: `check.gap` brief.md: Users can register a passkey and sign in with it. The brief states 'Users can register a passkey' but there is no requirement covering passkey registration; only signing in with a passkey is specified. Add a requirement for passkey registration.
- `ambiguity`, run 3: `check.gap` brief.md: Sign-in responds faster. The brief promises 'sign-in responds faster', but no metric or threshold for 'fast' response is specified in the requirement REQ-AUTH-003, making it unclear what 'fast' means or how to test it. Define a concrete measure of 'fast' (e.g., specific response time in milliseconds
- `constitution`, run 3: `check.gap` brief.md: Users can register a passkey and sign in with it. The brief promises that users can register a passkey, but no requirement describes or ensures registration of a passkey. Add a requirement and related tasks for registering a passkey.
- `constitution`, run 3: `check.gap` tasks.md: T001 [REQ-AUTH-003] Implement the passkey handler The task only implements a passkey sign-in handler, but does not cover registering a passkey. Add a task for passkey registration as promised in the brief.
- `clean`, run 1: `check.gap` brief.md: Users can register a passkey and sign in with it. The brief promises that users can register a passkey, but there is no requirement or task about registering a passkey; only signing in with one.
- `clean`, run 2: `check.gap` brief.md: Users can register a passkey and sign in with it. The brief promises that users can register a passkey, but there is no requirement covering passkey registration. Add a requirement for passkey registration.
- `clean`, run 3: `check.gap` brief.md: Users can register a passkey and sign in with it. Password sign-in stays as it is. The brief says 'Users can register a passkey' but there is no requirement covering registration of a passkey, only sign-in with one. Add a requirement for passkey registration or clarify non-goal.
- `clean`, run 3: `check.gap` specs/auth/spec.md: ### REQ-AUTH-003: Sign in with a passkey

The system SHALL let a user sign in with a passkey. There is no scenario or requirement for registering a passkey, only for signing in with one. Add requirement for passkey registration if intended.

## Missed

- `contradiction`, run 1: wanted check.contradiction or check.gap on brief.md or specs/auth/spec.md; found check.gap on brief.md
- `contradiction`, run 2: wanted check.contradiction or check.gap on brief.md or specs/auth/spec.md; found check.gap on brief.md
- `constitution`, run 1: wanted check.constitution or check.gap on tasks.md; found check.gap on brief.md
- `constitution`, run 2: wanted check.constitution or check.gap on tasks.md; found check.gap on brief.md; check.ambiguity on specs/auth/spec.md
- `constitution`, run 3: wanted check.constitution or check.gap on tasks.md; found check.gap on brief.md; check.gap on tasks.md

## Read by hand, and decided

Run on the owner's go-ahead on 21 November 2026 ("Run it again"), with the script that keeps what it cannot place:
15 model calls, about 18,700 tokens. No run failed.

**What it shows, which the first measurement could not.**

- **The labelled set itself held a fault nobody planted.** The brief every case shares said "Users can register a
  passkey and sign in with it", and no requirement covers registering one. Eight of the nine blocking findings on
  "nothing planted" name exactly that, in the clean case too. They are right. The ninth names the planted ambiguity
  in the brief, where the case expected it in the delta.
- **So the clean case was not clean,** and the first measurement's three unplaced findings were very likely this
  gap as well. Nothing here is evidence of a false finding.
- **The model mostly gives one finding a run.** Where it named the accidental gap, it left the planted fault
  unsaid: the contradiction was caught in one run of three, and the broken rule in none, where the first
  measurement had two and three. The half-done work was again judged rightly in all three runs, and the ambiguity
  found in all three.
- **Three runs do not make a rate.** The same case moved from three of three to none of three between two
  measurements an hour apart.
- Two findings were left out for quoting text that is not in the file. Their wording was not kept, so nobody can
  say whether one was a planted fault quoted a word off.

**Decided.**

- The set is corrected: the shared brief promises what its delta delivers, and no more
  (`test_the_clean_case_promises_nothing_its_delta_does_not_deliver`).
- The script keeps the wording of a finding left out for its quote, as it keeps the others.
- The check stage is to be told to report every fault it finds, not the first. That changes its instruction, so it
  is done in plan 4 and measured there, not tuned here.
- No severity rule is changed: nothing that blocked was wrong.
- The next measurement runs more than three times a case, or reports a range.

