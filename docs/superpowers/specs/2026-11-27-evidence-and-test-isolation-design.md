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

1. **H1-SEC: evidence reads only what a reading could.** A quote is looked for only in a file git lists for that
   repository, with its own exclusions (another repository's from its own `.spec/config.toml`), through no link on
   the way, and only in the file's scrubbed text: never a raw secret, nor `.git/`, an ignored file or an excluded one.
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

- **The listed files** come from `git.files`, kept per command with the file cache, as `quote_holds` is asked once a
  proof: one `ls-files` a repository a command.
- **A config that does not read** makes another repository's quotes unknown, not read without its exclusions.
- **The names dropped** are the keys google-genai reads for the Gemini arm, `GOOGLE_API_KEY` and `GEMINI_API_KEY`; the
  Copilot arm keeps its key in a file (see the non-goals).
