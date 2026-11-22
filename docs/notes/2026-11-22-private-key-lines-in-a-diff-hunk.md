# A change next to a private key can show lines of the key to a model

A finding for the `adk_review` project. Written on 22 November 2026 from adk-spec, which uses a copy of
`adk_review`'s table of secret shapes and had the same gap until the same day.

## The finding

The table hides a private key when the text holds the key's first line and its last line together
(`-----BEGIN … PRIVATE KEY-----` to `-----END … PRIVATE KEY-----`). That works for a whole file.

A diff does not show a whole file. It shows pieces, each with three unchanged lines around a change. A piece that
holds only one of the two lines, or neither, matches no shape, and the key lines in it are sent as they are.

The key does not have to be edited for this to happen. **A change within three lines of a key is enough**: the
unchanged lines git adds around the change are lines of the key.

## What was measured

Measured with adk-spec's copy of the table, on text shaped as a diff shows it. The key lines were made up.

| What the diff shows | Key lines readable after the scrub |
|---|---|
| 1. A whole key file added | 0 |
| 2. A whole key file deleted | 0 |
| 3. A key replaced in place, its first and last line unchanged | 0 |
| 4. One line changed in the middle of a key | 8 of 8 shown |
| 5. A line added just above a key | 2 of 2 shown |
| 6. A line changed just below a key | 2 of 2 shown |

Cases 5 and 6 are the likely ones: a comment added above a key, or a neighbouring field changed in a YAML or JSON
file that holds a key as a block. Two or three lines are a small share of a long RSA key. They are a large share of
a short one: an Ed25519 key in OpenSSH form has about five lines of body.

In adk-spec this was also seen end to end before the fix: a test changed one line in the middle of a tracked key
file, ran `verify`, and found lines of the key in the request made to the (fake) model.

## What was not measured

`adk_review` was not run, and nothing in it was changed. I read its source at commit `e2625aa`:

- `adk_review/core/secrets.py:225`, the `private_key` shape, and `:342`, `scrub`.
- `adk_review/collect/diff.py:203`, `capped`, which caps a diff through `cut_at`.
- `adk_review/judge/plugins.py:146-157`, where every request is scrubbed before it is sent.
- `adk_review/core/verdict.py`, `as_seen`, where a quote is held to the scrubbed text.

A search for `.pem`, `id_rsa` and `PRIVATE KEY` outside `core/secrets.py` found one example string in a rule
(`judge/rules/secrets.py:48`) and no place that leaves a file out for holding a key. So the gap is likely there,
and **not confirmed**: another step I did not read may keep such a file from a model.

`cut_at` does not cover it. It keeps a cap from falling inside a credential, in text that holds the whole
credential. Here git has already cut the file before `adk_review` reads anything.

A rule that reports a tracked key is a separate matter. It says the key is there. It does not keep the key's lines
out of a request.

## How to confirm it in `adk_review`

Not run there by me. The header is written in two halves so that this note holds no key's first line itself.

```python
from adk_review.core.secrets import scrub

body = [f"FAKEKEYBODY{n:02d}" + "A" * 51 for n in range(8)]
foot = "-----END RSA " + "PRIVATE KEY-----"
below = "\n".join([" " + body[6], " " + body[7], " " + foot, "-timeout: 30", "+timeout: 60"])
scrubbed, count = scrub(below)
print(count, [line for line in body if line in scrubbed])  # adk-spec's copy: 0 and both lines
```

Then the real question: does a hunk like `below` reach a guideline's request? A test that reviews a commit changing
the line under a tracked key, and reads the request the fake model was sent, answers it.

## Two ways to close it

**1. By file. This is what adk-spec does now, and what I would do first.**
Before a file's part of a diff is given to anything, decide whether the file holds a private key, and if it does,
leave its whole part out and say so in one line. A file holds a key where a line begins with a key's first line:

- in the part of the diff itself, which covers a key that was deleted or lost its first line, or
- in the file as it stands, which covers every piece that shows no first line (cases 4 and 6 above).

"A line begins with it" is the point of the rule. Code that only names the line in a string, as
`judge/rules/secrets.py:48` does, is still reviewed.

The cost: a model never reviews a file that holds a key, also not its other lines. For a key file that is no loss.
For a configuration file with a key in it, the rest of the file goes unreviewed by a model.

**2. By line.** Read the file on both sides of the diff, find the key blocks with the shape the table already has,
and blank those lines in every hunk. The rest of the file stays reviewable. It needs the file's text on both sides
and a mapping from the file's lines to a hunk's, so it is more code and more to get wrong.

## Where adk-spec has it

- `adk_spec/domain/secrets.py`, `holds_a_key(text)`: the rule, about ten lines.
- `adk_spec/workspace/source.py`, `Source.without_keys(diff)`: a diff less each such file's part, and the names.
- `adk_spec/domain/verify.py`, `parts_of_diff(diff)`: a diff split by file.
- Tests: `test_a_text_holds_a_key_where_a_line_begins_with_a_private_keys_first_line`,
  `test_a_diff_loses_the_part_of_each_file_that_holds_a_private_key`,
  `test_verify_is_sent_no_line_of_a_file_that_holds_a_private_key`.

## Two more lessons from the same day, already handled in `adk_review`

adk-spec ported the table and missed two things that `adk_review` does around it. Both were found by review and
fixed. They are listed so that a later port does not repeat them.

- **Scrub before cutting.** adk-spec cut a range of lines, a search hit and a long file out of a file first and
  scrubbed afterwards, and scrubbed line by line. A key's first line was hidden alone and its body was shown.
  `adk_review` has `cut_at` for this.
- **Hold a quote to the text the model saw.** adk-spec scrubbed every request and then looked for a model's quote
  in the unscrubbed text, so a quote of a scrubbed line was "not there". `adk_review` has `as_seen` for this.
