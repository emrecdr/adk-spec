# A lessons file

Design for phase 12 of adk-spec. Written on 22 November 2026.

**What the owner decided, and when.** 22 November 2026, in a dialog, both as recommended:

- **Code only, small.** `.spec/lessons.md` is the person's to edit, and every drafting stage reads it within a cap.
  adk-spec adds a line itself, in code, for each fault a gate sent back that a retry then fixed. At `approve`, where
  a drafted file was edited by hand, the next line asks the person to write the correction there. No model call.
- **Shared through git**, beside `constitution.md`.

Everything else is the builder's call, listed at the end.

## Intent, and why

A workspace makes the same corrections twice: a gate sends the deltas stage back for the same fault in one change
after another (about once a `propose` in the live runs), and a person fixes the same kind of thing in a draft by hand.
A file that every draft reads lets a correction be made once.

## How it works

```
.spec/lessons.md

# Lessons

What every draft in this workspace follows: ...

## From people

- Name a requirement after what the user does, not after the screen.

## Sent back by a gate

- deltas, `delta.target-missing` (3): REQ-AUTH-099 is not in the living spec of `auth`. ...
```

- `init` writes the file with its two sections; a workspace made before this phase gets it the first time a lesson
  is added. A person writes, edits or deletes any line.
- **What a gate sent back.** Each drafting gate (brief, deltas, design, tasks) notes the problems it sends back; when
  the next try passes, they are lessons. After the run, adk-spec adds each under "Sent back by a gate", by its stage
  and its code, with the first sentence it was sent back with, scrubbed and cut to one line; one seen before is
  counted once more instead. A problem with no code (an answer off its schema, a marker repeated) is the engine's,
  and no lesson; a stage given up teaches nothing.
- **Every gate sentence has a code**, as the validator's findings already do, so that a lesson is the same lesson in
  the next change.
- **What a person corrected.** A change records the fingerprint of each file adk-spec drafted. `approve` compares
  them with the files it approves and, where one differs, says so in one line:

  ```
  lessons   brief.md edited since it was drafted: what you corrected, in one line in .spec/lessons.md, later drafts follow
  ```

  Once said, the approved fingerprints stand in for the drafted ones, so the same edit is not named again.
- **Read by every drafting stage**, the brief, the deltas, the design and the tasks, as one more section, within
  6,000 characters, with one sentence: follow each lesson; the request, the answers and the rules come first.

## Anti-goals

- A model is called to write or read a lesson.
- A lesson is written for a stage that was given up, or for an engine fault.
- The same fault fills the file one line a change.
- A person's line is changed or removed by adk-spec.
- A secret in a gate sentence reaches the file.

## Decided by the builder, for the owner to check

1. The four drafting stages read the whole file; triage, `check` and `verify` do not.
2. A lesson keeps the first sentence it was sent back with, cut to 200 characters, as its example.
3. 6,000 characters of the file are read; past that, the start of the file, the person's lines first.
4. The nudge at `approve` covers the brief, the deltas, the design and the tasks; ticking a box is no edit.

## How it is proven

Offline: a stage sent back once and passing adds its line; a second time counts it; a stage given up adds none; an
engine fault adds none; a person's line survives; the stages' instructions carry the file; `init` writes it; `approve`
names an edited drafted file once, and nothing for an untouched one.
