# The `strict` tier

Design for phase 13 of adk-spec. Written on 22 November 2026.

**What the owner decided, and when.** 22 November 2026, in a dialog, all as recommended:

- **A strict `propose` writes the brief and the specs, then stops** before the design and the tasks, for a person to
  read; `adk-spec plan <id>` goes on. No new command.
- **Two different names approve a strict change**: `approve --by A`, then `approve --by B`. An edit in between
  voids both. Names stay recorded claims, as today.
- **Warnings of the check block a strict approval too**, and `--override` sets no blocking finding aside on strict.

From the report: a strict change always owes a design. Everything else is the builder's call, listed at the end.

## Intent, and why

`strict` is for a change with many capabilities, a high risk of regression or an audit trail it owes. It has been
read as `standard` since phase 2, which gave less than was asked. Kiro keeps its step-by-step flow for this kind of
work and one pass for the rest; this tier is that.

## How it works

```
adk-spec propose "Move billing to the new ledger" --tier strict
wrote     .spec/changes/move-billing.../, a strict draft
          brief.md, specs/billing/spec.md
plan      waits: a strict change is read first. Read brief.md and the specs, then `adk-spec plan <id>`
next      run `adk-spec plan move-billing...`

adk-spec plan move-billing...          design.md and tasks.md: a design is always owed
adk-spec approve move-billing... --by ana
approved  once, by ana: a strict change is approved by two names. Another approves it next
adk-spec approve move-billing... --by ben
approved  `move-billing...` by ben, after ana: 4 files recorded
```

- `strict` is a tier a person may choose (`--tier strict`, `default_tier = "strict"`), and the sizing model's
  `strict` is taken as it is.
- **A design is always owed**: a strict change records that it owes one, as a brief that says so does, and a change
  that owes a design and has none cannot be approved: `plan` drafts it.
- **The stop.** `propose` on a strict change, a revision included, writes the brief and the specs and drafts no plan;
  the next line says `plan`.
- **Two approvals.** The first is recorded and the change stays a draft, with one approval of two. The second, by
  another name and while the first still covers the files, approves it. The same name twice is refused. An edit, a
  rebase or a revision voids the first, as any approval.
- **Findings.** A strict approval stops on a warning as `approve --strict` does, and `--override` on a strict change
  is refused before anything is spent.

## Anti-goals

- A strict change is approved by one name, or by the same name twice.
- A strict change is approved with no design, or with a warning of the check set aside.
- `propose` drafts a strict change's design and tasks before a person read its brief and specs.

## Decided by the builder, for the owner to check

1. A change of any tier that owes a design and has none cannot be approved: a strict one always owes one.
2. Where the work began is recorded at the second approval, when the change is approved.
3. `verify` and `archive` are as for standard.

## How it is proven

Offline: `--tier strict` and the config accepted; the sizing model's strict kept; a strict `propose` stops after the
specs and `plan` drafts a design; the same name refused for the second approval; two names approve; an edit between
voids the first; a warning blocks; `--override` refused; a design owed and missing blocks with `plan` as the next
step.
