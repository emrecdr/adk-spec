# Adjacent tool categories: workflows and automation a local spec-driven CLI could adopt (as of November 2026)

Pages were fetched on 2026-11-24. None of the fetched pages showed a "last updated" date. Lines marked *(search summary)* come from a search engine's summary of the named official page, because a direct fetch of that page failed (404 or a site move). Treat them as less certain than lines from fetched pages. Vendor documentation is the primary source for a product's behaviour. Vendor marketing figures are marked as marketing.

Local cross-check (read-only, to avoid recommending what already exists): the CLI already fingerprints each delta requirement against its base in the living spec, and flags `delta.base-stale` when the base changes (`adk_spec/domain/validate.py`). It voids an approval when any change file is edited (`adk_spec/domain/lifecycle.py`). Its verify report records the commit it judged against (`adk_spec/domain/report_md.py`). `validate` and `status` take `--json` (`adk_spec/interfaces/cli.py`). The source has no SARIF, GitHub annotation, job summary, JUnit, ReqIF, supersede or "suspect" handling.

## 1. AI code review tools: grounding, team preferences, links to requirements or tickets, posting, repeated findings

### Takeaway
The reviewers converge on five patterns:
- whole-repository context, not just the diff;
- standing rules read from files already in the repository (CLAUDE.md, AGENTS.md, copilot-instructions);
- a memory that learns from people's replies, reactions and dismissals, and suppresses categories people keep ignoring;
- a per-requirement verdict against a linked ticket's acceptance criteria, in three or four levels such as Addressed, Not addressed and Unclear;
- one review comment updated on each push.

None of the fetched docs says it checks a model's quoted evidence against the diff in code. That is where the CLI already goes further than these tools.

### Cited Findings
**GitHub Copilot code review**
- **Context:** "Full project context gathering" analyzes the whole repository through agentic capabilities that run on GitHub Actions runners. Without runners, reviews still run, but without the agentic features. Cross-repository context is in public preview. — [GitHub Docs: Copilot code review](https://docs.github.com/en/copilot/concepts/agents/code-review)
- **Instruction files:** Copilot reads `.github/copilot-instructions.md` (repository-wide), `*.instructions.md` under `.github/instructions/` (matched by path), `AGENTS.md`, and skills. On a pull request it reads them from the head branch, not the base branch. — [GitHub Docs](https://docs.github.com/en/copilot/concepts/agents/code-review)
- **Triggering:** Automatic review is turned on in a user's settings or in a ruleset. A ruleset can force "Review new pushes" and "Review draft pull requests". Otherwise Copilot "will only review a pull request once", and a person re-requests a review from the Reviewers menu. — [GitHub Docs](https://docs.github.com/en/copilot/concepts/agents/code-review)
- **Approvals:** "By default, Copilot's reviews do not count toward required approvals." If Copilot approvals are enabled, its approval can satisfy the rule, and a new push dismisses that approval. — [GitHub Docs](https://docs.github.com/en/copilot/concepts/agents/code-review)
- **Limits:** Copilot "is not guaranteed to spot all problems". It skips dependency-manifest, log and SVG files. Cost is quoted per review, from about $0.05 to $25 depending on effort level. — [GitHub Docs](https://docs.github.com/en/copilot/concepts/agents/code-review)

**CodeRabbit**
- **How learnings are made:** A person replies to `@coderabbitai` on a pull request or issue. The bot decides whether to keep a learning and says so under "Learnings Added". A person can also import a file (`@coderabbitai add a learning using docs/coding-standards.md`). The SaaS can infer learnings itself. — [CodeRabbit: Learnings](https://docs.coderabbit.ai/knowledge-base/learnings)
- **Storage and scope:** Learnings are stored per organization with metadata (pull request number, filename, user). Credentials are redacted at write time. Scope is `local` (repository), `global` (organization) or `auto`. A learning from an open pull request applies only to that pull request until it merges. A learning tied to a filename pattern applies when the pattern matches a changed file. — [CodeRabbit: Learnings](https://docs.coderabbit.ai/knowledge-base/learnings)
- **Governance:** `approval_delay` (0 to 30 days) holds chat-sourced learnings for an admin's approval. They auto-approve after the delay unless an admin disapproves. Admins edit or delete learnings in a dashboard. Learnings export as CSV, or as a documentation pull request. — [CodeRabbit: Learnings](https://docs.coderabbit.ai/knowledge-base/learnings)
- **Rule files:** CodeRabbit "automatically detects and applies" files such as CLAUDE.md, .cursorrules and copilot-instructions, and recommends them over importing them as learnings. "Path instructions precede learnings." — [CodeRabbit: Learnings](https://docs.coderabbit.ai/knowledge-base/learnings)
- **Linking issues:** `fixes #123` or `closes #123` links GitHub and GitLab issues. Jira and Linear keys are read from the title, the description and the branch name. Keys in the title, in the branch name or on a `Closes`/`Fixes`/`Resolves`/`Refs` line are direct targets. Other keys in the description are "background context" and add no requirements. — [CodeRabbit: PR validation](https://docs.coderabbit.ai/issues/pr-validation)
- **Assessing issues:** CodeRabbit compares the issue's title, description and named custom fields with the code changes. "Comments and discussion threads aren't part of the assessment." Each objective is marked ✅ Addressed, ❌ Not addressed (with an explanation) or ❓ Unclear (with an explanation). — [CodeRabbit: PR validation](https://docs.coderabbit.ai/issues/pr-validation); trackers listed at [CodeRabbit: Issue integrations](https://docs.coderabbit.ai/integrations/issue-integrations)

**Qodo and PR-Agent**
- **Ticket sources and linking (open-source PR-Agent):** Tickets come from GitHub and GitLab issues, Jira Cloud (acceptance criteria from a configured `jira_requirements_field`), Linear, Asana and Azure DevOps. A ticket is linked through the pull request description or the branch name. Jira keys are read from branch names, and `extract_issue_from_branch=false` turns that off. — [PR-Agent docs: fetching ticket context](https://raw.githubusercontent.com/qodo-ai/pr-agent/main/docs/docs/core-abilities/fetching_ticket_context.md)
- **Compliance levels:** Each ticket is graded Fully Compliant, Partially Compliant, Not Compliant, or "PR Code Verified". The last means the code "meets ticket requirements, but requires additional manual testing". The grades appear only in the review comment: "These assessments are not added as PR labels." — [PR-Agent docs](https://raw.githubusercontent.com/qodo-ai/pr-agent/main/docs/docs/core-abilities/fetching_ticket_context.md)
- **Commercial Qodo:** "Qodo analyzes the full repository, not just the changed lines." Review Standards are built from the codebase, pull request history and requirements. "Rule Miner" turns recurring patterns from pull request history into enforced rules. With the per-commit trigger, Qodo "updates the same review comment as new commits land". It prioritizes issues like ones the team fixed and "quiets ones you've consistently dismissed". It also reports "requirement gaps" (a pull request missing its linked spec) and drift from a linked Figma design. — [Qodo docs: Code review](https://docs.qodo.ai/code-review) (vendor docs). The old PR-Agent docs URL now 301-redirects here, so the open-source and commercial documentation have split.

**Greptile**
- **Learning signals:** Team members' pull request comments, replies to Greptile, and 👍/👎 reactions. Greptile also "analyzes which comments get addressed by comparing first and last commits". Categories left unaddressed are suggested less often; an example suppresses semicolon nitpicks "after 3 ignores". Security and logic issues are never suppressed. Rules are inferred from team behaviour "without manual configuration". — [Greptile: Memory and learning](https://www.greptile.com/docs/how-greptile-works/memory-and-learning)
- **Marketing:** The same page claims an "80% reduction in ignored comments" and a "3x higher suggestion adoption rate". These are marketing figures and are unverified. — [Greptile: Memory and learning](https://www.greptile.com/docs/how-greptile-works/memory-and-learning)
- **Explicit rules** *(search summary)*: Rules can be set in the dashboard, a `.greptile/` folder or `greptile.json`, scoped to repositories and file paths. Greptile imports CLAUDE.md, `.claude/rules/**`, AGENTS.md, .cursorrules and `.cursor/rules/**` as organization-wide context. The docs say to verify auto-created rules. — [Greptile: Custom context](https://www.greptile.com/docs/code-review-bot/custom-context.md), [Greptile: Best practices](https://www.greptile.com/docs/code-review-bot/best-practices)

**Graphite Agent (formerly Diamond)** *(search summary)*
- **Rules:** Rules are either custom prompts in the UI or file-based rules: a glob such as `docs/coding-style.md`, `CONTRIBUTING.md` or `.github/rules/*.md` points at repository files. Large files are truncated. The docs recommend writing each rule as Rule → Bad example → Good example → Reasoning. The "Rules & exclusions" tab reports how many issues each rule flagged. — [Graphite docs: AI review customization](https://graphite.com/docs/ai-review-customization), [Graphite: Diamond setup](https://graphite.com/docs/diamond-setup)
- **Rename:** A third-party source dates the rename to Graphite Agent to 7 October 2025. — [21st.dev (third party)](https://21st.dev/blog/graphite-vs-design-bug-bot)

**Sourcery** *(search summary)*
- **Feedback:** 👍/👎 on review comments teaches Sourcery. When many similar past comments were marked unhelpful, it suppresses similar new ones, but one downvote does not silence a topic. `@sourcery-ai dismiss` dismisses all outstanding comments. Review rules now live on a dashboard tab, and `.sourcery.yaml` is "Legacy Configuration". — [Sourcery: Review rules](https://docs.sourcery.ai/reviews/review-rules/), [Sourcery: Interacting with Sourcery](https://docs.sourcery.ai/Code-Review/Code-Reviews-on-Pull-Requests/Interacting-with-Sourcery), [Sourcery legacy .sourcery.yaml](https://docs.sourcery.ai/References/Legacy-Configuration/sourcery-yaml)
- **Contested claim:** A third-party article says dismissals teach `.sourcery.yaml`, and cites a benchmark in which about half of Sourcery's comments were not actionable. Neither claim is supported by official docs. — [DEV Community (third party)](https://dev.to/rahulxsingh/sourcery-ai-review-worth-it-for-python-developers-42je)

### Inferences
- **Rule files:** Reading the rule files a repository already has is now table stakes: Copilot, CodeRabbit and Greptile all read CLAUDE.md, AGENTS.md or copilot-instructions. A spec CLI that ignores them repeats work the team has already written down.
- **Suppressing repeats:** The strongest common mechanism is suppressing findings people repeatedly dismiss. It is keyed by category and path (Greptile, Sourcery, Qodo) and gated by a human for anything persistent (CodeRabbit's `approval_delay`, Greptile's "verify inferred rules"). The CLI's `lessons.md` learns from gate send-backs a retry fixed. It does not learn from a person's dismissal of a check or verify finding. That gap is the transferable part.
- **Verdict scale:** The per-requirement scales (CodeRabbit: Addressed / Not addressed / Unclear; Qodo: Fully / Partially / Not / Verified-but-needs-manual-testing) match the CLI's verify step. Qodo's fourth level, "the code is right, but someone must test it by hand", is a useful verdict for requirements a diff cannot prove, such as UI work or behaviour across environments.
- **Who benefits:** Reviewers get less noise from suppression and rule files. Product owners and auditors benefit from ticket compliance verdicts. Authors benefit from an updated single comment rather than a stream of comments.

### Gaps
- The fetched pages do not say which review event Copilot submits (Comment or Request changes), how Copilot dedupes findings across pushes, or what thumbs feedback it takes.
- The fetched CodeRabbit pages do not say how it treats a finding that was resolved and then reappears on a later push.
- Greptile's grounding mechanism (code graph or index) is not described on the fetched page.
- No fetched doc for any reviewer describes verifying a model's quoted evidence against the diff in code. I found no source claiming any of them does it.

## 2. Requirements traceability and docs-as-code requirements tools

### Takeaway
The docs-as-code tools (Doorstop, sphinx-needs, StrictDoc) all keep requirements as text files in git with stable IDs. They link items to parents, code and tests, and validate the links in a CLI or build step. Doorstop's model is the closest to the CLI: each link stores the parent's fingerprint, so a parent edit turns the link "suspect", and each item's `reviewed` stamp is a fingerprint, so an edit marks it unreviewed. The enterprise ALM tools (Jama, Polarion) add admin-configured suspect triggers, baselines and ReqIF exchange, which matter in regulated supply chains but are heavy for a local tool.

### Cited Findings
**Doorstop**
- **Model:** "Each linkable item (requirement, test case, etc.) is stored as a YAML file." "The items in each directory form a document." Documents form a tree through `--parent`. Items are linked with `doorstop link`. Running `doorstop` alone runs integrity checks. `doorstop publish` writes HTML. — [Doorstop docs](https://doorstop.readthedocs.io/en/latest/)
- **Validation:** Warnings include "An item has unreviewed changes" and "There is a cycle of item links". Errors include "Link with a invalid UID", "Unknown item for an UID" and "External reference cannot be found". "When the fingerprint of a parent item changes, the link is reported as suspect during validation." `doorstop clear` clears suspect links, and can be limited to named parents (`doorstop clear LLT005 REQ002 REQ003`). `--strict-child-check` warns when an item has no links from a child document. — [Doorstop: Validating requirements](https://doorstop.readthedocs.io/en/v2.0/cli/validation/)
- **Review stamps** *(search summary)*: The `reviewed` attribute holds the fingerprint from the last review, or null if the item was never reviewed. `doorstop review` clears unreviewed status. — [Doorstop: Item reference](https://doorstop.readthedocs.io/en/latest/reference/item.html), [Doorstop release notes](https://doorstop.readthedocs.io/en/v2.1/about/changelog/)
- **Known gap** *(search summary)*: Doorstop notices edits to an item, its links and its references, but not edits to the content of a referenced test or source file. A feature discussion proposes hash-based review of external reference content. — [doorstop issue #564](https://github.com/doorstop-dev/doorstop/issues/564)

**sphinx-needs and related tools**
- **Model:** sphinx-needs lets teams "define, link, and analyse engineering objects within your documentation". It offers `need`, `needimport`, `needextend` and `needservice` (including a GitHub service), views (`needtable`, `needflow`, `needpie`, `needextract`, `needreport`), filters, "dynamic functions" for data chains between needs, and schema validation. — [sphinx-needs docs](https://sphinx-needs.readthedocs.io/en/latest/)
- **needs.json:** The `needs` builder "exports all found needs and selected filter results to a single json file". Needs are stored under the version from `conf.py`, and old versions are kept, so archiving the file in git at each release builds a history. A `needs_schema` tags each field as `core`, `links`, `backlinks` or `extra`. `needimport` and `needs_external_needs` read the file for cross-project links. The `needs_id` builder writes one JSON file per need. An experimental 2a1 format (since 9.3.0) is "readable only by the release that wrote it". — [sphinx-needs: Builders](https://sphinx-needs.readthedocs.io/en/latest/builders.html)
- **Test results:** sphinx-test-reports imports test results as need objects that "can be filtered and linked to specification objects". — [sphinx-test-reports](https://sphinx-test-reports.readthedocs.io/en/latest/)
- **Code links:** sphinx-codelinks (1.2.0 on PyPI) creates sphinx-needs items from source comments with a marker such as `@need:`, configured in `ubproject.toml`. Eclipse S-CORE uses it to generate links between implementation, tests and docs. — [PyPI: sphinx-codelinks](https://pypi.org/project/sphinx-codelinks/), [useblocks: trace code](https://x-as-code.useblocks.com/how-to-guides/trace-code/index.html), [Eclipse S-CORE source code linker](https://eclipse-score.github.io/docs-as-code/main/internals/extensions/source_code_linker.html)

**StrictDoc** *(search summary; direct fetches of the user guide returned 404, so the docs site has been reorganized)*
- **Code links:** Source files link to requirements through `@relation` markers in comments, with file, class, function, line or range scope. Function scope works for Python, C, C++ and Rust (Rust since 0.17.0). The reverse `File` relation, from a requirement to a source file, needs `REQUIREMENT_TO_SOURCE_TRACEABILITY`. — [StrictDoc user guide (traceability view)](https://strictdoc.readthedocs.io/en/stable/stable/docs/strictdoc_01_user_guide-TRACE.html), [StrictDoc release notes](https://strictdoc.readthedocs.io/en/latest/latest/docs/strictdoc_04_release_notes-TRACE.html)
- **ReqIF:** StrictDoc has "initial" ReqIF import and export. Since 0.10.0 it reads a ReqIF file in git directly into its HTML view. — [StrictDoc release notes](https://strictdoc.readthedocs.io/en/latest/latest/docs/strictdoc_04_release_notes-TRACE.html)
- **Diff and Changelog:** These web screens compare documentation trees at two git revisions. The server rejects bad input with "Valid Git revisions must be provided." — [StrictDoc server source](https://strictdoc.readthedocs.io/en/latest/_source_files/strictdoc/server/routers/other_router.py.html), [StrictDoc release notes](https://strictdoc.readthedocs.io/en/stable/strictdoc_04_release_notes.html)
- **Interface:** The README itself states only `strictdoc export .` (static HTML) and `strictdoc server .` (local web UI). — [StrictDoc README](https://github.com/strictdoc-project/strictdoc)
- **The same pattern elsewhere** *(search summary; small project, low authority)*: req-cli's `diff` groups requirements into added, removed and changed sets between two git revisions. — [req-cli diff.rs](https://docs.rs/crate/req-cli/0.1.0/source/src/commands/diff.rs)

**Jama Connect** (vendor docs)
- **Suspect links:** "Suspect links appear on an item when changes were made to upstream items." The item "might no longer be correct or complete". "Only updates to certain fields trigger suspect links", and an organization admin picks those fields per item type. A suspect link shows as a red indicator. A user can "Clear" one link or "Clear All" visible links. — [Jama: Clear suspect links](https://help.jamasoftware.com/en/manage-content/coverage-and-traceability/relationships/clear-suspect-links.html), [Jama: Find suspect links](https://help.jamasoftware.com/en/reference/quick-find/find-suspect-links.html)
- **Impact analysis and compliance** *(search summary; vendor blog)*: Impact analysis follows relationships upstream and downstream. Jama ties this change control to DO-178C, ISO 26262 and ISO 13485. — [Jama blog](https://www.jamasoftware.com/?p=58660)

**Polarion and ReqIF**
- **Round trip** *(search summary; vendor blog)*: A ReqIF round trip creates a baseline in Polarion and exports the data back to the sender, who merges the changes. Allowed relations are defined by link roles. — [Siemens Polarion blog](https://blogs.sw.siemens.com/polarion/part-1-how-to-exchange-data-from-ibm-rational-doors-classic-to-siemens-polarion/)
- **Interop friction** *(search summary)*: Polarion's ReqIF files lack the "Relation-Groups" that PTC Windchill RV&S expects on import. The matching OMG issue, raised for about 100 supplier ReqIFs, was still open. — [PTC community thread](https://community.ptc.com/t5/Windchill-Systems-Software/How-to-import-polarion-relations-by-ReqIF-to-RV-amp-S/m-p/923505), [OMG issue REQIF13-8](https://issues.omg.org/issues/REQIF13-8)
- **The standard:** ReqIF, the Requirements Interchange Format, is at version 1.2 (July 2016, formal). It is for exchanging requirements between organizations that cannot share one repository, and is defined by XML schemas (`reqif.xsd`, `driver.xsd`). — [OMG ReqIF](https://www.omg.org/spec/ReqIF/)

### Inferences
- **What the CLI already has:** Its requirement-level `delta.base-stale` fingerprint and its edit-voided approvals are Doorstop's two mechanisms (suspect links and reviewed stamps), applied to deltas and change files.
- **What is missing:** No tool here marks a verified requirement as suspect when the code or tests behind its evidence change. Doorstop's issue #564 shows even Doorstop lacks this, and Jama's suspect triggers are field edits, not code edits. The CLI already keeps code-checked quotes, so it holds the data to do it.
- **Changelog:** A requirement-level changelog between two revisions (StrictDoc's Diff/Changelog, req-cli's `diff`) is cheap for a tool that already parses its spec grammar both ways. It would help reviewers who ask what a merge changed in the living spec.
- **Coverage views:** These (sphinx-needs `needtable`/`needpie`, StrictDoc traceability) answer "which requirements have no test or verification". They help leads and auditors, and could be a few lines in an existing `status`.
- **Interchange:** sphinx-needs' versioned `needs.json` shows that a plain JSON export of the living specs is the realistic interchange format for a small tool. ReqIF's tool-specific quirks (Polarion/PTC) make it costly for little benefit outside regulated supply chains.
- **Who benefits:** Auditors and safety engineers (suspect links, baselines, ReqIF), maintainers (stale-evidence warnings) and reviewers (requirement changelogs).

### Gaps
- Which fields go into Doorstop's fingerprint is not on the fetched validation page.
- StrictDoc's current user guide could not be fetched (404s across several URL forms). Its MID machine identifiers, traceability matrix and JUnit import are unconfirmed here.
- How Jama and Polarion carry suspect state across baselines was not found.
- sphinx-needs `needs_warnings` and constraints were not on the fetched pages.

## 3. Architecture decision record tooling

### Takeaway
ADR tools are thin: numbered Markdown files (`NNNN-title.md`), a status line, and a supersede operation that updates both the old and the new record. Everything else, such as static sites, catalog tabs and search, is presentation. The idea most worth borrowing is MADR's optional "Confirmation" section, which says how compliance with the decision will be checked (a review or an ArchUnit test). That turns a decision into something a verify step can judge.

### Cited Findings
- **MADR 4.0.0 (2024-09-17):**
  - Optional front matter: `status` (proposed, rejected, accepted, deprecated, or "superseded by ADR-0123"), `date`, `decision-makers`, `consulted`, `informed`.
  - Sections: Context and Problem Statement, Decision Drivers, Considered Options, Decision Outcome ("Chosen option: …, because …") with Consequences, Confirmation, Pros and Cons of the Options, More Information.
  - — [MADR](https://adr.github.io/madr/)
- **MADR Confirmation:** "Describe how the implementation of/compliance with the ADR can/will be confirmed". It asks "Is the chosen design and its implementation in line with the decision?" and suggests a design or code review, or an ArchUnit test. "Although we classify this element as optional, it is included in many ADRs." More Information can record when or how the decision should be "re-visited". — [MADR](https://adr.github.io/madr/)
- **MADR file layout:** Files are named `NNNN-title-with-dashes.md` (as adr-tools does) and live in `docs/decisions`. Category subfolders are allowed, with numbers unique per folder. — [MADR](https://adr.github.io/madr/)
- **adr-tools:** `adr init doc/architecture/decisions` creates the folder with a first ADR recording the decision to use ADRs. `adr new` creates the next numbered file and opens an editor. `adr new -s 9 …` creates a new ADR "flagged as superceding ADR 9, and changes the status of ADR 9" to point at the new one. The default folder is `doc/adr`. The repository shows about 5.8k stars and no published releases. — [adr-tools](https://github.com/npryce/adr-tools)
- **Log4brains:** `log4brains adr new` creates ADRs interactively. `log4brains preview` serves a hot-reloading local UI. `log4brains build` writes a static site for GitHub Pages, GitLab Pages or S3. "ADR metadata automatically guessed from its raw text and git logs", so CI needs the full git history. MADR is the default template, and both monorepos and multi-package projects work. UI editing is listed as "coming soon", and the page shows no releases. — [Log4brains](https://github.com/thomvaill/log4brains)
- **Backstage ADR plugin:** A catalog annotation, `backstage.io/adr-location`, points each entity at its ADR folder. ADRs are parsed as MADR, but "Front matter is only recognised in the MADR 3.x form". An ADRs tab is added with `EntityAdrContent`. Search needs the ADR backend plugin. Status (accepted, rejected, superseded) can be styled, and the page documents no automatic filtering of superseded records. — [Backstage community ADR plugin](https://github.com/backstage/community-plugins/tree/main/workspaces/adr/plugins/adr)

### Inferences
- **Change-scoped decisions:** The CLI's `design.md` already records decisions with alternatives and risks (`adk_spec/orchestration/stages/design.py`), but they belong to a single change. ADR practice argues that decisions outlive changes and need a supersede chain. The analogue is to keep accepted decisions per capability when a change is archived, the same way deltas merge into living specs, with "superseded by" written into both records, as adr-tools does.
- **Confirmation:** A Confirmation line per decision ("how we will know the code follows this") would give the verify step a second kind of claim to judge against the diff with code-checked quotes. No ADR tool found here checks confirmation automatically, so this would be an edge.
- **Presentation:** Static sites, Backstage tabs and search are presentation layers that do not fit a local tool with few commands.
- **Who benefits:** Future maintainers (why something is the way it is), reviewers (whether a change contradicts an accepted decision) and architects (supersede history).

### Gaps
- The fetched adr-tools README does not document `adr link`, `adr generate toc` or `adr generate graph`, so they are unconfirmed here.
- No fetched source covers automated checking of ADR compliance in CI, beyond MADR's suggestion of ArchUnit tests.
- How Log4brains infers supersede relations from text was not documented on the fetched page.

## 4. CI policy and quality gates: gating a merge and annotating a pull request

### Takeaway
A local CLI can gate a GitHub merge without being a GitHub App. It runs as a workflow step that sets a required status check (exit code), emits file and line annotations (`::error file=…,line=…::`), and writes a Markdown job summary. Uploading SARIF to code scanning adds deduplication across runs by fingerprint, shows alerts only on changed lines, and lets a ruleset block merges by severity. The Check Runs API (custom buttons, 50 annotations per call) requires a GitHub App, so it suits hosted bots, not a local CLI.

### Cited Findings
**GitHub mechanisms**
- **Check Runs API:**
  - "To create a check run, you must use a GitHub App."
  - Conclusions: `action_required`, `cancelled`, `failure`, `neutral`, `success`, `skipped`, `stale` (set only by GitHub), `timed_out`.
  - Output: `title`, plus Markdown `summary` and `text` of up to 65,535 characters each.
  - Annotations: `path`, `start_line`, `end_line`, `annotation_level` (`notice`, `warning`, `failure`) and `message`, at most 50 per request. Actions steps are capped at 10 warning and 10 error annotations per step.
  - Up to three "requested action" buttons send a webhook back to the app. `external_id` and `details_url` link to the integrator's own system.
  - — [GitHub REST: Check runs](https://docs.github.com/en/rest/checks/runs)
- **Rulesets, status checks:** "Required status checks can be checks or statuses." A ruleset can pin the expected source app: "If the status is set by any other person or integration, merging won't be allowed." Strict mode (the branch must be up to date) is the default. — [GitHub Docs: Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
- **Rulesets, code scanning and quality:** "Require code scanning results" blocks a merge when a required tool finds an alert at a configured severity, while its analysis is still running, or when it is not configured. "Require code quality results" works the same way. "Restrict code coverage" (preview) blocks on a minimum coverage or a coverage drop. — [GitHub Docs: Available rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
- **Rulesets, pull request rules:**
  - Required approvals; dismiss stale approvals when new commits "affect the diff".
  - Code-owner review.
  - "Require an approval from someone other than the last person to push."
  - Conversation resolution.
  - Required reviewer teams scoped by file patterns (up to 15 teams).
  - "An additional approval for unattributed Copilot pull requests" (preview).
  - — [GitHub Docs: Available rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
- **Workflow commands:** Any step can annotate with `::error file={name},line={line},endLine={endLine},title={title}::{message}` (also `::warning` and `::notice`). Markdown appended to `$GITHUB_STEP_SUMMARY` appears on the run summary page. Limits are 1 MiB per step and 20 step summaries shown per job. — [GitHub Docs: Workflow commands](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands)
- **SARIF, deduplication:** Results are matched across runs by `partialFingerprints`, and "Code scanning only uses the `primaryLocationLineHash`". Paths must be stable. The `ruleId` "has to be the same across analysis". — [GitHub Docs: SARIF support](https://docs.github.com/en/code-security/code-scanning/integrating-with-code-scanning/sarif-support-for-code-scanning)
- **SARIF, pull requests and limits:** An alert shows on a pull request only when "all the lines of code identified by the alert exist in the pull request diff", on added or edited lines. Limits are 10 MB per gzipped file and 25,000 results per run (only the top 5,000 are kept). `runAutomationDetails.id` is read as `category/run-id`. — [GitHub Docs: SARIF support](https://docs.github.com/en/code-security/code-scanning/integrating-with-code-scanning/sarif-support-for-code-scanning)

**Danger JS**
- **Model:** A Dangerfile runs in CI with `danger.git.modified_files` and `created_files`, `danger.github.pr` (body, title, additions) and `diffForFile` or `structuredDiffForFile`. — [Danger JS](https://danger.systems/js/), [Danger JS reference](https://danger.systems/js/reference.html)
- **Messages:** `fail()` "Fails a build, outputting a specific reason for failing into a HTML table". `warn()` "does not fail the build". `message()` differs from `warn()` only by its emoji. `markdown()` adds raw Markdown under the table. All four take an optional `file` and `line`. Over time "the message is amended to reflect the current state of the code review". — [Danger JS reference](https://danger.systems/js/reference.html), [Danger JS](https://danger.systems/js/)

**OPA and Conftest**
- **Model:** Rego policies with `deny`, `violation` (structured data) and `warn` rules run against structured inputs: YAML, JSON, TOML, HCL, Dockerfile, CODEOWNERS, INI, XML and others, but not Markdown. A `_loc` field (file and line) in a rule's result points `json` and `github` output at a location. `conftest verify` unit-tests the policies. — [Conftest](https://www.conftest.dev/)
- **Output and exit codes:** Outputs are `stdout`, `json`, `tap`, `table`, `junit`, `github`, `azuredevops` and `sarif`. By default Conftest exits 1 only on failure. With `--fail-on-warn` it exits 0 (clean), 1 (warnings) or 2 (failures). `--combine` passes every file into one input so a rule can check across files. — [Conftest options](https://www.conftest.dev/options/)

**SonarQube quality gates** (vendor docs)
- **Conditions:** A gate's conditions apply to new code or overall code. Pull requests are judged on new-code conditions only. The default "Sonar way" requires no new issues, every new Security Hotspot reviewed, at least 80% coverage on new code and at most 3% duplication. Coverage and duplication conditions are ignored under 20 new lines. — [SonarQube: Introduction to quality gates](https://docs.sonarsource.com/sonarqube-server/latest/quality-standards-administration/managing-quality-gates/introduction-to-quality-gates/)
- **Pull requests:** The gate status appears as pull request decoration, and "It can be used to block the merge of the pull request if the quality gate fails". A new built-in "Sonar way for agentic AI" gate is recommended for agent-centric development. — [SonarQube: Introduction to quality gates](https://docs.sonarsource.com/sonarqube-server/latest/quality-standards-administration/managing-quality-gates/introduction-to-quality-gates/)

### Inferences
- **The cheapest gate:** The offline `validate` (with `--json`, which exists) as a required status check needs only a workflow file. Adding GitHub annotations and a job summary when `GITHUB_ACTIONS` is set would put findings on the pull request without a new subcommand.
- **Model calls in CI:** A gate that needs verify sends live model calls with a token in CI. That conflicts with the "no live model call without a go-ahead" rule unless the owner sets it up on purpose. The gate should check a committed verify report and its freshness (commit and fingerprints) rather than re-run verify.
- **SARIF:** Verify findings as SARIF (`ruleId` = finding code; `partialFingerprints` from requirement ID plus quote) would get deduplication across runs, display on changed lines only, and severity-based merge blocking for free. Code scanning on private repositories may need a paid GitHub plan (unverified here).
- **Existing parallels:** The CLI already has GitHub's "dismiss stale approvals on push" (approval fingerprints) and something like "approval from someone other than the last pusher" (its two-approver tiers). SonarQube's "new code only" matches judging only a change's own requirements.
- **Policy engines:** Danger and Conftest show policy-as-code with fail, warn and message levels. The CLI's `DEMANDS` table already is that policy, so embedding Rego would be heavy for no gain.
- **Who benefits:** Maintainers (merge protection), reviewers (annotations on the exact line) and teams with compliance needs (an auditable gate).

### Gaps
- Whether `GITHUB_TOKEN` can create check runs is not stated on the fetched page.
- Whether code scanning SARIF upload and "Require code scanning results" are available on private repositories without GitHub Advanced Security, or GitHub Code Security, was not checked.
- Whether Danger's inline comments come from the `file` and `line` arguments is only implied by the reference page.
- GitHub artifact attestations and in-toto, as a way to sign an approval or verification record, were not researched.

## 5. What would give a spec-driven CLI a genuine edge, and what does not fit a local tool with few commands

### Takeaway
The best transfers deepen what the CLI already does well, which is fingerprints, code-checked quotes and per-requirement verdicts. Each can ride on an existing command (`validate`, `status`, `verify`, `approve`, `archive`) rather than a new one. Hosted, bot-shaped, enterprise-interchange and dashboard features do not fit.

### Cited Findings
These are the anchors for the ranking below, from the sections above:
- Doorstop flags a link as suspect when the parent's fingerprint changes, and `doorstop clear` resolves it. — [Doorstop validation](https://doorstop.readthedocs.io/en/v2.0/cli/validation/)
- Doorstop does not track edits to referenced files' content. — [doorstop issue #564](https://github.com/doorstop-dev/doorstop/issues/564) *(search summary)*
- GitHub dedupes findings across runs by fingerprint and a stable `ruleId`, and shows them only on changed lines. — [GitHub SARIF support](https://docs.github.com/en/code-security/code-scanning/integrating-with-code-scanning/sarif-support-for-code-scanning)
- Greptile suppresses repeatedly ignored categories but never security or logic findings. — [Greptile memory and learning](https://www.greptile.com/docs/how-greptile-works/memory-and-learning)
- CodeRabbit holds learnings for admin approval (`approval_delay`) and scopes them by path. — [CodeRabbit learnings](https://docs.coderabbit.ai/knowledge-base/learnings)
- Qodo has a "verified but needs manual testing" verdict. — [PR-Agent ticket context](https://raw.githubusercontent.com/qodo-ai/pr-agent/main/docs/docs/core-abilities/fetching_ticket_context.md)
- CodeRabbit separates a ticket's "direct targets" from "background context". — [CodeRabbit PR validation](https://docs.coderabbit.ai/issues/pr-validation)
- MADR has a Confirmation section and a supersede status. — [MADR](https://adr.github.io/madr/)
- GitHub has workflow-command annotations and job summaries. — [GitHub workflow commands](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands)
- sphinx-needs writes a versioned `needs.json`. — [sphinx-needs builders](https://sphinx-needs.readthedocs.io/en/latest/builders.html)
- StrictDoc compares two git revisions in its Diff and Changelog screens. — [StrictDoc release notes](https://strictdoc.readthedocs.io/en/stable/strictdoc_04_release_notes.html) *(search summary)*
- Check runs require a GitHub App. — [GitHub check runs](https://docs.github.com/en/rest/checks/runs)
- ReqIF exchange is fragile across vendors. — [OMG REQIF13-8](https://issues.omg.org/issues/REQIF13-8) *(search summary)*

### Inferences
**Best transfers, in rough order of edge per cost.** Each is a judgment for the owner to weigh against the golden rule.
1. **Suspect verification: the clearest edge.** Fingerprint the files or hunks that each verify verdict quoted, which code has already checked. `status` and `validate` would then mark a verified requirement "suspect" once that evidence changes. This is Doorstop's and Jama's suspect link moved from requirement-to-requirement to requirement-to-code, which neither tool does. It needs no model call to detect, and it fits existing commands. It mostly helps maintainers and auditors.
2. **Stable finding fingerprints, plus recorded dismissals.** Give each check or verify finding a fingerprint (code + requirement ID + normalized quote, in the spirit of SARIF's `partialFingerprints`). A re-run then recognizes a finding it raised before, and a person's dismissal, with a reason, is recorded and not raised again. Never suppress security findings or the tier's must-haves (Greptile's rule). Dismissals could become `lessons.md` lines only after a person confirms them (CodeRabbit's `approval_delay` idea). Fits `check`, `verify` and `approve`, and helps authors and reviewers through less noise.
3. **CI-friendly output on existing commands.** When `GITHUB_ACTIONS` is set, `validate` (and the gate that reads a committed verify report) prints `::error`/`::warning` annotations with file and line, and appends a short Markdown summary to `$GITHUB_STEP_SUMMARY`. A ruleset's "Require status checks" then gates the merge, with no GitHub App, bot or new subcommand. SARIF output is an optional step beyond this. Helps maintainers.
4. **A fourth verdict level: "met in code, needs manual check".** This is Qodo's "PR Code Verified" and close to CodeRabbit's "Unclear". It suits requirements a diff cannot prove (UI, behaviour across environments), and is worth adding if verify lacks it (not checked here). Helps testers and approvers.
5. **Confirmation for decisions (MADR).** Give each design decision a one-line "how we will confirm it". Verify then judges it like a requirement, with checked quotes, and on `archive` accepted decisions could be kept per capability with "superseded by" links. This is moderate cost; it is worth it only if decisions are often revisited.
6. **Changelog and coverage in `status`.** A requirement-level changelog between two git revisions (StrictDoc, req-cli) and a count of requirements with no verification or test evidence (sphinx-needs tables, StrictDoc matrix). These are cheap given the parsed grammars, and help leads and reviewers.
7. **Ticket context as text, not an integration.** Let a brief take acceptance criteria from a pasted issue or a local file, and keep CodeRabbit's split between direct targets and background context. A live Jira or Linear integration brings network access, tokens and secret handling, which is costly for a local tool.
8. **A JSON export of living specs** (sphinx-needs' `needs.json`, with versions) for other tools. `--json` patterns already exist. It is low cost but also low benefit until someone asks.

**Do not fit a local CLI with few commands:**
- ReqIF export or import. It is an enterprise ALM exchange format with documented vendor quirks: large effort for a rare user.
- Check Runs API buttons and hosted pull request bots that comment on each push. They need a GitHub App or hosted service, plus live model calls in CI, which the CLI's rules forbid without a go-ahead.
- Dashboards and static sites: CodeRabbit's learnings dashboard, Log4brains sites, Backstage tabs, Jama's Live Trace views.
- Learning from emoji reactions, since a local CLI has no pull request surface.
- Admin-configured suspect-trigger fields (Jama). The CLI's fingerprint already covers the whole requirement.
- An embedded policy engine (OPA/Rego, Danger). The `DEMANDS` table is already the policy.
- ALM-style baselines. Git commits and tags, which verify already records, serve the purpose.
- Automatic, unreviewed rule inference from pull request history (Rule Miner, Greptile inferred rules). It needs PR history and a hosted index, and conflicts with the CLI's "a model's words count only where code finds them" stance unless a person confirms each rule.

### Gaps
- I did not measure how often check or verify findings repeat across runs in practice, which decides whether item 2 pays off. The repository's `docs/measurements/` may hold that data. It was not read for this note.
- Whether verify already has an "unclear / needs manual verification" verdict, and whether stage context already includes AGENTS.md or CLAUDE.md, was not checked in the source.
- No source was found that quantifies the benefit of any of these features for spec-driven tools specifically. Vendor figures (Greptile's "80% reduction") are marketing.
