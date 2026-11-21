# How often the labelled set's faults are caught

Measured 2026-11-21T20:38:05+00:00 on gpt-4.1 on copilot, 3 runs a case, at commit 5735877517e3.

| Case | Command | Caught | Blocking on nothing planted | Left out, no such quote | Tokens a run | Seconds a run | Failed |
|---|---|---|---|---|---|---|---|
| `contradiction` | check | 2/3 | 1 | 0 | 1,394 | 19.0 | 0 |
| `ambiguity` | check | 3/3 | 0 | 0 | 1,219 | 15.8 | 0 |
| `no-task` | check | 3/3 | 0 | 0 | 0 | 0.0 | 0 |
| `constitution` | check | 3/3 | 2 | 0 | 1,164 | 9.0 | 0 |
| `clean` | check | nothing planted | 0 | 0 | 1,164 | 3.4 | 0 |
| `half-done` | verify | 3/3, 3/3 | 0 | 0 | 1,291 | 10.0 | 0 |

Caught: in how many runs a finding on the planted fault's file named it; one figure a planted fault.
Blocking on nothing planted: blocking findings that match no planted fault, over all runs; an upper bound on
the false ones, since a model may find a real fault nobody planted.

## Read by hand, and decided

Run on the owner's go-ahead on 21 November 2026 ("Run it in full"): 15 model calls, about 18,700 tokens, three
minutes. No run failed, and no finding of the model's was left out for quoting text that is not there.

**What it shows.**

- Every planted fault was caught in at least two runs of three, and four of the five in all three.
- The clean case was never blocked.
- The half-done work was judged rightly in all three runs: the implemented requirement `met`, held to a line the
  diff adds, and the other one not.
- The case code decides cost no call and was found every time.

**What it does not show.** Three blocking findings matched nothing planted: one in the contradiction case, two in
the constitution case. What they said is not known. The script threw each run away and kept the number alone, so
nobody can say whether they were false findings or faults nobody planted. The script now keeps each one in its own
words, and each miss with what that run found instead, under headings of their own. The next measurement will
show them; this one cannot.

**Decided, by the three rules of the plan.**

- A planted fault caught in fewer than two runs of three: none. No instruction is changed on this evidence.
- A clean case blocked in any run: none. No severity rule is loosened.
- The largest command: a standard `propose` now spends about 4,700 tokens (`docs/confirmation/2026-11-propose.md`),
  half of what it did. The README's example of `max_tokens = 30000` stands.

**What this is not.** Three runs a case on one model is a first reading. The contradiction case at two of three
is the one to watch. Nothing here was run on the Gemini arm or on Windows.
