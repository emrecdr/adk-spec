# A code graph for the reading

Drafted on 27 November 2026, after the owner asked for "our simplified version of graphify" (never graphify as a
dependency), asked that adk-review use the same graph, and had the two sessions agree an architecture over the
agent messageboard (#699 to #708). Research: `docs/reports/2026-11-27-code-graph-research.md`, its claims about
adk-spec checked in the code.

## Intent

`propose` and `init` read a repository before drafting. Today a scout stage chooses what to read from a folded tree
of paths (up to 300, then folders), then up to four surveys and two reviews read it: seven model calls at most, the
ranges of lines guessed, and the block a quote stands in found by indentation. A graph of the code, built without a
model, aims that reading: which files matter for this request, where a name is defined, who imports it, which tests
reach it. The research's finding: a graph aims the reading, it does not replace it (a graph-only agent used ten times
fewer tokens and answered worse, 83% against 92%); skeletons of signatures choose code as well as whole files at a
seventh of the cost.

## Part 1: the shared library (agreed by the two sessions, for the owner's approval)

- **Pure and small.** Python 3.14, the standard library's `ast` only, no I/O, no network, no dependency. Its own
  repository, pinned by commit as a uv git source in adk-spec and adk-review. Neither tool imports the other.
- **The caller's input.** `build(sources: Mapping[str, str], *, commit: str, tests: Callable[[str], bool]) -> Graph`.
  adk-spec passes the files git lists in the working tree, with its exclusions, links and size cap, and HEAD plus a
  dirty mark as `commit`; adk-review passes git objects at a commit. Each reads files its own way.
- **What it holds.** Files (path, test flag, parsed or why not: the floor, so a query says "at least"); symbols
  (qualname, kind function, class, method or variable, file, first line with decorators, `head` where the signature
  ends, last line); edges defines, imports (the bound name, through re-exports four files deep, `lazy` and
  `type_checking` flags), inherits, tests (`via` imports or name), each with its site line; calls in a later version,
  resolved through imports, the module's own names and `self`, an unresolved call counted, never guessed.
- **What it never holds.** Source text beyond identifiers, paths and line numbers: no signature, docstring or literal
  value. A tool renders lines from its own sources by the graph's ranges: adk-spec from its scrubbed reading.
- **Resolution with no configuration.** Modules found by path suffix, so `src/` layouts and monorepos need no roots;
  a standard-library name is never a local file; an ambiguous name returns every candidate. adk-review offers its
  measured resolution code and tests as the seed.
- **Hygiene.** Warnings silenced while parsing; a syntax error, a `RecursionError` (checked: a 200,000-term
  expression on 3.14.10) or newer syntax lists the file as unparsed with why; walks are iterative; a path that is
  absolute, holds a backslash or `..` is refused.
- **Output.** POSIX paths, sorted, deterministic `to_json`/`from_json` with a schema version. Queries return plain
  data: `definition`, `importers`, `tests_for`, `parents`, `hubs`, `matching(words)`, `ranked(seeds, limit)`.
- **Room for a cache.** The build is split inside into a per-file step and a cross-file step; no cache in v1 (8,582
  files parse in 7.4 s), one later outside the repository, keyed by git blob, schema and Python minor.

## Part 2: adk-spec's use of it (the owner's call on scope)

1. **Ranked files for the scout.** Beside the folded tree, the scout is shown the files ranked by a personalised
   PageRank over imports, definitions and tests, seeded by the request's words matched to names, each with one
   reason ("defines `Source`"). Pure Python ranked 10,000 nodes in 0.23 s.
2. **Read by symbol.** A stage may name a symbol; code looks up its exact lines and reads only those: never a path
   built from a model's text.
3. **Exact `within`.** The block a quote stands in comes from symbol ranges; indentation stays for unparsed files.
4. **Hubs for `init`.** The most-imported modules and symbols feed the profile's "risky to change".
5. **Later:** a skeleton map of signatures under a budget; relations answered by code in a "more" round
   (`importers:X`, `tests:X`); reading before the scout, which saves a call but changes a flow and needs a live
   measurement, so the owner's go-ahead.

No new command: `propose` and `init` use it, and nothing more is printed.

## The owner's decisions, 27 November 2026

1. **Python only in v1.** JS/TS files are listed as unparsed, so a query says "at least"; v2 adds JS/TS import edges
   by regular expression, with no dependency.
2. **adk-spec's first scope is items 1 to 4**, with no change of flow: ranked files for the scout, reading by symbol,
   exact `within`, hubs for `init`; ranking and hubs live in adk-spec, on top of the library's facts (the owner's
   later call), and the graph only checks, as below.
3. **The library's repository is `~/Projects/playground/codegraph`**, local, with no remote. adk-spec's session builds
   v1 test first; adk-review's session reviews it and contributes its measured module-resolution code and tests.

## The graph checks, it never decides (the owner, 27 November 2026)

The owner's words: "at first, currently, use code graph as an validation, double check resource, not use as only
source of truth about codebase". So in adk-spec's first use:

1. **The scout keeps its tree of paths.** The graph's ranked files are given beside it as a hint, never in its place,
   and a file the scout names that the graph does not know is still read.
2. **Reading by symbol** takes the graph's lines to locate a symbol; the text read is always the file's own, and a
   range that no longer fits the file is not used.
3. **Exact `within`** uses the graph's ranges only where they agree with the file; indentation decides otherwise.
4. **Hubs** reach the profile as a hint the model checks against what it read, never as a statement of their own.

Nothing adk-spec writes, gates or says rests on the graph alone.

## Order of the work

1. The library, v1, in its own repository, with its own gate; reviewed by adk-review's session.
2. adk-spec's use of it, on a branch. It merges only once the library has a remote: adk-spec pins it by commit as a
   uv git source, and a local path would break CI, every other machine and the fresh-clone gate. The owner creates
   the remote; no session pushes or creates one without the owner's go-ahead.
