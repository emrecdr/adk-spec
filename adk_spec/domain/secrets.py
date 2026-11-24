"""Known credential shapes, and the scrub that hides them: applied to everything a model is sent.

Ported as it stands from the reference project, `adk_review/core/secrets.py`: its tables of shapes and `scrub`.
What that project builds on them for its rules (the search for a named secret, the spans of a cut, examples) is not
here, and four constants only those parts read are left out. A shape is changed there first, with its measurements,
and brought over: the comments beside each say what it was measured against.

Shape-based: a private key is found by its header and its block hidden, a vendor's token by its prefix, and a value
by the name it goes by, when it is quoted or when a `.env` or YAML line holds it with a digit, never when code
names, reads or calls it.
"""

from __future__ import annotations

import re

#: The words a secret goes by: what the name of a named value holds, and what a value holds that only names a secret,
#: `"OPENAI_API_KEY"` or `"Show password"`.
SECRET_WORDS = r"api[_-]?key|secret|token|passw(?:or)?d|pwd"
#: (kind, pattern, replacement).
#: The name a secret goes by, prefixed and suffixed as code spells it (`DB_PASSWORD`, `client_secret`, `SECRET_KEY`),
#: never inside a longer word: `tokenizer` names none. Its suffix is possessive: what follows a name in every shape,
#: a quote, a space, `:` or `=`, is no character of the suffix, so giving one back never finds a match. Read by a
#: Windows runner: given back, `token_` repeated over 200,000 characters took 2.3 s there, 141 ms here, where it now
#: takes 25 ms; scrubbed alike over 2.4 million lines of the installed packages and 200,000 random strings.
_NAMED = r"(?:" + SECRET_WORDS + r")(?:[_.-][\w.-]{0,80}+)?+"
#: Not a value but a stand-in for one: a template, a placeholder, or what an earlier shape already hid.
_STAND_IN = r"(?![$%{<]|\[REDACTED)"
#: Every run a shape scans is bounded: a name to 80 characters past its keyword, a scheme to 40, a token's segment to
#: 2,000. Measured with open runs: 9 s over one added line of 40,000 characters, four times as long for each doubling,
#: and no deadline stops a rule. A key block's body holds key-like lines only — a diff's marker, then base64, an armour
#: header, or nothing — so a header where no rule reads, a file's name or an unchanged line, cannot reach a footer
#: further on: measured with any text allowed between them, the change in between was hidden from every model call.
#: What may open a key's line: a diff's marker, then a quote's `>` as Markdown nests them, as a pasted issue or review
#: holds a key. Found by an outside audit: a quoted key had its header hidden and its body sent.
_LEAD = r"[+\- ]?(?:[ \t]*+>)*+[ \t]*+"
#: A comment's marks, as a fixture or a config keeps a key commented out: found by review, such a key had its header
#: hidden and its body sent. SQL's `--` is no mark before a third `-`, which opens a header's own five.
_MARKS = r"#|//|/\*|\*|;|--(?!-)|%"
#: A line opened with a comment's mark, after any quote's. A comment is mostly code's, not a key's: found by review, a
#: mark taken as a quote's is, `#endif`, `// TODO` or a bare `#` after a header only named were hidden from the model.
#: So such a line is a key's only where it holds base64 of sixteen characters or more or an armour field, or is the bare
#: mark before a line that does, as a commented PGP key's blank line.
_MARKED = _LEAD + r"(?:" + _MARKS + r")(?:[ \t]*+(?:>|" + _MARKS + r"))*+[ \t]*+"
#: Any opening at all, for a line that must open with a key's header to begin one.
_ANY_LEAD = r"[+\- ]?(?:[ \t]*+(?:>|" + _MARKS + r"))*+[ \t]*+"
#: An armour header a key's block may hold: PEM's, and PGP's, GnuPG writing `Version:` before the body. Found by an
#: outside audit: with no footer, `Version:` ended the key's lines, and the body after it reached the model.
_ARMOUR = r"(?:Proc-Type|DEK-Info|Version|Comment|Hash|Charset): [^\n]*+"
#: PEM's alone, where a key's block has no footer and its header is not PGP's: found by review, PGP's taken after
#: every header hid a line of code opening `Comment:` after a header only named in a string.
_PEM_ARMOUR = r"(?:Proc-Type|DEK-Info): [^\n]*+"
#: The fields a PuTTY key file writes before and among its base64.
_PUTTY_FIELD = (
    r"(?:Encryption|Comment|Public-Lines|Private-Lines|Key-Derivation|Argon2-Memory|Argon2-Passes|Argon2-Parallelism"
    r"|Argon2-Salt): [^\n]*+"
)
#: Base64 as a key's line holds it: any run of it where an end line follows, and sixteen characters or more where none
#: does, so that a short line of code after a header named in passing is not taken for the key's.
_ANY_BASE64, _LONG_BASE64 = r"[A-Za-z0-9+/=]++", r"[A-Za-z0-9+/]{16,}={0,2}"


def _key_line(base64: str, fields: str) -> str:
    """A line of a key's block: opened as a quote is, then base64 as `base64` takes it, one of its `fields`, or nothing;
    or opened with a comment's mark, then long base64 or a field, or nothing before a line of long base64. Every key
    shape builds its lines here, so that none takes a field or an opening another does not: found by an outside audit,
    a PGP key's `Version:` line ended one shape's lines and not its twin's."""
    after = r"(?=\r?\n" + _MARKED + _LONG_BASE64 + r")"
    quoted = _LEAD + r"(?:" + base64 + r"|" + fields + r")?"
    marked = _MARKED + r"(?:" + _LONG_BASE64 + r"|" + fields + r"|" + after + r")"
    return r"(?:" + quoted + r"|" + marked + r")[ \t]*+\r?"


_KEY_HEADER = r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY(?: BLOCK)?-----"
_KEY_FOOTER = r"-----END (?:[A-Z0-9]+ )*PRIVATE KEY(?: BLOCK)?-----"
#: The header as the key rule reads it: `pgp` set where it opens PGP's block, whose lines may hold PGP's armour.
_KEY_OPENS = r"-----BEGIN (?:(?P<pgp>PGP )|[A-Z0-9]+ )*PRIVATE KEY(?: BLOCK)?-----"
#: A line of a key's body where no footer follows: base64 of sixteen characters or more, an armour header, or a blank
#: line. Found by review: a header only named in code, and every short line after it taken for a key line, hid the
#: code from the model. With a footer, the block between is the key's whatever its lines.
_KEY_BODY = _key_line(_LONG_BASE64, r"(?(pgp)" + _ARMOUR + r"|" + _PEM_ARMOUR + r")")
#: Each run read once and kept: measured by review, a line's blanks split every way between the two runs, a header and
#: 8,000 spaces took 0.6 s to scrub, four times as long for each doubling, and every request of a review is scrubbed.
_KEY_LINE = _key_line(_ANY_BASE64, _ARMOUR)
#: A URL's scheme and user, and its password: up to the last `@` before the host, since a password may hold one,
#: `P@ssw0rd`. Measured before, the password ended at its first `@`: the rule read `P` as a placeholder, and redaction
#: sent the rest of the password to the model. The user may be none, as Redis takes a password, `redis://:secret@host`:
#: read by review of another tool's report, with one character of a user asked for, that form was hidden before no
#: model call and named by no rule.
_URL_LEAD = r"\b([a-z][a-z0-9+.-]{0,40}://[^\s:/@\"']*:)"
_URL_PASSWORD = r"[^\s/\"']+"
#: AWS Bedrock's API key: a long-term one, base64 after its prefix, or a short-term one, a signed request in base64
#: whose host, `bedrock.amazonaws.com`, opens it, its query hundreds of characters on. Measured: with none required
#: past the host, the shape matched its own source here, which a review of this file would name a blocker.
_BEDROCK = r"\b(?:ABSK[A-Za-z0-9+/]{109,269}={0,2}|bedrock-api-key-YmVkcm9jay5hbWF6b25hd3MuY29t[A-Za-z0-9+/=]{40,})"
#: A PuTTY key file: its header, then its own lines alone — a diff's marker, then a field PuTTY writes or base64 —
#: to its MAC, so a header where no rule reads cannot reach a MAC further on, as a private key's block cannot.
_PUTTY_LINE = _key_line(_ANY_BASE64, _PUTTY_FIELD)
#: The key's lines are taken whether or not its MAC line follows: a key pasted in part is a key all the same.
#: A PuTTY key's line where no MAC line follows: one of its headers, base64 of sixteen characters or more, or nothing.
_PUTTY_BODY = _key_line(_LONG_BASE64, _PUTTY_FIELD)
_PUTTY = (
    r"\bPuTTY-User-Key-File-[23]: [^\n]*(?:(?:\n(?>"
    + _PUTTY_LINE
    + r"(?=\n|\Z)))*+\n"
    + _ANY_LEAD
    + r"Private-MAC: [0-9a-fA-F]+|(?:\n(?>"
    + _PUTTY_BODY
    + r"(?=\n|\Z)))*)"
)
#: The shapes a vendor's credential takes, or a URL's or a key file's: what the secrets rule finds.
_VENDOR = (
    ("aws_access_key_id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), "[REDACTED:aws_access_key_id]"),
    (
        "aws_secret_access_key",
        re.compile(r"(?i)(aws_secret_access_key[\"']?\s*[:=]\s*[\"']?)[A-Za-z0-9/+=]{40}"),
        r"\1[REDACTED:aws_secret_access_key]",
    ),
    (
        "github_token",
        re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{80,})\b"),
        "[REDACTED:github_token]",
    ),
    # GitLab's every token, Slack's app-level and refresh tokens and its workflows' webhooks, each by its prefix.
    (
        "gitlab_token",
        re.compile(
            r"\b(?:gl(?:pat|dt|rt|cbt|ptt|ft|imt|soat|ffct)-[A-Za-z0-9_-]{20,}|glagent-[A-Za-z0-9_-]{50,}"
            r"|gloas-[A-Za-z0-9_-]{64,}|GR1348941[A-Za-z0-9_-]{20,})"
        ),
        "[REDACTED:gitlab_token]",
    ),
    (
        "slack_token",
        re.compile(
            r"\b(?:xox[abposr]-[A-Za-z0-9-]{10,}|xoxe(?:\.xox[bp])?-\d-[A-Za-z0-9]{140,}"
            r"|xapp-\d-[A-Za-z0-9]+-\d+-[A-Za-z0-9]{20,})"
        ),
        "[REDACTED:slack_token]",
    ),
    (
        "slack_webhook",
        re.compile(r"https://hooks\.slack\.com/(?:services|workflows|triggers)/[A-Za-z0-9_/]+"),
        "[REDACTED:slack_webhook]",
    ),
    ("stripe_key", re.compile(r"\b[rs]k_live_[A-Za-z0-9]{16,}"), "[REDACTED:stripe_key]"),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}"), "[REDACTED:google_api_key]"),
    # Measured by review: a key of each vendor below, held by a name that says no secret, was found by no rule and
    # reached the model unredacted. Each is known by its vendor's own prefix: measured over 7.6 million lines of this
    # repository and its installed packages, the OpenAI, Anthropic and LiteLLM SDKs among them, none matched.
    ("anthropic_api_key", re.compile(r"\bsk-ant-[a-z]{2,10}\d{2}-[A-Za-z0-9_-]{80,}"), "[REDACTED:anthropic_api_key]"),
    (
        "openai_api_key",
        re.compile(r"\bsk-(?:(?:proj|svcacct|admin)-[A-Za-z0-9_-]{40,}|[A-Za-z0-9]{20}T3BlbkFJ[A-Za-z0-9]{20}\b)"),
        "[REDACTED:openai_api_key]",
    ),
    (
        "huggingface_token",
        re.compile(r"\b(?:hf_[A-Za-z0-9]{34}|api_org_[A-Za-z]{34})\b"),
        "[REDACTED:huggingface_token]",
    ),
    ("npm_token", re.compile(r"\bnpm_[A-Za-z0-9]{36}\b"), "[REDACTED:npm_token]"),
    ("pypi_token", re.compile(r"\bpypi-AgE[A-Za-z0-9_-]{50,}"), "[REDACTED:pypi_token]"),
    # Its last segment may end in `-`, after which `\b` finds no edge before a quote.
    (
        "sendgrid_api_key",
        re.compile(r"\bSG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}(?![\w-])"),
        "[REDACTED:sendgrid_api_key]",
    ),
    # As each vendor documents its prefix: Shopify's access tokens and shared secret, 32 hex digits on; Stripe's
    # webhook signing secret, of more than one length; Tailscale's keys, a kind, an id and the secret. Measured over
    # the same 7.6 million lines, none matched.
    ("shopify_token", re.compile(r"\bshp(?:at|ca|pa|ss)_[a-fA-F0-9]{32}\b"), "[REDACTED:shopify_token]"),
    ("stripe_webhook_secret", re.compile(r"\bwhsec_[A-Za-z0-9]{32,}"), "[REDACTED:stripe_webhook_secret]"),
    (
        "tailscale_key",
        re.compile(r"\btskey-(?:auth|api|client|scim|webhook)-[A-Za-z0-9]{6,}-[A-Za-z0-9]{16,}"),
        "[REDACTED:tailscale_key]",
    ),
    # Measured by review: a key of each vendor below, held by a name that says no secret, was found by no rule and
    # reached the model unredacted. Each is the vendor's shape as gitleaks or trufflehog knows it, and over 12.4
    # million lines in 41,992 files of installed packages none matched. One that may end in `-` or `_` ends where no
    # such character follows, since `\b` finds no edge there before a quote.
    ("aws_bedrock_key", re.compile(_BEDROCK), "[REDACTED:aws_bedrock_key]"),
    ("atlassian_api_token", re.compile(r"\bATATT3[A-Za-z0-9_\-=]{186}"), "[REDACTED:atlassian_api_token]"),
    ("xai_api_key", re.compile(r"\bxai-[A-Za-z0-9]{80}\b"), "[REDACTED:xai_api_key]"),
    ("groq_api_key", re.compile(r"\bgsk_[A-Za-z0-9]{52}\b"), "[REDACTED:groq_api_key]"),
    ("perplexity_api_key", re.compile(r"\bpplx-[A-Za-z0-9]{48}\b"), "[REDACTED:perplexity_api_key]"),
    ("docker_hub_token", re.compile(r"\bdckr_(?:pat|oat)_[A-Za-z0-9_-]{27,}"), "[REDACTED:docker_hub_token]"),
    (
        "google_oauth_client_secret",
        re.compile(r"\bGOCSPX-[A-Za-z0-9_-]{28}(?![\w-])"),
        "[REDACTED:google_oauth_client_secret]",
    ),
    ("google_oauth_token", re.compile(r"\bya29\.[A-Za-z0-9_-]{50,}"), "[REDACTED:google_oauth_token]"),
    ("digitalocean_token", re.compile(r"\bdo[por]_v1_[a-f0-9]{64}\b"), "[REDACTED:digitalocean_token]"),
    ("databricks_token", re.compile(r"\bdapi[a-f0-9]{32}(?:-\d)?\b"), "[REDACTED:databricks_token]"),
    ("vault_token", re.compile(r"\bhvs\.[A-Za-z0-9_-]{90,120}(?![\w-])"), "[REDACTED:vault_token]"),
    (
        "terraform_token",
        re.compile(r"\b[a-z0-9]{14}\.atlasv1\.[a-z0-9_=-]{60,70}(?![\w=-])"),
        "[REDACTED:terraform_token]",
    ),
    (
        "grafana_token",
        re.compile(r"\b(?:glc_[A-Za-z0-9+/]{32,400}={0,3}|glsa_[A-Za-z0-9]{32}_[A-Fa-f0-9]{8}\b)"),
        "[REDACTED:grafana_token]",
    ),
    (
        "sentry_token",
        re.compile(r"\b(?:sntryu_[a-f0-9]{64}\b|sntrys_eyJ[A-Za-z0-9+/=_]{40,})"),
        "[REDACTED:sentry_token]",
    ),
    ("postman_api_key", re.compile(r"\bPMAK-[a-f0-9]{24}-[a-f0-9]{34}\b"), "[REDACTED:postman_api_key]"),
    ("linear_api_key", re.compile(r"\blin_api_[A-Za-z0-9]{40}\b"), "[REDACTED:linear_api_key]"),
    ("notion_token", re.compile(r"\bntn_[0-9]{11}[A-Za-z0-9]{35}\b"), "[REDACTED:notion_token]"),
    ("heroku_api_key", re.compile(r"\bHRKU-AA[0-9A-Za-z_-]{58}(?![\w-])"), "[REDACTED:heroku_api_key]"),
    (
        "age_secret_key",
        re.compile(r"\bAGE-SECRET-KEY-1[QPZRY9X8GF2TVDW0S3JN54KHCE6MUA7L]{58}\b"),
        "[REDACTED:age_secret_key]",
    ),
    ("onepassword_token", re.compile(r"\bops_eyJ[A-Za-z0-9+/]{250,}={0,3}"), "[REDACTED:onepassword_token]"),
    ("twilio_api_key", re.compile(r"\bSK[0-9a-fA-F]{32}\b"), "[REDACTED:twilio_api_key]"),
    ("telegram_bot_token", re.compile(r"\b\d{8,10}:AA[0-9A-Za-z_-]{33}(?![\w-])"), "[REDACTED:telegram_bot_token]"),
    (
        "private_key_base64",  # `-----BEGIN`, then `PRIVATE KEY` within forty characters, at any of base64's offsets
        re.compile(
            r"\bLS0tLS1CRUdJTi[A-Za-z0-9+/]{0,40}?(?:UFJJVkFURSBLRV|BSSVZBVEUgS0VZ|QUklWQVRFIEtFW)[A-Za-z0-9+/=]*"
        ),
        "[REDACTED:private_key_base64]",
    ),
    # Its whole block as a private key's is, its header where a line is all there is: a key file's own lines only,
    # each read once.
    ("putty_private_key", re.compile(_PUTTY), "[REDACTED:putty_private_key]"),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,2000}\.eyJ[A-Za-z0-9_-]{8,2000}\.[A-Za-z0-9_-]{8,}"), "[REDACTED:jwt]"),
    (
        "url_credentials",
        re.compile(r"(?i)" + _URL_LEAD + _STAND_IN + _URL_PASSWORD + r"(@)"),
        r"\1[REDACTED]\2",
    ),
    ("azure_account_key", re.compile(r"(?i)(AccountKey=)" + _STAND_IN + r"[A-Za-z0-9+/=]{20,}"), r"\1[REDACTED]"),
    (
        "azure_shared_access_key",
        re.compile(r"(?i)(SharedAccessKey=)" + _STAND_IN + r"[A-Za-z0-9+/=]{20,}"),
        r"\1[REDACTED]",
    ),
    ("azure_sas_signature", re.compile(r"([?&]sig=)" + _STAND_IN + r"[A-Za-z0-9%+/]{40,}={0,2}"), r"\1[REDACTED]"),
    (
        "azure_client_secret",  # three characters, a digit, `Q~`, and the rest: none of them may stand beside it
        re.compile(r"(?<![\w~.-])[A-Za-z0-9_~.]{3}\dQ~[A-Za-z0-9_~.-]{31,34}(?![\w~.-])"),
        "[REDACTED:azure_client_secret]",
    ),
    # Azure DevOps' personal access token, as Microsoft publishes its shape: 84 characters, `AZDO` after the 76th. Read
    # by an audit, and reproduced: such a token in `pat = "…"`, a URL or Azure CLI's own `AZURE_DEVOPS_EXT_PAT` passed.
    ("azure_devops_pat", re.compile(r"\b[A-Za-z0-9]{76}AZDO[A-Za-z0-9]{4}\b"), "[REDACTED:azure_devops_pat]"),
    (
        "discord_webhook",
        re.compile(r"https://(?:ptb\.|canary\.)?discord(?:app)?\.com/api/webhooks/\d{17,20}/[A-Za-z0-9_-]{60,}"),
        "[REDACTED:discord_webhook]",
    ),
    (
        # The whole block: its header, every key line after it, and its footer where one follows. A key pasted with no
        # footer is a key all the same: found by an outside audit, its body went to the model where the footer was
        # missing. Each key line is matched once, atomic, and no run reads past another header: measured by review, a
        # header with 25 key lines and no footer took over 45 s to scrub, each line matched two ways or three, and
        # 8,000 headers on one line 5.7 s.
        "private_key",
        re.compile(
            _KEY_OPENS
            + r"(?:(?:(?!-----BEGIN )[^\n])*?"
            + _KEY_FOOTER
            + r"|(?:(?!-----BEGIN )[^\n])*(?:\n(?>"
            + _KEY_LINE
            + r"(?=\n|\Z)))*+\n[^\n]*?"
            + _KEY_FOOTER
            + r"|(?:(?!-----BEGIN )[^\n])*(?:\n(?>"
            + _KEY_BODY
            + r"(?=\n|\Z)))*)"
        ),
        "[REDACTED:private_key]",
    ),
)
#: A value in quotes: no quote of either kind, or no white space and no quote of its own kind, so `"P@ss'w0rd99!"` is
#: one. Measured over 3.31 million lines of the installed packages and eight projects: a value that could also hold
#: white space reached across the strings of a line of code 17 times, `'TOKEN = "ghp_' + ...`; with none, two lines
#: more matched, each a real value of a test. A password of words holding the other quote is still missed.
_QUOTED_VALUE = r"([^\"'\n]{6,}|(?:(?!\2)\S){6,})"
#: A type annotation between a name and its value, `token: str = ...`, `KEY: Final[str] = ...` or a parameter's
#: default: read by a replay audit, and reproduced, it hid a credential from both rules and from the redaction.
#: Measured over 2.4 million lines of the installed packages and this repository: every line the shape matched
#: before it matches still, and 66 more, each a constant naming a variable, a URL or a header, none a finding.
_ANNOTATION = r"(?:\s*:\s*[\w.\[\], |]{1,80}?)?"
#: A character of a query parameter's value: none that ends one, nor a bracket. Read by review: the digit's search,
#: unbounded and over a `?` too, read to the end of each run from each name, 1.76 s over 40,000 characters, and past
#: a bracket the value stops at, so redaction hid what `named-secrets` let go.
_QUERY_VALUE = r"[^\s&#?;\"'<>()\[\]{}]"
#: A named parameter of a URL's query, or of its fragment, `#access_token=`, after a `?`, an `&`, a `;` or HTML's
#: `&amp;`: read by the second review, an escaped separator and an OAuth fragment opened none.
_QUERY_SECRET = re.compile(
    r"(?i)(?<=[?&;#])([\w.-]{0,40}?"
    + _NAMED
    + r"=)(?="
    + _QUERY_VALUE
    + r"{0,255}?\d)"
    + _STAND_IN
    + r"("
    + _QUERY_VALUE
    + r"{8,})"
)
#: A character of an authorization header's token: none that ends a string, a word or a call around it.
_HEADER_VALUE = r"[^\s\"'`<>(){}\[\],;\\]"
#: An `Authorization` header's token after its scheme, as code, a config or a command writes the header:
#: `"Authorization": "Bearer ..."`, `Authorization: Basic ...`, `.header("Proxy-Authorization", "Token ...")`. Read by
#: an audit, and reproduced: the header's name holds no word a secret goes by, so the token was named by no rule and
#: reached the model and the report. Between the name and the scheme stand the marks a language puts there, eight at
#: most, PHP's and Ruby's `=>` and a template's backtick among them, which the branch's review found missing. The
#: token holds a digit, or base64's `=`, within 255 characters, as a query's value holds a digit: a word
#: after the scheme, `Basic authentication`, is none, and a `Basic` pair whose base64 holds neither is missed.
#: Measured over 2.99 million lines of the installed packages: 10 lines, each a documentation's.
_HEADER = re.compile(
    r"(?i)((?<![a-z0-9])authorization[\"'`\]:=>,( \t]{1,8}+(?:bearer|basic|token)[ \t]++)(?="
    + _HEADER_VALUE
    + r"{0,255}?[\d=])"
    + _STAND_IN
    + r"("
    + _HEADER_VALUE
    + r"{8,})"
)
#: A value a name alone says is secret, with no vendor's shape: what `named-secrets` weighs. Read by validation, a
#: URL's query parameter was neither: `?api_key=`, `access_token=` and `password=` reached the model and the report.
_GENERIC = (
    (
        "generic_secret",  # a named value in quotes: code, JSON, YAML
        re.compile(
            r"(?i)(" + _NAMED + r"[\"']?" + _ANNOTATION + r"\s*[:=]\s*)([\"'])" + _STAND_IN + _QUOTED_VALUE + r"\2"
        ),
        r"\1\2[REDACTED]\2",
    ),
    (
        "generic_secret",  # a named value unquoted, a `.env`, YAML or Dockerfile line, holding a digit
        re.compile(
            r"(?im)^([+ -]?[^\S\n]*(?:(?:export|env|arg)[^\S\n]+)?[\w.-]{0,80}?"
            + _NAMED
            + r"\s*[:=]\s*)(?=[^\s#]*\d)"
            + _STAND_IN
            + r"([^\s\"'#(\[][^\s\"'#()\[\]{}]{7,})\s*$"
        ),
        r"\1[REDACTED]",
    ),
    (
        # An `.npmrc` registry's credential, `//host/path/:_authToken=`, `_auth=` or `_password=`, holding a digit.
        # Not the reference project's: found by an outside audit, a tracked `.npmrc` matched no shape.
        "generic_secret",
        re.compile(
            r"(?im)^([+ -]?[^\S\n]*//[^\s=]{1,200}?:_(?:authToken|auth|password)[^\S\n]*=[^\S\n]*)(?=[^\s#]*\d)"
            + _STAND_IN
            + r"([^\s\"'#]{8,})"
        ),
        r"\1[REDACTED]",
    ),
    ("generic_secret", _QUERY_SECRET, r"\1[REDACTED]"),  # a URL's query parameter, `?api_key=...`, holding a digit
    ("generic_secret", _HEADER, r"\1[REDACTED]"),  # an authorization header's token, holding a digit
)
#: A named value in quotes running to the end of a text cut from a longer one, its closing quote past the cut: read
#: only where the text was cut there. Read by review: a scrub that read as far as a cut and a credential crossing it
#: could run found no closing quote for a token longer than that, and its first 385 characters were printed as a rule's
#: evidence; and read at the end of every text, it took the first line of a value written over lines for a whole one,
#: `PASSWORD_RULES="at least twelve characters,` a blocker of named-secrets, and a guideline's quote of such a line
#: scrubbed where its hunk was not, the finding dropped.
_OPEN_AT_THE_CUT = (
    "generic_secret",
    re.compile(r"(?i)(" + _NAMED + r"[\"']?\s*[:=]\s*)([\"'])" + _STAND_IN + _QUOTED_VALUE + r"\Z"),
    r"\1\2[REDACTED]",
)
#: Every shape, a vendor's first: what redaction scrubs, and what a cut never falls inside.
_PATTERNS = (*_VENDOR, *_GENERIC)
#: The vendors' shapes that open on a word's edge and a prefix of their own, read first as one pattern: a text none of
#: them is in holds none, and the other shapes alone read it. Measured by review: each took a search of every added
#: line and of every diff past its cap, `vendor_shape` over a million lines 2.22 s and `spans` over 35.7 million
#: characters 5.44 s, read first as one 1.04 s and 2.91 s, every answer the same. Only a shape that reads the same
#: inside an alternation joins: no flag, no group referred back to.
_PREFIXED = tuple(
    shape
    for shape in _VENDOR
    if shape[1].pattern.startswith(r"\b")
    and shape[1].flags == re.UNICODE
    and not re.search(r"\\[1-9]|\(\?P[<=]", shape[1].pattern)
)
_ANY_PREFIXED = re.compile("|".join(f"(?:{pattern.pattern})" for _kind, pattern, _ in _PREFIXED))


def scrub(text: str, *, cut: bool = False) -> tuple[str, int]:
    """`text` with every known secret shape replaced, and how many were; `cut` where `text` was cut from a longer one,
    so a quoted value running to its end is one. A prefixed shape none of which is in the text is passed over until a
    shape rewrites it, since a rewrite can make one: `[REDACTED…]` is the word's edge a token glued to the value
    before it opens on. Measured by review: nine prefixed shapes more took scrubbing a request at the block cap from
    36 ms to 54, every request of every review, each on the event loop; passed over, 23."""
    total = 0
    unprefixed = not _ANY_PREFIXED.search(text)
    for shape in (*_PATTERNS, _OPEN_AT_THE_CUT) if cut else _PATTERNS:
        if unprefixed and shape in _PREFIXED:
            continue
        text, count = shape[1].subn(shape[2], text)
        total += count
        unprefixed = unprefixed and not count
    return text, total


def scrub_lines(text: str, *, cut: bool = False) -> tuple[str, int]:
    """`scrub`, with every line of `text` left at its own number: a shape that ran over several lines, a private
    key's block, is replaced by its mark and by as many line ends as it held.

    Not the reference project's: added here for text that a model is shown and that its quotes are then looked for
    in. Such text is scrubbed once, whole, before anything is cut out of it, and both uses read the result: a line
    is then the same line to the model and to the code that holds the model to it, at the number the file has it."""
    total = 0
    unprefixed = not _ANY_PREFIXED.search(text)  # as `scrub` does: measured by an outside audit, 2.5 times as fast
    for shape in (*_PATTERNS, _OPEN_AT_THE_CUT) if cut else _PATTERNS:
        if unprefixed and shape in _PREFIXED:
            continue

        def hidden(found: re.Match[str], replacement: str = shape[2]) -> str:
            mark = found.expand(replacement)
            return mark + "\n" * max(found.group(0).count("\n") - mark.count("\n"), 0)

        text, count = shape[1].subn(hidden, text)
        total += count
        unprefixed = unprefixed and not count
    return text, total


#: A private key's first line where a line begins with it, a diff's sign or a block's indent before it: how a key's
#: own file has it, and how code that only names the line in a string does not. A PEM block's header, or a PuTTY key
#: file's, whose private lines a diff shows without the header as a PEM block's are.
#: Opened as a key's line in a block may be: a diff's marker, a quote's `>`, a comment's mark. Found by review: with
#: fewer openings than the scrub takes, a file quoting or commenting out a key was not withheld, and a hunk from the
#: middle of its key, with no header, was sent.
_KEY_BEGINS_A_LINE = re.compile(r"(?m)^" + _ANY_LEAD + r"(?:" + _KEY_HEADER + r"|PuTTY-User-Key-File-[23]:)")


#: The words every key `holds_a_key` finds holds, which a file too large to read whole is searched for first. Found by
#: the fourth audit: the search had its own list, and a key a new pattern found would have been passed over by it.
KEY_WORDS: tuple[bytes, ...] = (b"PRIVATE KEY", b"PuTTY-User-Key-File-")


def holds_a_key(text: str) -> bool:
    """Whether a line of `text` begins a private key.

    Not the reference project's. A key's block is known to `scrub` by its first and last line together, so a piece
    of one is known for nothing: a hunk of a diff from a key's middle, a key with no last line, a block longer than
    one is read. Text that is shown in pieces is therefore judged by the file it is a piece of: a file that holds a
    key is shown in no piece at all."""
    return _KEY_BEGINS_A_LINE.search(text) is not None


#: A private key's first line, wherever in a line it stands.
_KEY_ANYWHERE = re.compile(_KEY_HEADER + r"|PuTTY-User-Key-File-[23]:")


def mentions_a_key(text: str) -> bool:
    """Whether a private key's first line stands anywhere in `text`.

    Not the reference project's. For text no quote is held to, a test run's output: a test runner writes its own
    words before each line of a failure, pytest an `E` and spaces, and a key's block is then no shape the scrub
    knows, so text that names one is shown in no part."""
    return _KEY_ANYWHERE.search(text) is not None
