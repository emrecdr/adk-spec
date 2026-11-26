# Secrets and links: phase 19

Designed on 26 November 2026 from the audit of 25 November (`docs/reports/2026-11-25-codebase-audit.md`, items S1,
S2 and S3, its P0). The owner said "proceed as recommended": this phase, test first, then H1 and S4 as phase 20.
Each finding was checked again in the code and with offline probes before the design.

## Intent

The project's rule is that secrets never reach a model or a recording. Three gaps break it: common credential lines
pass the scrub, a private key held in a string literal is sent in part, and a link under `.spec/` makes a command read
a file from anywhere, or prune `*.json` files from any folder. This phase closes the three, with no model call, no
new command and no new flag.

## Goals

1. **S2: credential lines scrubbed.** The unquoted rule hides a value followed by a ` # comment`, a value on a YAML
   list item (`  - POSTGRES_PASSWORD=...`) and one after Windows' `set`. A command's option, `--password=...` or
   `--token ...`, holding a digit, is hidden wherever it stands in a line.
2. **S1: a key in a string withheld.** `holds_a_key` also finds a key whose header stands inside a line, as code holds
   one in a string, where a key's base64 follows on that line or within the next four. Its file is then shown in no
   piece: neither the reading nor `verify`'s diff sends it.
3. **S3: no link under `.spec/`.** A command refuses a `.spec` tree that is a link or holds one that leads to a file
   or folder, naming it, before it reads or spends anything. `init` refuses a `.spec` that is a dangling link.

## Non-goals

- `.netrc` lines, Docker's `"auth"`, a connection string's password with no digit, and a Dockerfile's legacy
  `ENV NAME value` or several `NAME=value` on one `ENV` line: rarely in a tracked file, or each shape risks hiding
  code. Recorded in the roadmap.
- H1 (processes left running) and S4 (the MCP `verify` tool): phase 20.
- The reference project's `secrets.py`: shapes are changed here, as every audit fix since 22 November was, measured
  over the installed packages; bringing them there is the owner's.

## Calls made in the design (the builder's)

- **One place for the link rule.** `Workspace.find`, which every command opens the workspace with, walks `.spec` and
  raises `PathError` at the first link or junction. Not each of the twenty reads: one missed would reopen the hole.
  `PathError`, not `WorkspaceError`, so `init`'s check for a workspace above does not take a link for none.
- **Every link refused, not only one that leads out.** A link to a file inside the repository can name its `.env`;
  the code reading refuses every link too, and so do the writes (`inside()`). Emacs' lock, `.#name`, a link to
  nothing beside a file with unsaved edits, is passed over (the code review); any other link to nothing is refused,
  as it may stand where a folder is made, which would fail after a run paid (the second review). The walk costs
  172 ms over 2,000 archived changes, measured.
- **Three tests change what they pin.** A linked `lessons.md`, `changelog.md` or change folder no longer lets the
  command run on: it is refused before anything is recorded or spent, which is what those tests guarded (no command
  stopped half done, no paid draft lost). The linked `lessons.md` was read and sent to drafting: the hole itself.
- **The key in a string:** its header, then on that line or within the next four, after any indent, a run of forty
  base64 characters or more holding a digit: a PGP key's armour and an encrypted key's fields stand before it. Code
  that only names the header has none, and is read as before; a path or digest holding a digit there withholds the
  file, the safe side.
- **The option rule:** `--` then a name a secret goes by, `=` or blanks, or a container's `-e`, `--env` or
  `--build-arg` then `NAME=`; then a value, bare or in quotes, of eight characters or more, holding a digit within its
  first 200, and opening with no `-`.

## Tests

- Each credential form hidden; the same line naming no value, or a placeholder, left alone.
- A key in concatenated literals, in a triple-quoted string and in a YAML value withheld; a diff part of one withheld;
  code that only names the header read.
- A linked profile, a linked runs folder and a linked `.spec` each refused, the target unread and untouched; the three
  tests above pinned to the refusal.
- Measured: the scrub before and after over the installed packages and this repository, every newly hidden line
  read.
