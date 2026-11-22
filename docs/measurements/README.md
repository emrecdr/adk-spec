# Measurements

Each file here is a run of `uv run python -m scripts.measure`, on one model, at one commit of this package, or a
record of live runs of the commands themselves.

The labelled set is `scripts/cases.py`: seven small changes, each well formed. Five have one fault planted, one
has none, and one has nothing wrong and a place in the code to be found.

| Case | What is planted | Found by |
|---|---|---|
| `contradiction` | The brief leaves session length alone; the delta adds a requirement that ends idle sessions. | the model, in `check` |
| `ambiguity` | A requirement that says "quickly", with a scenario that says "fast". | the model, in `check` |
| `no-task` | Two requirements added, tasks for one. | code, in `check`, with no model asked |
| `constitution` | The repository's rules ask for a test with every change; the tasks hold none. | the model, in `check` |
| `clean` | Nothing. A blocking finding here is a false one, or a fault of the set itself: read its wording. | |
| `half-done` | Two requirements approved, one implemented. | the model, in `verify`, held to the diff by code |
| `across` | A web app in the workspace that signs in through an API in a repository beside it, named with the change; the place sign-in starts a session is in the API, and the web app holds an old file of a similar name. | the model, in the reading `plan` makes of both repositories: caught where a statement it kept names the planted file in the API |
| `profile` | A repository with no `.spec/` yet, whose errors are raised as one class and whose tests stand beside the code. | the model, in the reading `init` makes: caught where a rule it drafts into the constitution rests on a planted file |
| `integration` | A repository with one place where sign-in starts a session, and an old file of a similar name that nothing uses. | the model, in the reading `plan` makes of the code: caught where a statement it kept names the planted file |

A measurement calls a model with the account the environment names: about `16 x runs` calls for the whole set. The
script says the number before the first call. It holds for the model it ran on and for the instructions at that
commit; a change to a stage's instruction is a reason to measure again.

Under its table a report lists, each in its own words: every blocking finding that matched nothing planted, every
planted fault a run missed with what that run found instead, and every finding left out because the text it quotes
is not in the file it names. Read them before the table. The second measurement here showed that eight "false"
findings were one real fault of the set.

A count of three runs is not a rate. Between two measurements an hour apart, on one model and one commit, a case
moved from three of three to none of three. Read a count as what happened in those runs; to compare two
instructions, run each case five times or more (`--runs 5`, about 25 calls) and compare the lists as well as the
counts.

| File | Model | What changed before it |
|---|---|---|
| `2026-11-copilot-gpt-4.1.md` | gpt-4.1 on Copilot | The first measurement. |
| `2026-11-copilot-gpt-4.1-second.md` | gpt-4.1 on Copilot | The script keeps the wording of what it cannot place. It found a fault of the set itself. |
| `2026-11-22-live-reading.md` | gpt-4.1 on Copilot | Phases 6 to 13, one section each: the `integration`, `across` and `profile` cases, and live runs of `propose`, `plan`, `init`, `approve` and `verify`, with what each run found and what was fixed. |

Not yet measured: the set as corrected after the second measurement, and the check's instruction with "Report every
fault you find. One finding does not excuse the next." (plan 4, Task 4).

