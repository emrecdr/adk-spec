# Sizing by rules, and revising a change by instruction

Design for phases 10 and 11 of adk-spec, built as one. Written on 22 November 2026.

**What the owner decided, and when.** 22 November 2026, in a dialog:

- "do phase 10 & 11 together in 1 go", where I had recommended skipping phase 10 for its small benefit.
- A change is revised by **`propose "<instruction>" --id <its id>`**: no new command.
- A revision **keeps the person's hand edits and changes only what the instruction asks**; adk-spec lists the
  requirements added, changed and dropped, and an approved change must be approved again.

Everything else is the builder's call, listed at the end.

## Part 1: sizing by rules

**Removed** on 22 November 2026, on the owner's decision: the rule was built, narrowed by three reviews, and taken out,
since its list of risk words missed some in each and a miss sized a risky fix lean. See the roadmap's phase 10.

`propose` asks a model for the tier of every request unless `--tier` names one. With a tier known the sizing call is
skipped, and the capabilities come from the brief, so a rule need decide only the tier.

- **Lean, by rule:** a request of at most 240 characters that opens with a fix-shaped verb: fix, correct, rename,
  reword, bump, remove, typo, update the wording, adjust.
- **Standard, by rule:** a request of 600 characters or more, or of 200 or more that names two or more feature-shaped
  words: add, support, integrate, migrate, introduce, new, replace, redesign.
- **Otherwise** the model sizes it, as today, `none` included: a rule never decides that a request owes no spec.
- `propose` says the tier it took by rule, `sized     lean, by rule: a short fix`, so `--tier` can overrule it next
  time. The rules are code in `domain/`, each with its reason.

## Part 2: revising a change by instruction

```
adk-spec propose "also support backup codes" --id passkeys
revising  passkeys, a lean draft: its brief, its deltas and its tasks, kept where the instruction does not reach
revised   added REQ-AUTH-005; changed REQ-AUTH-004; dropped nothing
wrote     .spec/changes/passkeys/brief.md
          .spec/changes/passkeys/specs/auth/spec.md
          .spec/changes/passkeys/tasks.md
next      approve again: brief.md, specs/auth/spec.md, tasks.md changed since the approval
```

- With `--id` naming a change that exists, `propose` revises it. A draft or an approved change can be revised; a
  verified or archived one is refused, with what to do instead.
- The brief and the deltas stages are given the change's files as they stand, hand edits included, and the
  instruction as the request, with one guide sentence each: revise what stands; change only what the request asks;
  keep every other line as it is. Triage is not asked: the change has its tier.
- **IDs stay.** A requirement the revision keeps by name keeps its ID; a new one gets a new ID; no ID is reused.
- **What changed is said**, by comparing the requirements before and after: added, changed, dropped.
- **The plan follows.** Tasks are drafted again for the revised requirements, as `propose` drafts them, unless a task
  is ticked, in which case `tasks.md` is kept and the line says to run `plan <id> --replace`. `context.md` is kept.
- The approval stands recorded and is stale, as after any edit: `approve` again, as the next line says.
- Questions the revised brief leaves open are asked as they are for a new change.

## Anti-goals

- A requirement keeps its name and gets a new ID.
- A hand edit outside what the instruction asks is lost.
- A ticked task is lost.
- A rule sizes a request that owes no spec, or puts a long feature request on the lean path.

## Decided by the builder, for the owner to check

1. The rules' words and lengths above, conservative by design; anything else goes to the model.
2. Verified and archived changes are not revised.
3. IDs are matched by requirement name.
4. A ticked task keeps `tasks.md` as it is.

## How it is proven

Offline, on the fake model: rules on fix-shaped, feature-shaped and other requests; a revision that adds, changes and
drops a requirement, its IDs, its list and its stale approval; a hand edit kept through a revision the model returns
unchanged; a ticked task kept; a verified change refused; the brief and deltas stages shown the files as they stand.
