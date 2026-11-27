# Small refactors: phase 27

Designed on 27 November 2026 from the audit of 25 November (`docs/reports/2026-11-25-codebase-audit.md`: A4, A5, A6
and A8), each checked again in the code; built with phase 26 and reviewed once with it, as the owner asked. No
behaviour changes, except that a list cut short now always says `, and N more`, with its comma.

## Goals

1. **A4: one way to count.** `counted(count, noun)` and `first_of(names, shown)` in `domain/text.py`, used by the
   17 lines that wrote a plural by hand and the three that cut a list short. A count takes its thousands' commas
   everywhere; `lifecycle`'s list of unmet requirements gains the comma the others had.
2. **A5: names that need no alias.** `layout`'s file names end in `_FILE` (`BRIEF_FILE`, `TASKS_FILE`, `STATE_FILE`,
   `DESIGN_FILE`, `CONTEXT_FILE`), so no module imports them under another name; the stage key holding the
   constitution's text is `RULES_TEXT`, beside `BRIEF_TEXT` and the others, no longer `CONSTITUTION` read as `RULES`.
3. **A6: one set of exit codes.** The MCP server says what each ending means by `cli`'s own `EXIT_*` names.
4. **A8: quicker tests.** The two tests that waited out `DRAIN_S` (5 s) lower it: the wait is bounded all the same.

## Left as it was

- `source.py`'s list of libraries, cut where it is built, and counted from the whole: `first_of` would need both.
- `context_md`'s count whose noun is said only where nothing came before it.
- The MCP test's two-second limit: a child must start and print within it, and a slow Windows runner needs the room.
