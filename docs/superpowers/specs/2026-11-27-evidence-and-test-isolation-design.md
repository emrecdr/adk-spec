# Evidence and test isolation: phase 25

Designed on 27 November 2026 from an outside audit of `171f1c4` (Antigravity's, read as data and checked item by item
in the code; its findings H1-SEC to H5-REL and U2 here). The owner said "proceed as recommended". The first was
reproduced: a probe found `.git/config`'s `AUTHORIZATION: basic` prefix and `.env`'s value through `quote_holds`.

## Intent

The evidence check answers, for any path under a repository, whether a string is in it: so a pull request can add
evidence lines guessing a token in an untracked file, `.git/config` on a CI runner or a `.env`, and read which held
from `validate`'s notes. And a test run an assistant's tool call starts holds the provider's key in its environment;
a provider's error text reaches a recording unscrubbed; a package folder that is a link is read through.

## Goals

1. **H1-SEC: evidence reads only what a reading could.** A quote is looked for only in a file git tracks for that
   repository, with its own exclusions (another repository's from its own `.spec/config.toml`), through no link on
   the way, and only in the file's scrubbed text: never a raw secret, nor `.git/`, an untracked file or an excluded
   one. A path git does not track is looked for as one gone, so that whether a file is there never shows.
2. **H2-SEC: a tool call's test run holds no provider key.** Under `SPEC_TOOL_CALL`, the variables adk-spec reads for
   a provider's credentials are dropped from the test run's environment.
3. **H3-SEC: a provider's error text is scrubbed** before a recording keeps it or a run says it.
4. **H4-SEC: no package folder read through a link**; and past the cap, a package is counted, not read.
5. **The SIGHUP test passes under a runner that ignores SIGHUP**, as an agent's or `nohup` does.
6. **U2: two texts that drifted.** `init --refresh`'s help says it upgrades an unedited skill; the MCP instructions name
   the four commands that call a model.

## Non-goals

- The Copilot token is a file in the person's home: code the person's account runs can read it, with or without the
  variable naming its folder. Goal 2 covers keys held in the environment.
- A terminal's `verify`: its tests run with the person's own environment, as their own `pytest` does.
- The outside audit's signal race (H5-REL, first half): not real, the handler and every change to `RUNNING` run on one
  thread; its `[skill] paths` config (C3): the README's copy says it.

## Calls made in the design (the builder's)

- **The listed files** come from `git.tracked` (`ls-files --cached`), kept per command with the file cache, as
  `quote_holds` is asked once a proof: one `ls-files` a repository a command, a refusal kept too.
- **A config that does not read** makes another repository's quotes unknown, not read without its exclusions.
- **The names dropped** are the keys google-genai reads for the Gemini arm, `GOOGLE_API_KEY` and `GEMINI_API_KEY`; the
  Copilot arm keeps its key in a file (see the non-goals).


## After the code review

Its review at the highest level found four points to fix before the merge, two older ones and seven small ones,
each checked in the code:

- **Tracked files alone.** The first build listed what `git ls-files --others --exclude-standard` lists too. A pull
  request writes its own `.gitignore`: one that leaves a runner's `.env` out of it had the file read, so the oracle
  stayed open; and a path there but not listed read unknown where a gone one read gone, so whether any file was on
  the runner showed. Now only tracked files are read, which a pull request's author can read already, and an
  untracked path is looked for as gone. The cost: a quote in a new file not yet added to git reads gone until it is
  added, and the note now says "left in the files git tracks". A key's file or one past the cap, unknown, then tells
  nothing new either.
- **A value on the line after its name** (older): the scrub hid it in a file, but in a diff the next line opens with
  `+`, which broke the match, so the value went to the verify and check models, and a quote of it held in no
  scrubbed file. The space after `:` or `=` now crosses lines with a diff's mark (`_GAP` in `secrets.py`).
- **A provider's error answer**, given with its code rather than raised, reached the stage's failure in its own
  words; the guard scrubs it, and a test now gives one.
- **Small ones fixed:** the own config not reading makes quotes unknown, as another's does; a refused listing is
  kept for the command; a package's METADATA, RECORD or `package.json` that is a link is not read; `init --refresh`'s
  help says the skill is written with or without `--no-explore`.
- **Left:** `git grep`'s output read without `-z`, so a quote moved into a file whose name holds a colon or a quoted
  character reads gone (older; `grep` is shared with the code reading's line search); the count of packages past the
  cap may include an excluded one, as reading its name is what the cap saves.
