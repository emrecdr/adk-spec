# The skill's routes and its refresh: phase 23

Designed on 26 November 2026 from the audit of 25 November (`docs/reports/2026-11-25-codebase-audit.md`, C1-C3, step
5 of its order, with U12). The owner said "proceed as recommended". Each item was checked again in the code, and C2's
premise against the tools' own documentation, which changed it.

## Intent

The Agent Skill is how a coding assistant uses adk-spec with nothing set up. It lists the commands, but not which to
run for what a person asks; it does not name the reports `verify` leaves for the assistant and the pull request; and
it is written once, so an install never gets a better text.

## Goals

1. **C1: what the person asks, and what to run.** Each command's line names the plain requests it answers ("what is
   next?", a feature or a fix, "is it done?"), and the implementing section names "implement <id>". A section of its
   own was built and folded in by the cleanup reviews: it repeated the command list and "what stays the person's",
   loaded each time the skill is.
2. **U12: the report named.** Put `reports/summary.md` in the pull request, in the skill and the MCP server's
   instructions. `reports/remaining.md` is named by the step `status` and `verify` print, which both texts say to do.
3. **C3: a refresh upgrades an unedited skill.** `init --refresh` replaces a skill whose text is one adk-spec
   shipped, and says `replaced`; one a person edited is kept, said in one line. No mark is written into the file: the
   texts adk-spec shipped are known by their hashes, a test holding the list to the text.
4. **C2, changed by validation: one copy, and how to make another.** The README says Antigravity reads skills from
   `.agents/skills/` and how to copy the skill there.

## Non-goals

- **Writing the skill to `.agents/skills/` too**, as the audit proposed. Checked: GitHub Copilot reads
  `.github/skills/`, `.claude/skills/` and `.agents/skills/`, and VS Code lists a skill of the same name found in two
  of them twice, with no rule for which wins; duplicate skills cost context. Copilot is this tool's first arm, so the
  second copy is the person's to make where Antigravity is used. Claude Code reads `.claude/skills/` alone, so that
  stays the one written.

## Calls made in the design (the builder's)

- **"Unedited"** is the text's fingerprint, `sha256_of` (normalised: line ends, trailing blanks, one final newline),
  being one adk-spec shipped: three so far (`18f9839`, `83bd317`, `a22a99c`), and this phase's. An editor that only
  trims trailing blanks leaves it unedited.
