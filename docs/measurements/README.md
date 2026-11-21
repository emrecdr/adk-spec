# Measurements

Each file here is one run of `uv run python -m scripts.measure`, on one model, at one commit of this package.

The labelled set is `scripts/cases.py`: six small changes, each well formed, five with one fault planted and one
with none.

| Case | What is planted | Found by |
|---|---|---|
| `contradiction` | The brief leaves session length alone; the delta adds a requirement that ends idle sessions. | the model, in `check` |
| `ambiguity` | A requirement that says "quickly", with a scenario that says "fast". | the model, in `check` |
| `no-task` | Two requirements added, tasks for one. | code, in `check`, with no model asked |
| `constitution` | The repository's rules ask for a test with every change; the tasks hold none. | the model, in `check` |
| `clean` | Nothing. A blocking finding here is a false one. | |
| `half-done` | Two requirements approved, one implemented. | the model, in `verify`, held to the diff by code |

A measurement calls a model with the account the environment names: about `5 x runs` calls for the whole set. The
script says the number before the first call. It holds for the model it ran on and for the instructions at that
commit; a change to a stage's instruction is a reason to measure again.
