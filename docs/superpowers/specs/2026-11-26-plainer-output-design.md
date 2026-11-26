# Plainer output: phase 22

Designed on 26 November 2026 from the audit of 25 November (`docs/reports/2026-11-25-codebase-audit.md`, U1-U8, step
4 of its order). The owner said "proceed as recommended" to building them, three of which change printed lines that
tests pin. Each was checked again in the code before the design. The golden rule holds: no command or flag is added,
and each change makes a line shorter or plainer.

## Goals

1. **U1: progress in plain words, with the time.** A model call starting is said as what it does, not its stage's
   key, with the time since the command began: `working   reading the code  0:47`. The keys: triage "sizing the
   request", scout "choosing what to read", survey "reading the code", review "checking the reading", brief "writing
   the brief", deltas "writing the requirements", design "writing the design", tasks "writing the tasks", check
   "checking the files", verify "judging the work"; any other key as it is.
2. **U2: one figure for what was spent.** `tokens    23,149 in 9 calls`, and `of 80,000` where a ceiling is set. The
   split by stage stays in the run's recording.
3. **U3: `verify` says its outcome.** Each verdict names its requirement, and a verdict not met keeps the model's
   reason: `unmet     REQ-AUTH-005  Backup codes: no handler reads them`. Then one line, `verified  no: 1 of 2 met,
   tests passed`. What was written is one path a line. `remaining.md` names each requirement beside its ID.
4. **U4: the repositories said before the reading.** `propose` says `with` and `left out` before it reads, and its
   plan step does not say them again.
5. **U5: help that says what a command does.** Each command's help opens with what it does and whether it calls a
   model; `--id` says it revises an open change; the top help ends with the one-change flow.
6. **U6: the question round said plainly.** `1 point is open. Type an answer and press Enter; = takes the
   suggestion; an empty line leaves it open in brief.md.`, and an `answer> ` prompt where a person types. An
   interrupted command says that nothing more was written.
7. **U7: the README's samples as the commands print them.**
8. **U8: `init` says the test command is unset**, where it is: `tests     none named: set [verify] test in
   .spec/config.toml`.

## Non-goals

- Requirement names in `verify.md` and `summary.md`: their lines name each requirement already, by its delta.
- `status` repeating the unset test command: `init` and `verify` say it, and `status` is read often.
- Messages beyond `--help` that use the engine's words ("arm", "deltas"): a later pass.

## Calls made in the design (the builder's)

- **The time on a progress line** is since the command began, as `m:ss`, so a person sees the whole wait.
- **The prompt `answer> `** is printed only where standard input is a terminal: a pipe, a script and a test read the
  lines they read before.
- **The interrupted line** says `interrupted: nothing more was written`, true of every command, as each writes its
  files at once at its end; the pointer to `status` stays.
