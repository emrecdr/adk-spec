# Brownfield, part 3: `init` describes the repository

Design for phase 8 of adk-spec. Written on 22 November 2026.

**What the owner decided, and when.**

- 22 November 2026, in a dialog, both as recommended:
  - **`init` reads the code with a model, and says so first.** It says what it will cost before it starts;
    `--no-explore` skips it, as on `propose` and `plan`. No new subcommand.
  - **Rules already true of the code are drafted into `constitution.md`**, only while it is still the empty
    template, each with its quoted evidence and marked as drafted, for the person to keep, edit or delete.
- Standing: the golden rule of few commands and simple flows; the model points and Python reads; mostly brownfield
  work, often across repositories.

Everything else is the builder's call, listed at the end for the owner to check.

## Intent, and why

Today `init` makes an empty `.spec/` and asks the person to write the constitution. In an existing repository that
is the moment adk-spec knows least: every change then reads the code from nothing, and the constitution is blank or
written from memory.

This phase makes adopting adk-spec one command that describes the repository back to the person, with evidence,
and leaves two files every later change uses: a profile of the repository, and a constitution that starts from what
is already true.

## What the research says

- **Neither parent project does this.** Spec Kit's guide for an existing project says `init` "does not rewrite your
  application or infer specifications for existing behavior", and to write only principles "already true for the
  repository", warning: "Do not invent standards merely to fill the constitution template." OpenSpec's position is
  "You write specs only for what you're about to change."
- **So this phase writes no spec of the existing system**: a profile and drafted rules, each statement resting on a
  quote code found, which is what adk-spec adds over both.
- Source: `research_notes/Spec driven framework on Google ADK/speckit_internals.md`, sections on the constitution
  and on brownfield.

## Goals

1. `init` in an existing repository reads its code with the reading of phases 6 and 7 (scout, survey, review, every
   rule of the reader) and writes `.spec/profile.md`: what is here, how this repository does things, risks, and what
   is still unknown, each statement with a file, a line and a quote.
2. Rules already true of the code are drafted into `constitution.md` while it is still the template, each with its
   quote, under a heading that says they are drafted.
3. Before it reads, `init` says so in one line, with the most it can cost.
4. `init` never fails for want of a model: the tree is made, and the line says why the code was not read and how to
   read it later.
5. Each change's reading starts from the profile: the scout is shown it, so it goes to the right folders with fewer
   rounds; the design and tasks stages are shown it beside `context.md`.
6. `init --refresh` reads the code again in a workspace that has one, and rewrites the profile.

## Non-goals

- A spec of existing behaviour, or living specs drafted from code.
- Describing the other repositories a change names: the profile is of the workspace's own repository. A change
  reads its other repositories when it names them, as in phase 7.
- A capability-to-folder map with its own accept step. The profile's statements name the folders each part lives
  in, and the person edits the profile like any file.

## Anti-goals: it has failed if any of these can happen

- `init` fails, or leaves no `.spec/`, because no model is set up or a call fails.
- A statement in the profile or a drafted rule rests on nothing in the code.
- `constitution.md` is changed once the person has written in it.
- The reading reads a file the reader of phases 6 and 7 would not.
- A change's reading costs more than it does today because of the profile.

## How it works

```
adk-spec init
   made      .spec
   reading   the code, to describe this repository: up to 7 model calls. --no-explore skips it
   explored  14 files: 18 statements kept, 2 left out, 1 unknown
   wrote     .spec/profile.md
   drafted   4 rules into .spec/constitution.md: keep, edit or delete each
   next      run `adk-spec propose "<what you want>"`
```

### The reading

The explore app of phase 7, unchanged, seeded with a fixed brief instead of a change's: what a person changing
this repository first needs to know, namely its stack and versions, its layout and where each part lives, how it is
built and tested, how errors and configuration are handled, and what is risky to change. The reading's kinds stay
as they are; `touches` is read as "where things live".

### `profile.md`

Written by code from what was kept, as `context.md` is, under `# This repository`, with the same sections and the
commit it was read at. It is the person's to edit. `init --refresh` rewrites it.

### Drafted rules

Code turns each kept `convention` statement into one drafted rule: the note as the rule, the quote and its place as
its evidence. They go at the end of `constitution.md`, under `## Drafted from the code`, with one line saying they
are drafted by `init` and are the person's to keep, edit or delete. Only while `constitution.md` is still exactly
the template; never on `--refresh`.

### Where the profile is used

- The scout of every change's reading is shown the profile, capped, in a section of its own.
- The design and tasks stages are shown it beside `context.md`, capped. Their guides gain no rule: the profile is
  material, as the constitution and `context.md` are.
- `check` and `verify` do not read it.

### When the code is not read

- Not in a git repository, or no file beside `.spec/`: nothing to read, nothing said beyond `made`.
- `--no-explore`: said in the `next` line as how to read it later.
- No model ready (no token, no key): one line with the reason, and `init --refresh` once it is set up.
- A reading that keeps nothing: one line, and no profile written. One that ends early having kept statements
  writes them, marked partial, as a change's `context.md` is.

## Constraints

- No subcommand. One flag, `--refresh`, on `init`, beside `--no-explore`.
- The layers keep their one-way imports; the reading is phase 7's, called the way `plan` calls it.
- No live model call in the build. The plan's last task holds the live steps, each on the owner's go-ahead.

## Cost, said plainly

One reading: up to seven model calls, measured live at some 30,000 tokens on a repository of 268 files. Once, at
`init`, and again only on `--refresh`. A change's reading is shown the profile, a few thousand characters more, and
should need fewer rounds for it.

## Decided by the builder, for the owner to check

1. The profile is `.spec/profile.md`, beside the constitution, and is no part of an approval.
2. Drafted rules come from `convention` statements only, by code, with no model call of their own.
3. No capability-to-folder map with an accept step; the profile names where things live.
4. `init --refresh` rewrites the profile and never touches the constitution.
5. The scout, the design stage and the tasks stage are shown the profile; `check` and `verify` are not.
6. The profile describes the workspace's own repository only.

## How it is proven

- Offline, on the fake model: `init` in a small repository writes the profile and drafts rules; `--no-explore`,
  no model, a failed reading and an edited constitution each leave the tree made and say why; `--refresh` rewrites
  the profile alone; a change's scout is shown the profile.
- A labelled case: a repository with a planted convention (tests beside the code, errors raised as one class), scored
  on whether a drafted rule names it.
- Live, on the owner's go-ahead: `init` on a copy of adk-spec itself, read by hand.
