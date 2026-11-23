# Phase 15: research during planning — design

Owner decisions of 23 November 2026, settled in grilling rounds after the `grilling` skill
(github.com/mattpocock/skills): each question asked with a recommended answer, "yes" accepting it. The owner
answered "proceed as recommended" to each round.

## Why

`propose` drafts a change's brief and requirements before it reads any code, and the reading that follows serves the
plan alone. So the brief asks the person what the repository would answer, requirements cannot build on what exists,
and what a reading could not establish is carried to the plan and asked of nobody. The owner wants planning to rest
on research: the repository's code, and what can be known beyond it.

## What was weighed, and set aside

- **The company's documentation (Confluence Cloud), and Microsoft 365 Copilot's reach into it.** The models adk-spec
  calls are GitHub Copilot's, through LiteLLM; the connectors that give Copilot clients company content are run by
  those clients, never by the model endpoint. Microsoft 365 Copilot is another product, with another sign-in, and an
  app reading through it needs an app registration and an administrator's consent. The owner set both aside for now.
- **Web search.** Every option either works on one arm only (Gemini's own search), or needs a third party's key and
  sends words drawn from company work to it, or brings back shallow text (a registry's README). Not chosen.
- **Installed libraries, read offline.** Chosen: the project's dependencies at the versions it runs, read from its own
  environment. Nothing leaves the machine but what a model is shown, as with code.

## Decisions

1. **The reading comes before the brief** (Q1). `propose` sizes the request, reads the repository aimed by it, and
   only then drafts the brief, with what the reading kept and the repository's profile. Facts are adk-spec's to find;
   decisions are the person's. One reading per change, as before: `plan` reuses its `context.md`.
2. **Questions are asked in order of what they depend on** (Q2). Each open point the brief leaves may name the points
   it depends on. A round asks only the points whose prerequisites are settled; the rest come in later rounds, within
   the three rounds `propose` already has. With no question asked, every point comes back in the output, those that
   can be answered now first.
3. **"yes" takes the suggestion** (Q3), as `=` does. An empty line still leaves a point open, so a key pressed by
   habit never accepts a model's answer. The brief words each question so that "yes" accepts its suggestion.
4. **The reading may look into installed libraries** (Q4): the repository root's Python environment (`.venv` or
   `venv`) and its `node_modules`. A stage is shown each library's name and version, and reads files by path,
   `python:httpx/_client.py` or `node:react/index.js`; libraries are never searched. Quotes are checked as for code,
   secrets scrubbed, a file holding a key withheld. Other ecosystems come later.
5. **The reading's unknowns become questions where the person can answer them** (Q5): the brief is given what the
   reading left unknown, and asks, in its rounds, what the person can decide or knows. What stays unknown is listed
   for the design and the tasks, as now; one the brief settled from an answer is known to them.
6. **No step to confirm a summary** (Q6): the brief is the summary, and the strict tier already stops after the brief
   and the specs for a person to read.
7. **The editor's tools are unchanged** (Q7): they ask nothing; the open points come back in their output for the
   assistant to put to the person, who revises with `propose` and the change's id.

## How it fits

- **`workspace/source.py`**: `Source.of(..., installed=True)` adds the installed libraries as read-only sources beside
  the repositories, each under its scheme (`python:`, `node:`). Their files are found from the environment's own
  records (a Python distribution's `RECORD`, a package's folder), filtered to text a stage can use, and read by the
  same rules as a repository's: joined to their root only once found in the list, never through a link, scrubbed
  whole, a key withheld. They are listed by name and version under the tree; they are not searched, not diffed, and
  have no tests or commits. No network module: the layering test holds.
- **`orchestration/stages/{scout,survey,review}.py`**: their guides say how a library is named and when to read one.
  Openings are unchanged.
- **`orchestration/graph.py`**: `build_triage_app` sizes a request alone. `OpenPointDraft` gains `depends_on`; the
  questions a round puts are the open points whose prerequisites are settled.
- **`orchestration/stages/brief.py`, `deltas.py`**: given the profile and what the reading kept. The brief's guide
  says not to ask what those settle, to ask what the person can decide of what is still unknown, and to word each
  question so "yes" accepts its suggestion.
- **`interfaces/cli.py`**: `propose` sizes, reads, then drafts from the brief on; `context.md` is written once the
  change has its id. A revision keeps its `context.md`, and `--no-explore` reads nothing, as now. `_answered` takes
  "y" and "yes" as `=`.

## Safety and limits

- A library's text is untrusted as a repository's is: a statement counts only where its quote is in the file.
- The round's caps bound what one call is shown, libraries included; a library's listing is capped.
- pnpm's linked `node_modules` is not read (links are never followed); npm and Yarn's hoisted layout is.
- The reading spends what it spent before, only earlier; a request triage sizes as owing no spec spends no reading.

## Live proof

One `propose` on a real repository with a `.venv`, then its `plan`, on Copilot: whether the brief asks fewer facts,
and a library statement is kept. It sends real requests and waits for the owner's go-ahead in so many words.
