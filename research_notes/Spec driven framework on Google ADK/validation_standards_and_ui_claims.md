# Validation report: standards, protocols, security guidance, tooling and UI claims

- **Snapshot validated:** frozen copies taken 2026-11-20 23:16 CET (`secondary-snapshot/research_notes/04…`, `05…`, `06…` and `secondary-snapshot/reports/03…`).
- **Date checked:** 2026-11-20, between about 23:20 and 23:55 CET, the same evening as the snapshot.
- **Scope:** external facts only: named standards, protocols, security frameworks, notations, libraries, tools, products, versions, attributions, and how they integrate with Google ADK or each other. Rows in file 04 about OpenSpec, Spec Kit and ADK API internals were left to the other checkers.

## 1. Overall verdict

Every named standard, protocol, package and product exists, and the package versions are accurate to the day. The errors are in what the documents say those things do, and in who they credit.

The five findings that matter most for the design:

1. **SSE reconnect with `Last-Event-ID` is not something the named stack provides.** The AG-UI 1.0 specification rules it out in so many words, and neither `ag-ui-adk` 0.13.0 nor ADK 2.15.0 implements it (claims 24, 25).
2. **"Sharing resets on archive" is the opposite of what Claude Projects does.** Anthropic's help page says archiving does not reset sharing (claim 19).
3. **The SDD "maturity levels" section misstates its source.** The three terms come from one article by Birgitta Böckeler, who places Kiro and Spec Kit at spec-first, not spec-anchored (claims 1, 2).
4. **Plannotator is real but is credited with capabilities its documentation does not describe**: AST-anchored annotations and patch delivery (claim 28).
5. **Several statements read as measured results or industry consensus but have no source**: "~10x capacity" for the project's own search, "near-zero ambiguity", the "Seven Pillars of Context Engineering" (claims 9, 12, 13, 21).

### Reliability per file

59 distinct claims were checked: 33 confirmed, 4 wrong, 12 partly right, 3 outdated and 7 unverifiable. The counts below are per file, so a claim that appears in three files is counted once in each.

| File | Verdict | Confirmed | Wrong | Partly right | Outdated | Unverifiable | Total |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `05-modern-sdd-standards-and-architecture-patterns.md` | Mixed. Reliable on Python, toolchain, OWASP identifiers and ADK class names. Unreliable on the SDD tool landscape (§1 and §2) and on consensus-style assertions. | 18 | 1 | 6 | 2 | 5 | 32 |
| `06-ui-ux-and-page-design-spec.md` | Mostly reliable on what exists. Unreliable on transport resilience, on Plannotator's capabilities and on the Claude archive behaviour. | 11 | 2 | 2 | 0 | 2 | 17 |
| `03-ui-ux-workbench-and-engineering-standards.md` | Reliable on versions. Inherits the transport and Plannotator errors from 06 and the unsourced "~10x" figure from 05. | 22 | 1 | 4 | 0 | 2 | 29 |
| `04-validation-audit-and-improvement-options.md` (in-scope rows) | The version audit (fourth pass) is accurate. The sixth pass and the improvement list contain three wrong statements, and the audit log has no row at all for most of the standards it says it covered (see section 5, item 9). | 23 | 3 | 3 | 1 | 3 | 33 |

### How the checks were done

- **Versions:** live queries to the PyPI JSON API, the npm registry and the GitHub releases API on the check date.
- **ADK, AG-UI and MCP behaviour:** the published wheels for `google-adk` 2.15.0, `ag-ui-adk` 0.13.0, `ag-ui-protocol` 1.0.0, `ag-ui-a2ui-toolkit` 0.0.6, `mcp` 2.3.0 and `mutmut` 3.8.1 were downloaded and read. Nothing was executed.
- **Standards and attributions:** the original article, specification or vendor documentation, fetched directly. Key quotations were confirmed against the page text.

Not checked: the `adk_review` local repository that file 04 cites as evidence, ADK's `constraints-3.14.txt`, and whether every listed package ships a Python 3.14 wheel (sampled only: `google-adk`, `mcp`, `mutmut`, `textual`).

## 2. Claims checked

"Where" gives the file number and section. Verdicts use the five labels requested.

### 2.1 SDD terminology, notations and tools

| # | Where | Claim | Verdict | Evidence | Correction or note |
| --- | --- | --- | --- | --- | --- |
| 1 | 05 §1 | "Industry practice categorizes" SDD into three "maturity levels": Level 1 spec-first, Level 2 spec-anchored, Level 3 spec-as-source | PARTLY RIGHT | https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html | The three terms are real. They were introduced by Birgitta Böckeler (Thoughtworks) on martinfowler.com, 15 October 2025, as "multiple implementation levels" in one author's analysis. The article does not number them, does not use the word "maturity", and defines spec-first as "a well thought-out spec is written first, and then used in the AI-assisted development workflow for the task at hand", with nothing about ad-hoc PRDs or rotting. |
| 2 | 05 §1 | Kiro and GitHub Spec Kit are representative "Level 2: Spec-Anchored" tools | WRONG | https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html | The source of the taxonomy says Kiro "seems to be mostly spec-first" and spec-kit is "what I would call spec-first only, not spec-anchored over time". OpenSpec is not assessed there. The source dates from October 2025; the document cites nothing newer for its placement. |
| 3 | 05 §1; 05 §2 | Tessl is the representative spec-as-source tool, where "specs compile into code" | PARTLY RIGHT | https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html | The source says Tessl "explicitly aspires to a spec-anchored approach, and is even exploring the spec-as-source level", in private beta, with one spec mapped to one file. It was an aspiration, not an established practice. |
| 4 | 05 §2 | Tessl offers "strict guardrail registries", "executable contract tests & continuous drift detection" | OUTDATED | https://docs.tessl.io/ ; https://tessl.io/blog/tessl-launches-spec-driven-framework-and-registry/ | At its September 2025 launch Tessl had a Spec Registry (usage specs for open-source libraries) and a Framework in closed beta whose specs link to tests as "guardrails". There is no "guardrail registry", and drift detection is not mentioned. Tessl's documentation home page today describes "an open platform for managing agentic development" built around a registry of skills and plugins; that page does not mention spec-driven development, the Framework or the Spec Registry. |
| 5 | 05 §2 | Kiro has an IDE spec flow, EARS requirement syntax, steering and hooks | CONFIRMED | https://kiro.dev/docs/specs/feature-specs/ ; https://kiro.dev/docs/hooks/ ; https://kiro.dev/docs/steering/ | The product is branded "Kiro" and comes from AWS; "AWS Kiro" is informal. |
| 6 | 05 §2 | Kiro row: "EARS 5-pattern requirement grammar eliminating ambiguous natural language" | PARTLY RIGHT | https://kiro.dev/docs/specs/feature-specs/ ; https://alistairmavin.com/ears/ | Kiro's documentation shows a single template, `WHEN [condition/event] THE SYSTEM SHALL [expected behavior]`. The five patterns are from EARS itself, not from Kiro. EARS is constrained natural language that reduces ambiguity; neither source says it eliminates it. |
| 7 | 04 §2 item 11 | "AWS Kiro's 5 deterministic EARS sentence patterns" | WRONG | https://alistairmavin.com/ears/ | EARS was developed by Alistair Mavin and colleagues at Rolls-Royce and first published in 2009. Kiro adopted it. |
| 8 | 05 §3 | EARS stands for Easy Approach to Requirements Syntax, with patterns Ubiquitous, Event-driven, State-driven, Optional feature, Unwanted behaviour and the templates shown | CONFIRMED | https://alistairmavin.com/ears/ | Templates match. Mavin's page also lists a sixth, "Complex", which combines keywords. The original uses lower-case "shall"; the capitalised SHALL is the document's RFC 2119 overlay. |
| 9 | 05 §3; 04 §2 item 11 | "Vague prose guarantees LLM drift"; the hybrid grammar "forces every requirement into a deterministic, test-compilable structure"; "near-zero ambiguity and direct test compilation" | UNVERIFIABLE | none found | No source is cited and none was located. Kiro's documentation says each requirement "can be directly translated into test cases"; it does not describe automatic compilation. |
| 10 | 05 §3 | RFC 2119 requirement keywords | CONFIRMED | https://www.rfc-editor.org/rfc/rfc2119.txt | |
| 11 | 05 §2 | BMAD has role personas "PM, Architect, Scrum Master, Dev, QA" | OUTDATED | https://docs.bmad-method.org/reference/skills-and-agents/ ; https://github.com/bmad-code-org/BMAD-METHOD | The current stable release (v6.12) installs six agents: Analyst, Product Manager, Product Owner, Architect, Developer and UX Designer. There is no Scrum Master agent and no dedicated QA agent; test generation is a Developer command and the Test Architect is a separate module. |
| 12 | 05 §5 | "Seven Pillars of Context Engineering" | UNVERIFIABLE | none found | No published seven-pillar framework with these names was located. It appears to be the document's own synthesis, presented as an established model. |
| 13 | 05 §7 | "AI coding agents frequently write shallow, example-only unit tests that mirror implementation bugs" | UNVERIFIABLE | none found | Stated as fact with no source. |

### 2.2 Claude Projects

| # | Where | Claim | Verdict | Evidence | Correction or note |
| --- | --- | --- | --- | --- | --- |
| 14 | 05 §2; 04 §1 sixth pass | Projects switch automatically from in-context knowledge to RAG, expanding capacity "up to ~10x" | CONFIRMED | https://support.claude.com/en/articles/11473015-retrieval-augmented-generation-rag-for-projects | "Claude will automatically enable RAG mode to expand your project's capacity by up to 10x." Paid plans. |
| 15 | 05 §2; 04 §1 sixth pass | The retrieval tool is called `project_knowledge_search` | UNVERIFIABLE | https://support.claude.com/en/articles/11473015-retrieval-augmented-generation-rag-for-projects | Anthropic's documentation says "project knowledge search tool". The literal identifier is not published there. |
| 16 | 05 §2; 04 §1 sixth pass | GitHub integration lets you choose files ("Configure files") and sync manually | CONFIRMED | https://support.claude.com/en/articles/10167454-using-the-github-integration | Sync is user-triggered ("Sync now"). Only file names and contents are synced, not history or pull requests. |
| 17 | 05 §2; 04 §1 sixth pass | Project memory is separate, with a toggle to wall it off from account memory | CONFIRMED | https://support.claude.com/en/articles/9519177-how-can-i-create-and-manage-projects | "Each project has its own memory." The toggle is "Use account memory" on the project page. |
| 18 | 05 §2; 06 §4 page 7; 03 §4; 04 §1 sixth pass | Sharing roles are `Can view` and `Can edit` | CONFIRMED | https://support.claude.com/en/articles/9517075-what-are-projects | Team and Enterprise plans. |
| 19 | 06 §4 page 7; 04 §1 sixth pass; 04 §2 item 24 | "Sharing resets on archive", presented under "Claude Projects Pattern" and sourced to Anthropic's sharing documentation | WRONG | https://support.claude.com/en/articles/9519177-how-can-i-create-and-manage-projects | The page says: "Archiving a project doesn't reset its sharing permissions or remove members. All members, permission levels, and project knowledge are preserved." |
| 20 | 06 §1 principle 6; 04 §1 sixth pass | Chats in a project share knowledge and instructions but not each other's transcripts; the cited help-centre URL exists | CONFIRMED | https://support.claude.com/en/articles/9519177-how-can-i-create-and-manage-projects ; https://support.claude.com/en/articles/9517075-what-are-projects | "Context is not shared across chats within a project unless the information is added into the project knowledge base." With memory on, a per-project memory does carry across chats. |
| 21 | 05 §5 pillar 7; 03 §4; 04 §2 item 22 | The project's own pure-Python BM25 `spec_knowledge_search` gives "~10x capacity" | UNVERIFIABLE | https://support.claude.com/en/articles/11473015-retrieval-augmented-generation-rag-for-projects | "10x" is Anthropic's figure for its own retrieval system. Nothing measures it for an unbuilt BM25 loader. |
| 22 | 04 §2 item 23 | Manual sync matches "Claude Projects' manual GitHub Sync stability guarantee" | PARTLY RIGHT | https://support.claude.com/en/articles/10167454-using-the-github-integration | Sync is manual. Anthropic documents no "stability guarantee". |

### 2.3 Agent-to-UI protocols and the web stack

| # | Where | Claim | Verdict | Evidence | Correction or note |
| --- | --- | --- | --- | --- | --- |
| 23 | 06 title; 06 §2; 03 §1; 04 §2 item 16 | AG-UI is at version 1.0 | CONFIRMED | https://pypi.org/project/ag-ui-protocol/1.0.0/ ; https://docs.ag-ui.com/spec/1.0/basic/transports/http-sse.md | `ag-ui-protocol` 1.0.0 was published 2026-09-17 and declares `PROTOCOL_VERSION = "1.0"`. `@ag-ui/core` is at 1.0.5. A 1.1 working draft exists. |
| 24 | 06 §2; 03 §1; 03 §4; 04 §2 item 21 | "AG-UI 1.0 (SSE + Last-Event-ID Reconnect)"; `Last-Event-ID` cursor replay as part of the backend stack | WRONG | https://docs.ag-ui.com/spec/1.0/basic/transports/http-sse.md ; https://pypi.org/project/ag-ui-adk/0.13.0/ ; https://pypi.org/project/google-adk/2.15.0/ | The AG-UI 1.0 HTTP+SSE binding states: "The binding has no stream resumption: SSE's `Last-Event-ID` mechanism is not used, and a broken stream cannot be re-entered." Runs are started with POST, and consumers must ignore the `id:` field. `ag-ui-adk` emits `data:` frames with no `id:` (`ag_ui_adk/endpoint.py`). The string `Last-Event-ID` does not occur in the ADK 2.15.0 wheel. What `ag-ui-adk` does offer is re-sync by snapshot: an `/agents/state` endpoint and an optional `MessagesSnapshotEvent`. |
| 25 | 06 §2 | "Every streamed ADK event carries `event_id` (monotonic sequence), `run_id`, `invocation_id`, `node_id`, and `timestamp`" | PARTLY RIGHT | https://pypi.org/project/google-adk/2.15.0/ ; https://pypi.org/project/ag-ui-protocol/1.0.0/ | An ADK `Event` has `id` (a UUID, not a sequence), `invocation_id`, `timestamp` and `node_info.path`, from which a run id is derived (`google/adk/events/event.py`). An AG-UI event has `type`, `timestamp` and `rawEvent`; run events add `runId` and `threadId`. Neither carries a monotonic sequence number. |
| 26 | 06 §2; 03 §1; 04 §1 fourth pass | `ag_ui_adk` provides `ADKAgent`; `ag-ui-adk` 0.13.0 pairs `google-adk<3` with `ag-ui-a2ui-toolkit>=0.0.6` | CONFIRMED | https://pypi.org/project/ag-ui-adk/0.13.0/ ; https://adk.dev/integrations/copilotkit/ | It is a separate middleware from the AG-UI project, not part of ADK: the ADK wheel contains no AG-UI code. It also exports `add_adk_fastapi_endpoint`, and supports ADK `ResumabilityConfig` interrupts through AG-UI `resume` entries. |
| 27 | 06 §2; 04 §2 item 16 | A2UI: agents emit declarative JSON mapped to vetted host components, with no arbitrary code execution | CONFIRMED | https://a2ui.org/ ; https://developers.googleblog.com/en/a2ui-10-build-delightful-fast-reliable-agentic-experiences/ | "Streams declarative JSON data with two-way bindings — never executable code"; "Agents place only components you registered." Google announced A2UI 1.0 as the first stable version on 2026-11-11, nine days before the snapshot. |
| 28 | 06 §1 principle 2; 06 §4 pages 2 and 3; 03 §1; 03 §3; 04 §2 item 21 | Plannotator provides "AST/line-range anchored" inline annotations, including on Mermaid blocks, "delivered as AST/line-range patches", and is a component of the web workbench stack | PARTLY RIGHT | https://github.com/backnotprop/plannotator ; https://registry.npmjs.org/@plannotator%2Fui | Plannotator exists: a local, browser-based review surface for coding agents (Claude Code, Codex, Gemini CLI, OpenCode and others), dual-licensed Apache 2.0 or MIT. Its documentation describes annotating rendered blocks, text selections and diff lines, with "structured feedback sent to agent" as text. It does not describe AST anchoring, patch delivery or Mermaid annotation. An installable `@plannotator/ui` (0.63.0, needs React ^19.2.3 and Tailwind ^4.1.18) does exist, but its README says it is published so the vendor's own commercial app can reuse it. |
| 29 | 03 §1 item 1 | A2UI surfaces in the web workbench come from `ag-ui-a2ui-toolkit` | PARTLY RIGHT | https://pypi.org/project/ag-ui-a2ui-toolkit/0.0.6/ ; https://pypi.org/project/ag-ui-adk/0.13.0/ | The package is real but is an agent-side helper ("op builders, prompt assembly, history walkers") at version 0.0.6, not a browser renderer. Rendering is done by packages such as `@a2ui/react` or `@copilotkit/a2ui-renderer`. The `ag-ui-adk` source notes that native A2UI 1.0 validation lives in the middleware "until the published toolkit supports that protocol". |
| 30 | 03 §1 item 1; 04 §1 fourth pass | Frontend versions: `react` 19.3.1, `next` 16.4.6, `typescript` 7.0.2, `@xyflow/react` 13.0.2, `@copilotkit/react-core` 1.90.0, `@ag-ui/core` 1.0.5, `tailwindcss` 4.3.5 | CONFIRMED | https://registry.npmjs.org/@xyflow%2Freact ; https://registry.npmjs.org/@copilotkit%2Freact-core ; https://registry.npmjs.org/typescript | All are the `latest` tag on the check date. `@xyflow/react` 13.0.0 was published 2026-11-16, four days before the snapshot. CopilotKit 2.0.0 is at release candidate 68. |
| 31 | 06 §5; 03 §4 | WCAG 2.2 level AA | CONFIRMED | https://www.w3.org/TR/WCAG22/ | W3C Recommendation. |
| 32 | 06 §1 principle 2; 03 §3 | Bare approve/reject prompts invite rubber-stamping ("approval fatigue") | CONFIRMED | https://www.anthropic.com/engineering/claude-code-auto-mode ; https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/ | Anthropic (25 March 2026): "in practice users accept 93% of them anyway", leading to "approval fatigue". OWASP lists the related risk as ASI09, Human-Agent Trust Exploitation. The documents cite neither. |
| 33 | 06 §1 principle 2; 03 §3 | Side-by-side diffs plus three-way controls with defensive button ordering counter approval fatigue | UNVERIFIABLE | none found | No evidence is cited that this layout reduces rubber-stamping. Anthropic's own response to the 93% figure was to reduce the number of prompts, not to redesign them. |
| 34 | 06 §1 principle 3; 03 §3 | OpenSpec's `reviewing-changes.md` recommends reading proposal, then spec deltas, then design, then tasks, to quit earliest | CONFIRMED | https://github.com/Fission-AI/OpenSpec/blob/main/docs/reviewing-changes.md | "Read the files in the order that lets you quit earliest if something's wrong." OpenSpec says design is read only for larger changes; "& Contracts" is the document's addition. |
| 35 | 06 §4 page 1 | Wireframe figures such as "Token Savings: -41% vs Phase1" and "Spec Test Cov: 84%" | UNVERIFIABLE | none | Placeholder data in a mock-up. Not measurements, and should not be quoted as results. |

### 2.4 ADK integration with protocols and services

| # | Where | Claim | Verdict | Evidence | Correction or note |
| --- | --- | --- | --- | --- | --- |
| 36 | 06 §2; 03 §1 | `get_fast_api_app(agents_dir=..., web=False)`; the `adk web` developer UI; `adk web --no_use_local_storage`; `.adk/session.db` | CONFIRMED | https://pypi.org/project/google-adk/2.15.0/ | Wheel: `google/adk/cli/fast_api.py`, `cli/cli_tools_click.py`, `cli/utils/dot_adk_folder.py`. `web` is a required keyword argument. |
| 37 | 06 §2; 03 §1 item 5; 04 §1 fourth pass | ADK exposes agents over MCP with `to_mcp_server`; `mcp` 2.3.0 uses `MCPServer` | CONFIRMED | https://pypi.org/project/google-adk/2.15.0/ ; https://pypi.org/project/mcp/2.3.0/ | Wheel: `google/adk/tools/mcp_tool/_agent_to_mcp.py`. In `mcp` 2.x `FastMCP` was renamed `MCPServer`. ADK's `mcp` extra allows `mcp<3,>=1.24`. |
| 38 | 03 §1 item 5; 04 §2 item 20 | `to_a2a` and `RemoteA2aAgent` serve agents over A2A JSON-RPC with `a2a-sdk` 1.3.1 | CONFIRMED | https://pypi.org/project/google-adk/2.15.0/ ; https://a2a-protocol.org/latest/specification/ | Wheel: `google/adk/a2a/utils/agent_to_a2a.py`. ADK's `a2a` extra allows `a2a-sdk<2,>=0.3.4`. |
| 39 | 05 §8; 03 §4; 04 §2 item 17 | ADK ships `ModelArmorPlugin` with an `after_tool_callback`, and `E2BEnvironment` and `DaytonaEnvironment` sandboxes | CONFIRMED | https://pypi.org/project/google-adk/2.15.0/ | Wheel: `google/adk/integrations/model_armor/_plugin.py`, `integrations/e2b/`, `integrations/daytona/`. |
| 40 | 06 §1 principle 5; 06 §4 page 9; 03 §2 | `ResumabilityConfig`, `Runner.rewind_async`, the `token_usage_v1`, `inference_call_count_v1` and `invocation_duration_v1` metrics, and `TelemetryConfig` with `NO_CONTENT` exist | CONFIRMED | https://pypi.org/project/google-adk/2.15.0/ | Existence only. Behaviour is for the ADK checker. |

### 2.5 OWASP

| # | Where | Claim | Verdict | Evidence | Correction or note |
| --- | --- | --- | --- | --- | --- |
| 41 | 05 §8 | "OWASP Top 10 for Agentic Applications (2025–2026)" | PARTLY RIGHT | https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/ | The official title is "OWASP Top 10 for Agentic Applications for 2026", released 9 December 2025. |
| 42 | 05 §8; 03 §4; 04 §2 item 17 | ASI01 Agent Goal Hijack, ASI02 Tool Misuse & Exploitation, ASI05 Unexpected Code Execution (RCE), ASI06 Memory & Context Poisoning | CONFIRMED | https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/ | Identifiers and risk names match OWASP's own listing, which uses the short forms "Tool Misuse" and "Unexpected Code Execution". The longer forms match secondary coverage of the PDF, which was not opened. The documents address four of the ten risks (see section 4, item 10). |

### 2.6 Python, packaging and toolchain

| # | Where | Claim | Verdict | Evidence | Correction or note |
| --- | --- | --- | --- | --- | --- |
| 43 | 04 §1 fourth pass | Python runtime "Live Verified Latest" is 3.14.10 | OUTDATED | https://docs.python.org/3.15/whatsnew/3.15.html | 3.14.10 is the newest 3.14 release. The newest stable Python is 3.15.2; 3.15.0 was released 9 October 2026. `google-adk` 2.15.0 and `mutmut` 3.8.1 already carry a 3.15 classifier. |
| 44 | 05 §9; 03 §1; 04 §1 fourth pass | `google-adk` 2.15.0 is current, supports Python 3.14, and bounds `google-genai>=2.34,<3`, `pydantic>=2.12,<3`, `fastapi>=0.133,<1`, `sqlalchemy>=2,<3`; `google-genai` latest is 3.6.1 | CONFIRMED | https://pypi.org/project/google-adk/2.15.0/ ; https://pypi.org/project/google-genai/ | 2.15.0 was published on the snapshot day, 2026-11-20. |
| 45 | 03 §1; 04 §1 fourth pass | `pydantic` 2.14.4, `fastapi` 0.165.0, `uvicorn` 0.54.0, `pyyaml` 6.0.3, `aiosqlite` 0.22.1, `sqlalchemy` 2.1.9, `mcp` 2.3.0, `a2a-sdk` 1.3.1, `ag-ui-protocol` 1.0.0, `typer` 0.29.2, `rich` 15.0.0, `textual` 8.2.8 | CONFIRMED | https://pypi.org/pypi/pydantic/json ; https://pypi.org/pypi/fastapi/json ; https://pypi.org/pypi/textual/json | Each is the latest release on PyPI on the check date. |
| 46 | 05 §6.4 item 8; 03 §4; 04 §1 fourth pass | `pytest` 9.2.0, `pytest-asyncio` 1.5.0, `hypothesis` 6.170.17, `mutmut` 3.8.1, `import-linter` 2.17, `ruff` 0.17.6, `mypy` 2.4.1, `ty` 0.0.107, `pyright` 1.1.414, `pyrefly` 1.5.0 | CONFIRMED | https://pypi.org/pypi/ruff/json ; https://pypi.org/pypi/hypothesis/json ; https://pypi.org/pypi/pyrefly/json | Each is the latest release. |
| 47 | 05 §6.4 item 1; 03 §4; 04 §1 fourth pass | uv accepts `exclude-newer = "P3D"` and `required-version`; `uv` 0.13.9, `hatchling` 1.33.0, `truststore` 0.10.5, `python-dotenv` 1.2.4 | CONFIRMED | https://docs.astral.sh/uv/reference/settings/ | uv accepts "an ISO 8601 duration (e.g., `PT24H`, `P7D`, `P30D`)". See section 5, item 1, for a conflict with the pins. |
| 48 | 03 §4; 04 §1 fourth pass | `litellm` 1.110.2 is the verified version for the stack that runs on `google-adk` 2.15.0 | PARTLY RIGHT | https://pypi.org/project/google-adk/2.15.0/ ; https://pypi.org/pypi/litellm/json | 1.110.2 is the latest release. But every `google-adk` 2.15.0 extra that includes LiteLLM declares `litellm<1.106.3,>=1.84`. `google-adk[extensions]` cannot be installed with 1.110.2, and installing them separately puts LiteLLM outside the range ADK declares. The audit caught the equivalent `google-genai<3` bound but not this one. |
| 49 | 05 §6.4 items 2 and 3; 03 §4; 04 §1 fourth pass | Python 3.14 has native deferred annotations (PEP 649 and 749, `annotationlib`) and template strings (PEP 750, `string.templatelib.Template`) | CONFIRMED | https://peps.python.org/pep-0749/ ; https://peps.python.org/pep-0750/ | |
| 50 | 03 §1 item 4 | "PEP 750 ANSI control-char sanitization" | PARTLY RIGHT | https://peps.python.org/pep-0750/ | PEP 750 separates literal text from interpolated values. It does no sanitising; the escaping function has to be written. File 05 §6.4 item 3 describes this correctly. |
| 51 | 05 §6.4 item 4; 05 §9 item 3; 03 §4 | Ruff rule `S607` flags starting a process with a partial executable path | CONFIRMED | https://docs.astral.sh/ruff/rules/start-process-with-partial-path/ | |
| 52 | 05 §6.4 item 8; 03 §4; 04 §1 fourth pass | Pyrefly has an error kind `direct-abstract-base-instantiation` | CONFIRMED | https://pyrefly.org/en/docs/error-kinds/ | Default severity is `warn`. |
| 53 | 05 §7; 04 §2 item 18 | Hypothesis offers `@given` and `RuleBasedStateMachine`; `import-linter` enforces layer and forbidden-import contracts | CONFIRMED | https://hypothesis.readthedocs.io/en/latest/stateful.html ; https://import-linter.readthedocs.io/en/stable/contract_types.html | |
| 54 | 05 §9 item 5; 03 §4; 04 §1 fifth pass | `mutmut` 3.8.1 needs `os.fork()` and has no native Windows support (issue 397); `cosmic-ray` 8.9.0 is the Windows alternative | CONFIRMED | https://pypi.org/project/mutmut/3.8.1/ ; https://github.com/boxed/mutmut/issues/397 ; https://github.com/sixty-north/cosmic-ray | mutmut README: "Mutmut must be run on a system with `fork` support." For `cosmic-ray`, Windows support rests on the README's Windows badge only. |
| 55 | 03 §4; 04 §1 fifth pass | LiteLLM has a `github_copilot/` provider and a `litellm.disable_copilot_system_to_assistant` flag | CONFIRMED | https://docs.litellm.ai/docs/providers/github_copilot ; https://github.com/BerriAI/litellm/blob/main/litellm/__init__.py | The flag defaults to `False`. The other Copilot settings in that row come from the local `adk_review` repository and were not checked. |
| 56 | 05 §9 item 4 | "Windows consoles default to legacy codepages like `cp1252`" | PARTLY RIGHT | https://docs.python.org/3.14/library/sys.html ; https://docs.python.org/3.15/whatsnew/3.15.html | Python on Windows uses UTF-8 for the console device. The legacy code page applies to pipes and redirected files. From Python 3.15, UTF-8 is the default encoding everywhere (PEP 686). |
| 57 | 05 §9 item 3 | "Windows searches the current working directory first" | PARTLY RIGHT | https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw | `CreateProcess` searches the directory of the calling application first and the current directory second. The security point stands. |
| 58 | 05 §9 items 1, 2 and 4 | Git settings `core.autocrlf`, `core.fsmonitor`, `core.precomposeUnicode`, `core.attributesFile`; `os.path.isjunction()`; `TemporaryDirectory(ignore_cleanup_errors=True)` | CONFIRMED | https://git-scm.com/docs/git-config ; https://docs.python.org/3.14/library/os.path.html ; https://docs.python.org/3.14/library/tempfile.html | |
| 59 | 04 §1 fourth pass | `@fission-ai/openspec` 2.1.1 and `spec-kit` v1.4.3 are the latest releases | CONFIRMED | https://registry.npmjs.org/@fission-ai%2Fopenspec ; https://github.com/github/spec-kit/releases | Published 2026-11-19 in both cases. |

## 3. Named things that do not exist or are materially misdescribed

No named standard, protocol, package or product is invented; each was found. One named framework, the "Seven Pillars of Context Engineering", could not be traced to any external source. The following are misdescribed:

| Thing | How the documents describe it | What the source says |
| --- | --- | --- |
| AG-UI 1.0 | An SSE transport with `Last-Event-ID` reconnect and cursor replay | The 1.0 specification has a section titled "No resumption". A dropped stream cannot be re-entered; a re-run is a new run. |
| Claude Projects | Sharing "resets on archive" | Archiving preserves members and permission levels. |
| SDD "maturity levels" | An industry classification with numbered levels, placing Kiro and Spec Kit at spec-anchored | One author's "implementation levels" (Böckeler, October 2025), unnumbered, with Kiro and Spec Kit placed at spec-first. |
| EARS | "AWS Kiro's" sentence patterns (file 04) | Alistair Mavin and colleagues, Rolls-Royce, 2009. Kiro uses it. |
| Plannotator | AST-anchored annotations delivered as patches; a workbench library | A review surface for coding agents that returns structured text feedback. AST anchoring and patches are not documented. |
| Tessl | "Strict guardrail registries" with drift detection | No such concept. The 2025 Spec Registry held library usage specs; today's product is a skills and plugins platform. |
| BMAD | Personas including Scrum Master and QA | The current roster has neither. |
| `ag-ui-a2ui-toolkit` | The A2UI surface layer of the React workbench | An agent-side helper library at version 0.0.6. |
| PEP 750 | Provides ANSI control-character sanitisation (file 03) | Provides template structure only. |
| OWASP Agentic Top 10 | "(2025–2026)" | "for 2026", released December 2025. |
| "Seven Pillars of Context Engineering" | Presented as an established framework | No external source found. |
| `project_knowledge_search` | The name of Claude's retrieval tool | Anthropic's documentation says "project knowledge search tool" and publishes no identifier. |
| "Latest" Python | 3.14.10 | 3.15.2. |

## 4. Design recommendations that rest on a wrong or unverifiable claim

1. **SSE auto-reconnect with `Last-Event-ID` replay** (06 §2; 03 §1 and §4 "Accessibility & Transport UX"; 04 item 21). Depends on claim 24. Neither AG-UI 1.0, `ag-ui-adk` nor ADK provides cursor resumption, so this is unbuilt custom server work, not a property of the chosen stack. The same applies to the "no duplicate graph renders" behaviour that relies on it.
2. **Typed SSE envelopes with a monotonic `event_id`** (06 §2). Depends on claim 25. Neither ADK events nor AG-UI events carry a sequence number.
3. **Plannotator-based inline review with AST-anchored patches** (06 principle 2, pages 2 and 3; 03 §1 and §3; 04 item 21). Depends on claim 28. The anchoring and patch format are not Plannotator features, and the installable UI package is published for the vendor's own product.
4. **Workbench roles that reset sharing on archive, labelled as the Claude Projects pattern** (06 page 7; 04 sixth pass and item 24). Depends on claim 19. If the reset is wanted, it is the project's own design choice, not an adopted pattern.
5. **Positioning as "Level 2+ (Spec-Anchored with Selective Level 3 Compilation)"** (05 §1). Depends on claims 1 to 3. The source does not present a ladder in which a higher level is better. Its author compares spec-as-source to model-driven development and asks whether it "might end up with the downsides of both MDD and LLMs".
6. **Benchmarking against Kiro and Spec Kit as spec-anchored peers, and against Tessl's "guardrail registries" and "continuous drift detection"** (05 §2 "Key Pattern Worth Adopting"). Depends on claims 2 and 4.
7. **Mapping BMAD's role roster onto ADK agent modes** (05 §2). Depends on claim 11, an outdated roster.
8. **The two-tier knowledge loader justified by "~10x capacity"** (05 §5 pillar 7; 03 §4; 04 item 22). Depends on claim 21. The figure belongs to a different system.
9. **The EARS hybrid grammar as a route to "near-zero ambiguity and direct test compilation", and property tests "derived from EARS invariants"** (05 §3 and §7; 04 items 11 and 18). Depends on claim 9. EARS is a writing discipline; nothing verified here shows mechanical compilation to tests.
10. **A security posture covering only ASI01, ASI02, ASI05 and ASI06** (05 §8; 03 §4; 04 item 17). Depends on a partial reading of the OWASP list (claim 42). The same documents add A2A federation (ASI07, Insecure Inter-Agent Communication), third-party skills and MCP servers (ASI04, Agentic Supply Chain Vulnerabilities), stored Copilot OAuth tokens (ASI03, Identity & Privilege Abuse) and a human approval gate (ASI09, Human-Agent Trust Exploitation), none of which is mapped.
11. **Three-way review controls as the remedy for approval fatigue** (06 principle 2; 03 §3). Depends on claim 33. The problem is documented; the effectiveness of this remedy is not.
12. **`requires-python = ">=3.14,<3.15"` presented alongside "latest library compatibility"** (05 §6.4; 03 §4; 04 fourth pass). Depends on claim 43. The cap excludes the current stable Python.
13. **The Copilot arm on `litellm` 1.110.2 with `google-adk` 2.15.0** (03 §4; 04 fourth and fifth pass). Depends on claim 48, an unverified compatibility.
14. **A2UI surfaces delivered through `ag-ui-a2ui-toolkit`** (03 §1). Depends on claim 29. The toolkit is a 0.0.x agent-side helper that, per the `ag-ui-adk` source, does not yet support A2UI 1.0 natively.

## 5. Internal contradictions

1. **Dependency cooldown against the pins** (05 §6.4 items 1 and 8; 03 §4; 04 fourth pass). The files require `exclude-newer = "P3D"` and also pin `ruff==0.17.6` (uploaded 2026-11-19), `pyrefly==1.5.0` (2026-11-19), `import-linter>=2.17` (2026-11-18) and `hypothesis>=6.170.17` (2026-11-20), on top of `google-adk` 2.15.0 (2026-11-20), `pydantic` 2.14.4 (2026-11-19) and `fastapi` 0.165.0 (2026-11-18). By uv's documented behaviour a three-day cooldown excludes all of these on the snapshot date. This was inferred from the documentation, not run, and it clears itself by 2026-11-23.
2. **Rich or Textual, and where the TUI lives.** 06 §2 and §5 and 04 item 16 describe a "Rich TUI" invoked as `adk-spec view`. 03 §1 item 4 describes a Textual application, `adk-spec-tui`, in a separate workspace member so that headless installs carry no UI dependencies. A `view` subcommand on the main CLI would defeat that isolation.
3. **Reject is named but absent.** 06 principle 2 says to position "Reject / Revise" before Approve. The action bar it specifies (06 page 3, 03 §3) has Revise, Edit and Approve only.
4. **Session tab names.** 06 principle 6 and 04 item 23 use `explore`, `assess`, `change`. 06 page 2 uses `explore`, `clarify`, `change`.
5. **Overview KPIs.** 06 page 1 lists five KPIs including Draft Changes and Completed Changes. Its own wireframe shows neither and adds "Python Offload" instead.
6. **Dependency-graph chips.** 06 page 1 defines four states including `·` for blocked. 03 §2 lists three and drops blocked.
7. **Breakpoints.** 06 §6 and 03 §3 define layouts for 1440 px and above, 1024 to 1439 px, and below 768 px. Widths from 768 to 1023 px have no layout.
8. **EARS attribution.** 05 §3 presents EARS as an independent notation. 04 item 11 calls it "AWS Kiro's".
9. **What the audit says it covered.** 04's opening sentence says the six-pass audit covered "modern SDD/security/UI standards". Its six tables have no row for the AG-UI specification, A2UI, OWASP, EARS, Plannotator, WCAG, the SDD levels, BMAD, Tessl or Kiro. Of the four claims found wrong in this report, only the Claude archive statement appears in the audit log (sixth pass); the other three were never audited.
10. **PEP 750.** 05 §6.4 item 3 describes t-strings correctly as separating literals from interpolations. 03 §1 item 4 turns that into "PEP 750 ANSI control-char sanitization".

## 6. Observation on freshness

Several baselines the documents treat as settled were days old at the snapshot: `google-adk` 2.15.0 (same day), `@xyflow/react` 13 (four days, three releases in two days), A2UI 1.0 (nine days), `ag-ui-adk` 0.13.0 (eight days) and `ag-ui-a2ui-toolkit` at 0.0.6. The version numbers are right; the documents do not flag how new they are.
