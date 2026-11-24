# Industry standards, protocols and conventions for a spec-driven development CLI with AI stages (as of 2026-11-24)

Scope note: each section gives the standard's current version and date, its requirements, and (under Inferences) an
"Adoption note": what a local, file-based spec-driven CLI with model stages, code gates, requirement IDs, approvals by
file fingerprint, an MCP server and an Agent Skill could adopt, the capability it adds, and what it would look like.
Everything fetched was treated as data. Where only secondary sources were found, that is said.

## 1. Requirements notation and quality: EARS, ISO/IEC/IEEE 29148, Gherkin/BDD, and what tools check automatically

### Takeaway
EARS (2009, Rolls-Royce) is a small, regex-checkable sentence grammar (zero or more preconditions, at most one trigger,
one system, one or more responses); ISO/IEC/IEEE 29148:2018 (still the active edition) names nine quality
characteristics for an individual requirement plus set-level ones and language criteria; Gherkin is the de facto
scenario grammar (Feature/Rule/Example, Given/When/Then, 3-5 steps per example). Automatic checking in the field is
pattern conformance plus "requirements smells" detection, with modest precision (59% in the best-known study), so it
works as warnings, not gates.

### Cited Findings
- **EARS patterns**: Ubiquitous "The <system> shall <response>"; State-driven "While <precondition(s)>, the <system>
  shall …"; Event-driven "When <trigger>, the <system> shall …"; Optional feature "Where <feature is included>, the
  <system> shall …"; Unwanted behaviour "If <trigger>, then the <system> shall …"; Complex combines them, e.g. "While
  …, when …, the <system> shall …". — [EARS, Alistair Mavin](https://alistairmavin.com/ears/)
- EARS generic syntax: "While <optional pre-condition>, when <optional trigger>, the <system name> shall <system
  response>"; ruleset: zero or more preconditions, zero or one trigger, one system name, one or more system responses.
  — [EARS](https://alistairmavin.com/ears/)
- EARS was developed at Rolls-Royce PLC analysing airworthiness regulations for a jet-engine control system, first
  published 2009; "no specialist tool is necessary"; used by Airbus, Bosch, Dyson, Honeywell, Intel, NASA, Rolls-Royce,
  Siemens. — [EARS](https://alistairmavin.com/ears/)
- **ISO/IEC/IEEE 29148:2018**, "Systems and software engineering — Life cycle processes — Requirements engineering",
  published 30 Nov 2018, edition 2.0, listed as active; it defines what makes a good requirement, its attributes and
  characteristics. — [IEEE Xplore](https://ieeexplore.ieee.org/document/8559686); [IEC webstore](https://webstore.iec.ch/publication/64315)
- 29148:2018 clause structure: 5.2.5 "Characteristics of individual requirements", 5.2.6 "Characteristics of a set of
  requirements", 5.2.7 "Requirement language criteria". — [iTeh sample of ISO/IEC/IEEE 29148:2018 (table of contents)](https://cdn.standards.iteh.ai/samples/72089/62bb2ea1ef8b4f33a80d984f826267c1/ISO-IEC-IEEE-29148-2018.pdf)
- The nine individual-requirement characteristics in 29148:2018: necessary, appropriate, unambiguous, complete,
  singular, feasible, verifiable, correct, conforming. — [ResearchGate: NLP framework for verifying to ISO 29148-2018 (abstract)](https://www.researchgate.net/publication/385802396_Well-Formed_Quality_of_System_Requirements_for_Verifying_to_ISO_29148-2018_A_Natural_Language_Processing_NLP_Based_Framework_and_Quantitative_Metric)
- The INCOSE Guide to Writing Requirements is at v4 (INCOSE-TP-2010-006-04, July 2023); it defines characteristics
  C1-C14 for needs/requirements and sets; C9 "Conforming" means following an approved pattern and style guide. —
  [INCOSE GtWR v4 summary sheet](https://www.incose.org/docs/default-source/working-groups/requirements-wg/guidetowritingrequirements/incose_rwg_gtwr_v4_summary_sheet.pdf)
  (returned HTTP 403 to direct fetch; content seen via search snippets); [se-trends review of the GtWR](https://www.se-trends.de/en/review-incose-guide-for-writing-requirements/)
- **Gherkin**: one `Feature` per `.feature` file; `Rule` (since Gherkin 6) groups examples of one business rule;
  `Example`/`Scenario`; steps `Given`/`When`/`Then`/`And`/`But` (keywords ignored when matching step definitions);
  `Background` (one per Feature or Rule); `Scenario Outline` with `Examples` tables and `<parameter>` placeholders;
  `@tags`; doc strings; data tables; 70+ languages via `# language: xx`. Guidance: 3 to 5 steps per example; keep
  Background short (~4 lines). Page last updated Nov 23, 2026. — [Cucumber Gherkin reference](https://cucumber.io/docs/gherkin/reference)
- **Automatic checking**: "Requirements Smells" (Femmer, Méndez Fernández, Wagner, Eder; J. Systems and Software
  2016) transfers code smells to requirements; their prototype tool Smella reached on average 59% precision and 82%
  recall, with some smells "not clearly distinguishable"; the authors position it as a supplement to reviews. —
  [arXiv:1611.08847](https://arxiv.org/abs/1611.08847)
- LLM-based requirements QA against 29148 characteristics is an active research line, e.g. "Leveraging LLMs for the
  Quality Assurance of Software Requirements". — [arXiv:2408.10886](https://arxiv.org/pdf/2408.10886)

### Inferences
- EARS is the most code-checkable of the three: a deterministic parser can classify each requirement sentence into one
  of the six patterns and flag a missing "shall", two triggers, or a compound response, which matches the "a model
  drafts, code gates" split.
- 29148's "singular", "verifiable", "unambiguous" and "conforming" are the characteristics with partial mechanical
  proxies (one "shall" per statement, a scenario/verification method present, weak-word lists, pattern match);
  "necessary", "appropriate", "correct" and "feasible" need judgment (a model check stage or a person).
- Given ~59% precision for smell detection, smells belong as warnings that a model or person resolves, not as hard
  gate failures.
- **Adoption note (quality, auditability)**: (a) an EARS-conformance check in the validate gate: each requirement
  statement tagged with its EARS pattern, a finding when none matches (tier-dependent: warning in light tiers, block in
  strict); (b) a 29148 language-criteria word list (subjective, vague, open-ended terms) as warnings carrying a stable
  finding code; (c) a per-requirement record of which 29148 characteristics the model check judged, so the check
  report reads as a 29148 review; (d) optional Gherkin export: each requirement's scenarios written as a `Rule` with
  `Example`s in a `.feature` file tagged `@REQ-ID`, so pytest-bdd/Cucumber can bind step definitions. (d) is the most
  work and only pays for teams already running BDD.

### Gaps
- The exact 29148:2018 set-level characteristics (5.2.6) and the list of language criteria / terms to avoid (5.2.7)
  could not be read: the standard is paywalled and the free sample holds only the table of contents. Commonly cited
  lists (superlatives, subjective language, vague pronouns, ambiguous adverbs/adjectives, open-ended terms,
  comparatives, loopholes, totality terms, negative statements) are unverified here.
- No current open-source EARS linter or Gherkin linter was verified in this session.

## 2. Traceability: requirements-to-code-to-test conventions, ReqIF, and suspect links

### Takeaway
ReqIF 1.2 (OMG, July 2016) is still the only formal requirements interchange format; "suspect link" practice is
universal in commercial RM tools: a change upstream automatically flags downstream links, and a person clears them
after review. In code-centric open-source practice, traceability is done with IDs in Markdown and tags in source/tests
(OpenFastTrace et al.) and with test-case properties in JUnit XML.

### Cited Findings
- **ReqIF** current version 1.2, status "formal", published July 2016 (supersedes 1.2 Beta1); 1.1 October 2013; 1.0.1
  April 2011; machine-readable files include reqif.xsd and driver.xsd; purpose: exchange requirements between
  organizations that cannot share a repository, for authoring-tool import/export. — [OMG ReqIF](https://www.omg.org/spec/ReqIF/)
- **Suspect links**: downstream items linked to a changed upstream requirement are flagged suspect, since they may no
  longer match; suspect traces may be marked automatically but must be cleared manually, after investigating and making
  any required downstream changes. — [PTC Windchill RV&S help: Managing Suspect Trace Relationships](https://support.ptc.com/help/windchillrvs/r13.2.0.0/en/IntegrityHelp/int-user/client_docs_managing_suspect_trace_relationships.html)
- **OpenFastTrace** (open source) is a requirement management and tracing suite that shows whether planned
  requirements were implemented and flags obsolete parts; v4.x needs Java 17+; distributed via APT, Homebrew, JBang,
  Maven/Gradle plugins; example command references 4.10.0. — [OpenFastTrace on GitHub](https://github.com/itsallcode/openfasttrace)
- **JUnit XML** has no official specification; common subset: `testsuites` > `testsuite` > `testcase` with
  `failure`/`error`/`skipped`, `system-out`/`system-err`, and `properties/property` (name/value) at suite or case
  level; testcase attributes `name`, `classname`, `time`, `file`, `line`; pytest and Playwright support testcase
  properties. — [testmoapp/junitxml](https://github.com/testmoapp/junitxml)
- GitHub code scanning shows a SARIF alert in a pull request's checks only when every line the alert identifies is in
  the PR diff and was added or edited, which favours findings located on the changed spec lines. — [GitHub SARIF support](https://docs.github.com/en/code-security/code-scanning/integrating-with-code-scanning/sarif-support-for-code-scanning)

### Inferences
- A requirement ID plus a version or content hash is the minimal mechanism behind "suspect": anything that recorded
  "covers REQ-7 @ hash h" becomes suspect when REQ-7's text hash changes.
- **Adoption note (auditability)**: (a) store, per requirement in the living spec, a short content hash; tasks,
  verification verdicts and test links record the hash they were made against; when a merge changes a requirement,
  `status`/`validate` lists the now-suspect tasks/tests/verdicts, and re-running verify (or a person) clears them.
  This reuses the existing approval-fingerprint idea at requirement granularity and needs no new command. (b) a
  convention for tests to name the requirement they cover (e.g. a pytest marker that writes `record_property
  ("requirement", "CAP-REQ-3")`), so JUnit XML from the project's own test run carries requirement links that the
  verify stage and CI tools can read. (c) ReqIF export is possible (map capability → SPECIFICATION, requirement →
  SPEC-OBJECT) but is a large XML mapping whose value is limited to enterprises with DOORS/Polarion; likely defer.

### Gaps
- OpenFastTrace's exact ID syntax (`type~name~revision`), its `Needs:`/`Covers:` keywords and source-tag syntax were not
  on the fetched page (they are in its user guide, not fetched).
- No standard JUnit XML property name for linking requirements was found (tools like Xray use their own); ReqIF element
  names (SPEC-OBJECT, SPEC-RELATION) were not confirmed from the OMG page itself.

## 3. Architecture decisions: ADR and MADR formats and status lifecycle

### Takeaway
MADR 4.0.0 (2024-09-17) is the current Markdown ADR template: optional YAML front matter (`status`, `date`,
`decision-makers`, `consulted`, `informed`), required Context/Considered Options/Decision Outcome, files
`docs/decisions/NNNN-title-with-dashes.md`, status values proposed/rejected/accepted/deprecated/"superseded by ADR-NNNN".

### Cited Findings
- MADR 4.0.0 released 2024-09-17 (4.0.0-beta 2024-09-02); MADR stands for "Markdown Architectural Decision Records". —
  [MADR](https://adr.github.io/madr/)
- Sections: title (H1); Context and Problem Statement (required); Decision Drivers (optional); Considered Options
  (required); Decision Outcome (required) with optional Consequences and Confirmation; Pros and Cons of the Options
  (optional, Good/Neutral/Bad); More Information (optional). — [MADR](https://adr.github.io/madr/)
- Front matter (all optional): `status`, `date`, `decision-makers`, `consulted`, `informed`. Status examples:
  `proposed`, `rejected`, `accepted`, `deprecated`, `superseded by ADR-0123` (list marked non-exhaustive). —
  [MADR](https://adr.github.io/madr/)
- File naming `NNNN-title-with-dashes.md` (consecutive number, lowercase, dashes) in `docs/decisions/`; markdownlint
  config and an example GitHub workflow are provided; the page says there is no tooling supporting MADR 3.0.0+ for
  automatic creation. — [MADR](https://adr.github.io/madr/)

### Inferences
- MADR's "Confirmation" subsection (how compliance with the decision is confirmed) maps directly onto a verify stage
  that judges whether code follows a recorded design decision.
- **Adoption note (interoperability)**: render each decision in a change's `design.md` in MADR shape (Context,
  Considered Options, Decision Outcome, Consequences, Confirmation) and, on archive, write accepted decisions to
  `docs/decisions/NNNN-*.md` with MADR front matter (`status: accepted`, `date`, `decision-makers` = approvers). A
  later change that reverses one sets the old file to `superseded by ADR-NNNN`. This gives ADR-tool and docs-site
  compatibility for little code (a renderer and a parser, like the existing Markdown grammars). Writing outside
  `.spec/` is a product decision.

### Gaps
- Nygard's original ADR format and adr-tools/log4brains current versions were not fetched in this session.

## 4. Results interchange: SARIF 2.1.0, JUnit XML, GitHub check runs and annotations, GitLab code quality

### Takeaway
SARIF 2.1.0 (OASIS Standard, March 2020; errata 01 2023) is the format for findings in GitHub code scanning; GitLab
uses a CodeClimate-subset JSON for code quality and JUnit XML for test reports; GitHub check runs need a GitHub App,
while plain workflow commands (`::error file=…,line=…::msg`) and `$GITHUB_STEP_SUMMARY` give annotations and a
Markdown summary from any CLI step.

### Cited Findings
- SARIF 2.1.0 at OASIS: `os/` (OASIS Standard) folder dated 27-Mar-2020; `errata01/` dated 01-Sep-2023, consolidated
  documents 28-Aug-2023. — [OASIS SARIF v2.1.0 directory](https://docs.oasis-open.org/sarif/sarif/v2.1.0/)
- GitHub code scanning supports only SARIF 2.1.0. Required: `$schema`, `version`, `runs[]`; `tool.driver.name`; rules
  `id`, `shortDescription.text`, `fullDescription.text`, `help.text`; results `message.text`, `locations[]`
  (`physicalLocation.artifactLocation.uri`, `region`), `partialFingerprints`; `ruleId` must stay the same across
  analyses. — [GitHub SARIF support](https://docs.github.com/en/code-security/code-scanning/integrating-with-code-scanning/sarif-support-for-code-scanning)
- Only `partialFingerprints.primaryLocationLineHash` is used to match results across runs; the `upload-sarif` action
  fills it if missing, the REST API does not (duplicates result); file paths must be consistent across runs. — [GitHub SARIF support](https://docs.github.com/en/code-security/code-scanning/integrating-with-code-scanning/sarif-support-for-code-scanning)
- Limits: 10 MB gzip per file; 20 runs per file; 25,000 results per run (top 5,000 shown); 25,000 rules per run; 1,000
  locations per result (100 shown); 20 tags per rule (10 shown). Severity: `level` note/warning/error (default
  warning); `properties.security-severity` 0.1-10 for security rules; `properties.problem.severity`
  (error/warning/recommendation) for others. `runAutomationDetails.id` category separates analyses (split at last `/`).
  Upload via `upload-sarif` action or `/code-scanning/sarifs` REST endpoint. — [GitHub SARIF support](https://docs.github.com/en/code-security/code-scanning/integrating-with-code-scanning/sarif-support-for-code-scanning)
- **GitHub check runs**: "To create a check run, you must use a GitHub App"; output `title`, `summary` (≤65,535 chars
  Markdown), `text`, `annotations`, `images`; annotation `path`, `start_line`, `end_line`, `annotation_level`
  (notice/warning/failure), `message` (≤64 KB), optional `title`, `raw_details`; 50 annotations per request; GitHub
  Actions limited to 10 warning and 10 error annotations per step; conclusions success/failure/neutral/cancelled/
  skipped/timed_out/action_required; API version header `X-GitHub-Api-Version: 2026-03-10`. — [GitHub REST: check runs](https://docs.github.com/en/rest/checks/runs)
- **Workflow commands**: `::error file={name},line={line},endLine={endLine},title={title}::{message}` (also
  `::warning`, `::notice`; `col`, `endColumn`); job summary: Markdown appended to `$GITHUB_STEP_SUMMARY`, max 1 MiB per
  step, max 20 step summaries displayed per job, secrets auto-masked; `::add-mask::` redacts a value. — [GitHub workflow commands](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands)
- **GitLab code quality** report: a JSON array; each object needs `description`, `check_name`, `fingerprint`,
  `location.path` (relative, no `./`), `location.lines.begin` or `location.positions.begin.line`, `severity`
  (info/minor/major/critical/blocker); declared as a `codequality` report artifact; BOM rejected. Shown in the MR
  Reports tab on Free/Premium/Ultimate, the pipeline Code Quality tab on Premium/Ultimate, and as diff gutter marks on
  Ultimate only. The CodeClimate-based CI template was deprecated in GitLab 17.3, removal planned for 19.0 (the report
  format itself remains). — [GitLab Code Quality](https://docs.gitlab.com/ci/testing/code_quality/)
- **JUnit XML**: no official spec; de facto subset as in section 2. — [testmoapp/junitxml](https://github.com/testmoapp/junitxml)

### Inferences
- The project's gate findings are already "a stable code + a sentence + a quoted location", which is exactly the SARIF
  result shape (`ruleId` = finding code, `message.text` = sentence, `region` = where `quoted_at` found the quote).
- One finding model can emit three formats: SARIF (GitHub), GitLab code-quality JSON, and workflow-command lines;
  verify verdicts per requirement fit JUnit XML (one `testcase` per requirement, `failure` when not met), which GitLab
  (`artifacts:reports:junit`) and Jenkins consume.
- **Adoption note (CI integration)**: an output option on the existing `check`/`validate`/`verify` commands (not a
  new subcommand), e.g. `--report sarif|junit|codequality PATH`, plus automatic `::warning file=…,line=…::` lines and a
  short `$GITHUB_STEP_SUMMARY` when `GITHUB_ACTIONS=true`. Fingerprint = hash of (finding code, file, quoted text) so
  alerts survive line moves and match across runs; `runAutomationDetails.id` = `spec/<change-id>`. Check runs are not
  worth it (need a GitHub App). Secrets: annotations and summaries leave the machine, so they must pass the same
  scrubbing as model input.

### Gaps
- Whether GitHub code scanning on private repositories still requires GitHub Advanced Security / Code Security
  licensing in 2026 was not stated on the fetched page.
- GitLab's `artifacts:reports:junit` page was not fetched.

## 5. Observability of AI agents: OpenTelemetry GenAI semantic conventions and CLI traces

### Takeaway
The GenAI semantic conventions moved out of the core OTel repo into `open-telemetry/semantic-conventions-genai`, whose
first standalone release v0.1.0 (2026-11-21, depends on semconv v1.45.0) made many breaking renames; everything is
still "Development" status. Spans: `gen_ai.client.inference` (`{operation} {model}`), `execute_tool {tool}`,
`create_agent`, `invoke_agent` (client/internal; workflows now recorded as `invoke_agent` internal with
`gen_ai.operation.name = invoke_workflow`). Message content is opt-in. Google ADK ships OTel instrumentation.

### Cited Findings
- The opentelemetry.io GenAI semconv pages now say the conventions "have moved" to
  `open-telemetry/semantic-conventions-genai` and the old pages are no longer maintained. — [opentelemetry.io GenAI semconv](https://opentelemetry.io/docs/specs/semconv/gen-ai/);
  [semantic-conventions-genai repo](https://github.com/open-telemetry/semantic-conventions-genai)
- v0.1.0 is the "first standalone release", listing changes since semantic-conventions v1.41.0 and depending on
  semantic-conventions v1.45.0; GitHub release published 2026-11-21. — [CHANGELOG](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/CHANGELOG.md);
  [releases](https://github.com/open-telemetry/semantic-conventions-genai/releases)
- Breaking changes in v0.1.0 include: `invoke_workflow` span merged into `gen_ai.invoke_agent.internal`
  (`gen_ai.operation.name` stays `invoke_workflow`, `gen_ai.workflow.name` replaced by `gen_ai.agent.name`);
  `gen_ai.client.token.usage` histogram replaced by `gen_ai.client.inference.operation.input_tokens` /
  `…output_tokens` (record 0 when usage missing, `error.type` on failure); new `gen_ai.client.inference.duration`,
  `gen_ai.client.invoke_agent.duration`, `gen_ai.execute_tool.duration` metrics replacing
  `gen_ai.client.operation.duration`; `gen_ai.usage.cache_creation.input_tokens` → `cache_write`; MCP spans use
  `rpc.status_code`; structured (not JSON-string) values required for schema-defined attributes. — [CHANGELOG](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/CHANGELOG.md)
- Status of the GenAI conventions document: Development. — [docs/gen-ai/README.md](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/README.md)
- Inference span `gen_ai.client.inference`: name `{gen_ai.operation.name} {gen_ai.request.model}`; required
  `gen_ai.operation.name`, `gen_ai.provider.name`; conditionally `gen_ai.conversation.id`, `gen_ai.request.model`;
  recommended `gen_ai.usage.input_tokens` / `gen_ai.usage.output_tokens` (input SHOULD include cached tokens); opt-in
  `gen_ai.input.messages`, `gen_ai.output.messages`, `gen_ai.system_instructions`, `gen_ai.tool.definitions`, and
  `*_ref` variants holding a URI to externally stored content. — [client-inference.md](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/client-inference.md)
- Tool span `gen_ai.execute_tool`: name `execute_tool {gen_ai.tool.name}`; required `gen_ai.operation.name`,
  `gen_ai.tool.name`; conditional `gen_ai.agent.name`, `gen_ai.conversation.id`, `gen_ai.tool.call.id`; opt-in
  `gen_ai.tool.call.arguments` / `gen_ai.tool.call.result`. — [execute-tool.md](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/execute-tool.md)
- Agent spans: `create_agent {gen_ai.agent.name}`; invoke agent client and internal spans named
  `{gen_ai.operation.name} {gen_ai.agent.name}`; `gen_ai.agent.name` MUST be low cardinality. — [gen-ai-agent-spans.md](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md)
- The repo also holds MCP, A2A, OpenAI, Anthropic, AWS Bedrock conventions (`docs/gen-ai/mcp.md`, `a2a.md`, …). —
  [semantic-conventions-genai repo tree](https://github.com/open-telemetry/semantic-conventions-genai/tree/main/docs/gen-ai)
- MCP 2026-07-28 documents OTel trace-context propagation through `_meta` keys `traceparent`, `tracestate`, `baggage`
  (SEP-414), and recommends OpenTelemetry instead of MCP Logging. — [MCP 2026-07-28 changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- Google ADK includes OpenTelemetry instrumentation (ADK ≥1.17.0); Google's guide sets
  `OTEL_SEMCONV_STABILITY_OPT_IN='gen_ai_latest_experimental'`,
  `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT='EVENT_ONLY'` (warns not to set `true`), and recommends
  `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS='false'` to keep PII and oversized attributes out of spans; ADK's model span is
  `call_llm`; `adk web --otel_to_cloud` exports to Google Cloud. — [Google Cloud: Instrument ADK applications with OpenTelemetry](https://docs.cloud.google.com/stackdriver/docs/instrumentation/ai-agent-adk)
- Third-party ADK instrumentations differ in names (e.g. Go ADK writes `generate_content`; TypeScript keeps
  `call_llm`), so attribute sets vary by instrumentation. — [Amplitude ADK integration](https://amplitude.com/docs/amplitude-ai/agent-analytics/integrations/google-adk) (secondary)

### Inferences
- Because ADK already creates spans, the low-cost path is to let ADK's own instrumentation export and add a few
  parent spans of one's own (one `invoke_workflow` per command, one `invoke_agent` per stage, `execute_tool` per
  code-reading tool), with token counts from the existing token ledger on inference spans.
- The conventions are Development and just broke names three days before this note; anything emitted should be pinned
  to a convention version and treated as unstable.
- **Adoption note (auditability, operations)**: off by default; on when the standard OTel environment variables
  (exporter endpoint) are set, so there is no new command or flag. Never set the opt-in content attributes
  (`gen_ai.input.messages`, `gen_ai.system_instructions`, tool arguments/results) and force
  `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false`, consistent with a "secrets never reach a recording" rule; record gate
  outcomes (finding codes, tries) as span attributes or events instead. Propagate `traceparent` into MCP subprocess
  calls so an assistant's trace links to the CLI's.

### Gaps
- How other CLIs (Gemini CLI, Claude Code, Codex) configure and emit OTel telemetry was not verified in this session.
- Whether the Python `opentelemetry-instrumentation-google-genai` package already emits the v0.1.0 names was not
  checked.

## 6. Model Context Protocol: current specification beyond tools, and client support in 2026

### Takeaway
The current MCP revision is **2026-07-28** (previous 2025-11-25). It made MCP stateless (no `initialize`, no sessions;
version and client capabilities ride in each request's `_meta`; servers MUST implement `server/discover`), replaced
server-initiated requests (sampling, elicitation, roots) with Multi Round-Trip Requests (`resultType:
"input_required"`), moved Tasks to an official extension (`io.modelcontextprotocol/tasks`), and deprecated Roots,
Sampling and Logging. Tools remain by far the most supported primitive: in the community client table (39 clients) tools are
supported by 28 (every coding assistant listed), resources by 11, prompts by 10, elicitation by 11 and tasks by 2.

### Cited Findings
- 2026-07-28 major changes: removal of protocol-level sessions and `Mcp-Session-Id` (SEP-2567); removal of the
  `initialize` handshake, with `io.modelcontextprotocol/protocolVersion` and `…/clientCapabilities` in every
  request's `_meta` (SEP-2575); `server/discover` MUST be implemented; `subscriptions/listen` replaces the GET endpoint
  and `resources/subscribe`; `ping`, `logging/setLevel` and `notifications/roots/list_changed` removed; request-scoped
  `notifications/progress` and `notifications/message` continue on the request's response stream. — [MCP 2026-07-28 changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- Tasks moved out of core into the official extension `io.modelcontextprotocol/tasks`: polling via `tasks/get`, new
  `tasks/update` for client-to-server input, `tasks/list` removed, servers may return task handles unsolicited
  (SEP-2663). — [MCP 2026-07-28 changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- Multi Round-Trip Requests replace server-initiated `roots/list`, `sampling/createMessage`, `elicitation/create`:
  the server returns `InputRequiredResult` with `inputRequests`; the client retries the original request with
  `inputResponses`; every result carries `resultType` (`complete` / `input_required`) (SEP-2322); URL-mode
  elicitation's `notifications/elicitation/complete` and `elicitationId` removed (state goes in `requestState`). —
  [MCP 2026-07-28 changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- Minor: `extensions` field in client/server capabilities; deterministic `tools/list` order (SHOULD); `ttlMs` and
  `cacheScope` required on list/read results (`CacheableResult`, SEP-2549); `inputSchema`/`outputSchema` may use any
  JSON Schema 2020-12 keywords and `structuredContent` may be any JSON value (SEP-2106); resource-not-found error
  -32002 → -32602; error-code range -32020…-32099 reserved for the spec. — [MCP 2026-07-28 changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- Deprecated (minimum 12-month window under the new feature lifecycle policy, SEP-2596): Roots, Sampling, Logging
  (SEP-2577; migrate to tool parameters/resource URIs, direct provider APIs, stderr or OpenTelemetry); HTTP+SSE
  transport; `includeContext` `thisServer`/`allServers`; OAuth Dynamic Client Registration in favour of Client ID
  Metadata Documents. — [MCP 2026-07-28 changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- Release post dated July 28, 2026. — [MCP blog: The 2026-07-28 Specification](https://blog.modelcontextprotocol.io/posts/2026-07-28/)
- Anthropic (July 28, 2026): support "is rolling out across Claude products soon"; Claude already supports MCP Apps
  (interactive UI in conversation); Tasks ships as a versioned extension alongside MCP Apps. — [Claude blog: Bringing MCP 2026-07-28 to Claude](https://claude.com/blog/bringing-mcp-2026-07-28-to-claude)
- Client support (community table, the programmatic copy of the modelcontextprotocol.io clients matrix; columns
  Resources/Prompts/Tools/Discovery/Sampling/Tasks/Roots/Elicitation): **Visual Studio Code** all eight; **Cursor**
  resources, prompts, tools, discovery, roots, elicitation; **Claude Code** resources, prompts, tools, roots;
  **Claude.ai** resources, prompts, tools; **Goose** resources, prompts, tools; **Gemini CLI** prompts, tools; **Zed**
  prompts, tools; **OpenAI Codex** tools, elicitation; **GitHub Copilot CLI** tools only; **Windsurf** tools,
  discovery; **JetBrains AI Assistant** sampling, roots, elicitation; Tasks only VS Code and Glama. — [mcp-client-capabilities 0.0.14 README](https://cdn.jsdelivr.net/npm/mcp-client-capabilities@0.0.14/README.md)
  (community-maintained; the official [modelcontextprotocol.io/clients](https://modelcontextprotocol.io/clients) page
  redirected to the introduction when fetched, so the official matrix could not be read)

### Inferences
- For a CLI's MCP server, structured tool output (`outputSchema` + `structuredContent`) is the highest-value feature:
  it works wherever tools work (every coding assistant in the table), and lets an assistant read `status`/`validate`/`check` results as data
  instead of parsing text.
- Resources (living specs and change files as `spec://<capability>` / `change://<id>/brief.md`) and prompts (e.g.
  "propose a change from this request") reach VS Code/Copilot Chat, Cursor, Claude Code, Goose, but not Copilot CLI or
  Codex; worth it only because they are cheap to add on top of existing file reads.
- Elicitation (now via MRTR) could carry a brief's open questions to the person inside the assistant, but client
  support is thin and the mechanism just changed; Sampling and Roots should not be adopted (deprecated).
- Long model stages fit request-scoped `notifications/progress` today; the Tasks extension is the right later home
  for multi-minute runs but has almost no client support.
- **Adoption note (assistant integration)**: (1) add `outputSchema` and `structuredContent` to the existing tools; (2)
  expose read-only resources for living specs, change files and reports with `ttlMs`; (3) send progress notifications
  per stage during model-calling tools; (4) defer elicitation/tasks until clients catch up; (5) plan the SDK upgrade
  for 2026-07-28 (no `initialize`, `server/discover`, `resultType`), keeping backward compatibility with 2025-11-25
  clients.

### Gaps
- The official client matrix could not be fetched; the community table's date and whether its rows reflect 2026-07-28
  behaviour are unknown (e.g. Claude Code elicitation support may have changed).
- The Python MCP SDK's support status for 2026-07-28 was not checked.

## 7. Agent Skills (agentskills.io) and AGENTS.md: which assistants read which locations

### Takeaway
An Agent Skill is a directory with `SKILL.md` (YAML front matter `name` ≤64 chars matching the directory, `description`
≤1024 chars; optional `license`, `compatibility`, `metadata`, experimental `allowed-tools`), loaded by progressive
disclosure. The spec does not fix a location, but `.agents/skills/` (project and `~`) is the cross-client convention;
GitHub Copilot reads `.github/skills`, `.claude/skills` and `.agents/skills`. AGENTS.md is plain Markdown, nearest file
wins, stewarded by the Agentic AI Foundation (Linux Foundation), and read by Codex, Jules, Gemini CLI, Copilot coding
agent, VS Code, Cursor, Zed and others.

### Cited Findings
- SKILL.md front matter: `name` (required; 1-64 chars; lowercase a-z, 0-9, hyphens; no leading/trailing or consecutive
  hyphens; must match parent directory), `description` (required; 1-1024 chars; what and when), `license`,
  `compatibility` (≤500 chars), `metadata` (string→string map), `allowed-tools` (space-separated, experimental).
  Optional dirs `scripts/`, `references/`, `assets/`; progressive disclosure: metadata ~100 tokens at startup, body
  <5000 tokens recommended on activation, resources on demand; keep SKILL.md under 500 lines and references one level
  deep; validate with `skills-ref validate ./my-skill`. — [Agent Skills specification](https://agentskills.io/specification)
- Client guidance: scan project `<project>/.<client>/skills/` and `<project>/.agents/skills/`, user `~/.<client>/skills/`
  and `~/.agents/skills/`; `.agents/skills/` "has emerged as a widely-adopted convention for cross-client skill
  sharing" though the spec does not mandate locations; some clients also scan `.claude/skills/`; project-level skills
  override user-level; gate project skills on a folder-trust check; lenient validation (warn on name mismatch, skip on
  missing description). — [Agent Skills: How to add skills support to your agent](https://agentskills.io/client-implementation/adding-skills-support)
- GitHub Copilot supports Agent Skills in the Copilot app, Copilot CLI, Copilot cloud agent and code review on
  GitHub.com, and agent mode in VS Code, Visual Studio and JetBrains; project skills in `.github/skills`,
  `.claude/skills`, `.agents/skills`; personal skills in `~/.copilot/skills` or `~/.agents/skills`. — [GitHub Docs: About agent skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)
- As of July 17, 2026, Codex, Cursor, OpenCode, Gemini CLI and Antigravity scan project-level `.agents/skills/`;
  Claude Code does not (it uses `.claude/skills/`). — [yage.ai: Agent Skills harness portability, 2026-07-20](https://yage.ai/share/agent-skills-harness-portability-en-20260720.html)
  (secondary); an open feature request asks Claude Code to support `.agents/skills/` — [claudeissues.com mirror of the request](https://claudeissues.com/issue/16345-feature-request-support-the-standard-agents-skills-directory-for-agent-skills) (secondary)
- AGENTS.md: "a simple, open format for guiding coding agents", standard Markdown with no required fields; nested files
  allowed, the closest AGENTS.md to the edited file wins and explicit user prompts override; "used by over 60k
  open-source projects"; "now stewarded by the Agentic AI Foundation under the Linux Foundation"; listed supporters
  include Codex, Jules, Factory, Aider, goose, opencode, Zed, Warp, VS Code, Devin, Junie, Amp, Cursor, RooCode, Gemini
  CLI, Kilo Code, Semgrep, GitHub Copilot coding agent, Windsurf, Augment Code. — [agents.md](https://agents.md/)

### Inferences
- A tool that writes one skill into `.claude/skills/` reaches Claude Code and Copilot; writing (or also writing) to
  `.agents/skills/` reaches Copilot, Codex, Gemini CLI, Cursor, OpenCode and Antigravity. Claude Code is the one client
  that needs the `.claude/skills/` copy.
- Claude Code is not in the AGENTS.md supporter list (it reads CLAUDE.md), so a short AGENTS.md pointer helps every
  other assistant while CLAUDE.md/`.github/copilot-instructions.md` cover the rest.
- **Adoption note (assistant integration)**: `init` writes the skill to `.agents/skills/<name>/SKILL.md` (cross-client)
  and to `.claude/skills/<name>/` only if that directory is in use; a test runs the spec's constraints (name rules,
  description length, <500 lines) the way `skills-ref validate` does; optionally append a 3-5 line section to an
  existing AGENTS.md naming the commands. Low cost, broad reach.

### Gaps
- Official Claude Code, Codex and Gemini CLI documentation for skill locations was not fetched; their entries rest on
  a secondary article.
- agentskills.io's client showcase page (list of products) was not fetched.

## 8. Supply-chain provenance: SLSA, in-toto, Sigstore, and approvals as attestations

### Takeaway
SLSA v1.2 (approved, announced November 2025) added a Source track whose top level is two-party review and whose
evidence is in-toto attestations (Source Provenance, format left to the source-control system; Source VSA with
predicate `https://slsa.dev/verification_summary/v1`). in-toto has no vetted "human approval" or "code review"
predicate, but custom predicate types are allowed and GitHub's `actions/attest` signs them with Sigstore. An approval
recorded as "file fingerprints + approver + tier" maps cleanly to an in-toto Statement v1 whose subjects are the
approved files and whose predicate is a custom approval record.

### Cited Findings
- SLSA v1.2 release announced on the SLSA blog in November 2025; RC2 asked for comments by November 24, 2025 before
  publication as the approved specification. — [SLSA blog: announce v1.2](https://slsa.dev/blog/2025/11/announce-slsa-v1.2);
  [SLSA blog: v1.2 RC2](https://slsa.dev/blog/2025/11/slsa-v1.2-rc2). Exact day conflicts: Nov 24, 2025 per
  [Socket glossary](https://socket.dev/glossary/supply-chain-levels-for-software-artifacts.md), Nov 12, 2025 per
  [Safeguard blog](https://safeguard.sh/resources/blog/slsa-v1-2-source-track-deep-dive-2025) (both secondary).
- SLSA v1.2 Source track (status Approved): L1 version controlled; L2 history and provenance (the SCS issues Source
  Provenance attestations per revision); L3 continuous technical controls on protected named references; L4 two-party
  review (two trusted persons, uploader + reviewer or two reviewers). Approvals apply to the final revision submitted
  and to a specific context (repository + branch); changes during review must be reviewed; reviewers must see a clear
  representation of what accepting the change would do. — [SLSA v1.2 Source requirements](https://slsa.dev/spec/v1.2/source-requirements)
- Source Provenance format is left to each SCS (which must document it); a "code review attestation" is an example.
  Source VSA: statement `https://in-toto.io/Statement/v1`, predicate `https://slsa.dev/verification_summary/v1`,
  `subject.digest` includes the revision id (e.g. `gitCommit`), `resourceUri` = repository, `verifiedLevels` e.g.
  `SLSA_SOURCE_LEVEL_3`; `ORG_SOURCE_` prefixes for organization-defined properties. — [SLSA v1.2 Source requirements](https://slsa.dev/spec/v1.2/source-requirements)
- in-toto vetted predicates: CycloneDX, link, SLSA provenance, reference, release, runtime-trace, SCAI, SPDX 2/3, SVR
  (Simple Verification Result), test-result, VSA, vulns; none is specifically for code review or human approval. —
  [in-toto attestation predicates](https://github.com/in-toto/attestation/tree/main/spec/predicates)
- GitHub `actions/attest`: `predicate-type` may be a vetted type or a custom URI; exactly one of `subject-path` /
  `subject-digest` / `subject-checksums`; exactly one of `predicate` / `predicate-path` (≤16 MB); signed with a
  Sigstore-issued certificate; verification of non-default predicate types needs `--predicate-type`;
  `attest-build-provenance` is now a wrapper. — [actions/attest](https://github.com/actions/attest);
  [GitHub Docs: use artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)

### Inferences
- The local approval (fingerprints of the change's files, who approved, at which tier, against which check report) is
  structurally an in-toto Statement: `subject` = each approved file with its digest, `predicateType` = a custom URI
  (e.g. `https://<your-domain>/spec-approval/v1`), `predicate` = change id, tier, approver identity, check-report
  digest, timestamp. The test-result predicate fits verify outcomes; SVR/VSA fit "this change passed its gates".
- Signing is what turns the record into evidence: locally a person has no keyless identity outside CI, so the realistic
  path is CI signing with `actions/attest` (Sigstore + OIDC) after merge, or leaving the unsigned Statement JSON in the
  change folder for a later signer.
- SLSA's "approval applies to the final revision" rule matches "any edit voids the approval"; SLSA's two-party L4
  corresponds to a strict tier needing two approvers.
- **Adoption note (auditability)**: write `reports/approval.intoto.json` (unsigned in-toto Statement v1) alongside
  `change.json` at approve time, from data already recorded; document a CI recipe that signs it with `actions/attest
  --predicate-path`. Moderate value for regulated users, low code cost; full Sigstore signing inside the CLI would be a
  large dependency for a small gain and is better deferred.

### Gaps
- The in-toto Statement v1 field layout (`_type`, `subject[].digest` DigestSet algorithms) and the test-result/SCAI
  predicate schemas were not fetched; the `_type` value emitted by `actions/attest` was not confirmed.
- Sigstore `cosign attest-blob` / Rekor details for local, non-CI signing were not researched in this session.
