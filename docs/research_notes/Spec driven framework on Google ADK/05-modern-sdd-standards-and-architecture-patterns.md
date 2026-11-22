# Modern SDD Standards, Context Engineering, Security & Software Architecture Patterns (2025–2026)

This research note synthesizes modern Spec-Driven Development (SDD) methodologies, executable specification standards, context-engineering patterns, anti-tautological verification, OWASP agentic security defenses, and Python software architecture patterns that shape `adk-spec`.

---

## 1. The SDD Maturity Spectrum (2025–2026)

Industry practice categorizes Spec-Driven Development into three distinct maturity levels:

| Level | Paradigm | Characteristics | Representative Tools |
| --- | --- | --- | --- |
| **Level 1: Spec-First** | Prompt + ad-hoc PRD | Spec written once to kick off coding; rots immediately after implementation | Ad-hoc `SPEC.md` in Cursor / Claude Code |
| **Level 2: Spec-Anchored** | Living repo specs synced with code | Versioned specifications + plans + tasks stay alongside code and evolve across PRs | **OpenSpec**, **GitHub Spec Kit**, **AWS Kiro** |
| **Level 3: Spec-As-Source** | Specs compile into code | Humans maintain structured capability specs & invariants; generated code is treated as disposable output | **Tessl** |

**Target positioning for `adk-spec`:** **Level 2+ (Spec-Anchored with Selective Level 3 Compilation)**—maintaining living canonical `.spec/specs/` synchronized via fingerprint-guarded deltas, while deterministically compiling/scaffolding contracts, property-test stubs, schemas, and traceability reports straight from structured specs.

---

## 2. Broader SDD Tooling Benchmark

| Framework / Tool | Signature Strength | Key Pattern Worth Adopting in `adk-spec` |
| --- | --- | --- |
| **OpenSpec** | Living `specs/` + isolated `changes/` deltas + `skip_specs: true` | Brownfield delta model, declaration-ordered DAG, `REMOVED` `git log` verification |
| **GitHub Spec Kit** | `constitution.md` + `clarify`/`analyze`/`converge` + `overlays` + `assess`/`bug` | Strict gate write contracts, `T### [P] [US#]` slicing, `contracts/` & `roadmap.md` |
| **AWS Kiro** | Tight IDE spec flow + **EARS** requirement syntax + steering & lifecycle hooks | EARS 5-pattern requirement grammar eliminating ambiguous natural language |
| **BMAD** | Role-based agile multi-agent personas (PM, Architect, Scrum Master, Dev, QA) | Clean separation of specialist agent roles (maps naturally to ADK `LlmAgent` modes) |
| **Tessl** | Spec-as-source + strict guardrail registries | Executable contract tests & continuous drift detection linking code back to specs |
| **Claude Projects** | Persistent workspace bundling Knowledge Base + Instructions + isolated threads, automatic Direct→RAG (`project_knowledge_search`) up to ~10x capacity, selective manual GitHub file sync, memory isolation toggle, Artifacts & `Can view`/`Can edit` sharing | `.spec/knowledge/` pack, 2-tier Direct Cache → pure-Python BM25 `spec_knowledge_search`, pinned manual `adk-spec knowledge sync`, `isolated_memory` wall, and human-gated `[↑ Promote to Knowledge]` |

---

## 3. Unified Specification Grammar: EARS + RFC 2119 + 4-Hash BDD

Vague prose (*"Login should be fast and secure"*) guarantees LLM drift. Combining **EARS (Easy Approach to Requirements Syntax)** with OpenSpec's **RFC 2119** + **`#### Scenario:`** grammar forces every requirement into a deterministic, test-compilable structure (`<= 500` chars per requirement):

| EARS Pattern | Template | Concrete Example (`adk-spec` Format) |
| --- | --- | --- |
| **Ubiquitous** | *The `<system>` SHALL `<response>`.* | `The system SHALL persist all approved spec changes in an immutable timestamped archive.` |
| **Event-Driven** | *WHEN `<trigger>`, the `<system>` SHALL `<response>`.* | `WHEN a user submits valid credentials, the AuthService SHALL issue a signed JWT expiring in 900s.` |
| **State-Driven** | *WHILE `<in state>`, the `<system>` SHALL `<response>`.* | `WHILE a change is in analyze mode, the WritePolicyPlugin SHALL deny all file mutations.` |
| **Optional Feature** | *WHERE `<feature enabled>`, the `<system>` SHALL `<response>`.* | `WHERE ceremony profile is strict, the Workflow SHALL require a checked reviewer checklist before apply.` |
| **Unwanted Behavior** | *IF `<condition>`, THEN the `<system>` SHALL `<mitigation>`.* | `IF base requirement SHA-256 diverges from live specs/, THEN DeltaMerger SHALL abort archive and emit diff3 markers.` |

Paired directly underneath with OpenSpec's 4-hash scenario block:

```markdown
### Requirement: Stale Base Conflict Guard [REQ-MERGE-001]
IF a base requirement SHA-256 fingerprint diverges from live `.spec/specs/`,
THEN the archive engine SHALL abort the merge and emit 3-way conflict markers.

#### Scenario: Concurrent change modifies an already-archived requirement
- **GIVEN** Change A and Change B both branched from Auth v1
- **WHEN** Change A archives first and Change B attempts to archive second
- **THEN** the archive halts with diagnostic code `stale_base_conflict`
- **AND** Change A's scenarios remain untouched in `.spec/specs/auth/spec.md`
```

---

## 4. Executable Specifications & Bidirectional Traceability

A spec is only trustworthy when verified continuously by code and tests:

```text
Roadmap Entry (R1) ──▶ Requirement (REQ-AUTH-001) ──▶ Scenarios (#### Scenario:)
                                │                             │
                                ▼                             ▼
                       contracts/ (OpenAPI/Pydantic)    Tasks (T012 [P] [US1])
                                │                             │
                                └──────────┬──────────────────┘
                                           ▼
                      @pytest.mark.spec("auth:REQ-AUTH-001") / Hypothesis PBT / Contract Tests
                                           │
                                           ▼
                      CI Traceability & Mutation Gate (Spec Coverage % & Drift Detection)
```

- **Deterministic coverage scoring:** A lightweight Python AST/marker scanner collects `@pytest.mark.spec("<cap>:<REQ-ID>")` decorators (and OpenAPI contract test links) across `tests/` so `analyze` and `verify_converge` know *mechanically*—with zero LLM tokens—which requirements lack passing tests.

---

## 5. Seven Pillars of Context Engineering Mapped to Google ADK 2.0

| Context Engineering Pillar | Why It Matters in SDD | Native ADK 2.0 / `adk-spec` Mechanism |
| --- | --- | --- |
| **1. Progressive Disclosure** | Loading every rubric, template, and checklist upfront wastes tokens and degrades attention | `SkillToolset` (`load_skills_from_dir`) exposes metadata first, loading `SKILL.md` & `references/` on demand |
| **2. Context Isolation** | Multi-turn brainstorming pollutes strict auditing and code generation; parallel threads cross-contaminate | `LlmAgent(mode="single_turn")` & `mode="task"` (`include_contents="none"`); transcript-isolated parallel project threads sharing only Project Knowledge |
| **3. Immutable Prefix Caching** | Repeatedly re-sending `constitution.md` and canonical `specs/` spikes cost | `LlmAgent.static_instruction` + `ContextCacheConfig` on `App` (Gemini arm) reuses cached prefixes cleanly |
| **4. Non-Destructive Compaction** | Long SDD sessions hit context limits if full diffs stay in active window | `EventsCompactionConfig` summarizes older turns into `EventCompaction` while preserving full `Session.events` |
| **5. Out-of-Band Heavy Payloads** | Large diffs, `analyze` reports, and logs bloat tool-response history | `ArtifactService` (`ctx.save_artifact`) stores versioned blobs out-of-band, returning small `{filename, version}` refs |
| **6. Cross-Session Semantic Recall & Isolation** | Fresh change sessions forget why past architectures were rejected—yet client/regulated repos need isolation | `BaseMemoryService` (`add_session_to_memory`, `load_memory`) partitioned by `(app_name, project_id)` with `isolated_memory` toggle (default `true` in `strict`) & human-gated ingestion (`ASI06`) |
| **7. Auto-Scaling Hybrid Retrieval & Pinned Selective Sync (Claude Projects Pattern)** | Large multi-module repos or tighter GitHub Copilot context windows overflow naive full-context injection; blind auto-sync shifts context mid-session | **2-Tier Knowledge Loader (`domain/knowledge_index.py`):** Tier 1 injects small packs directly into `static_instruction`; above budget, Tier 2 flips automatically to compact ToC + deterministic pure-Python BM25/heading `spec_knowledge_search` (~10x capacity, zero vector DB initially; optional semantic hybrid in Phase 4). Driven by a selective `knowledge:` allowlist (`1 MiB` file cap) and pinned manual `adk-spec knowledge sync` snapshots |

- **Positive Structural Context Hygiene (Claude Projects Prompt Lesson):** Prefer structured, modular `.spec/knowledge/` files (clean headings, unambiguous domain terms, non-bloated selections without lockfiles/build outputs) and affirmative architectural guidance over long lists of *"NEVER do X"* prompt prohibitions—delegating hard bans mechanically to `WritePolicyPlugin` and `tool_filter`.

---

## 6. Software Architecture & Python Coding Structure Patterns

### 6.1 Hexagonal Architecture (Ports & Adapters)

Never couple pure SDD parsing, delta merging, or graph rules to Google ADK or LLM SDK classes. Structure `adk_spec/` strictly in concentric layers (with terminal UI isolated in a sibling `tui/` `uv` workspace member):

```text
           ┌────────────────────────────────────────────────────────┐
           │     Interfaces (cli.py, tui, fast_api/AG-UI, mcp)      │
           └───────────────────────────┬────────────────────────────┘
                                       ▼
           ┌────────────────────────────────────────────────────────┐
           │   Orchestration (ADK Workflow, App, Plugins, Runner)   │
           └──────────┬──────────────────────────────────┬──────────┘
                      ▼                                  ▼
     ┌────────────────────────────────┐ ┌────────────────────────────────┐
     │   Adapters: LLM (`LlmAgent`)   │ │   Adapters: Python (`@node`)   │
     └────────────────┬───────────────┘ └────────────────┬───────────────┘
                      └───────────────┬──────────────────┘
                                      ▼
           ┌────────────────────────────────────────────────────────┐
           │       Ports (`typing.Protocol` + Pydantic Models)      │
           └───────────────────────────┬────────────────────────────┘
                                       ▼
           ┌────────────────────────────────────────────────────────┐
           │  Pure Domain Engine (DAG, EARS Parser, 3-Way Merger)   │
           │     *Zero imports from google.adk or google.genai*     │
           └────────────────────────────────────────────────────────┘
```

### 6.2 Safe Strangler-Fig Migration + Guarded Shadow-Mode Pattern

To migrate safely from LLM-heavy stages to deterministic Python without race conditions, drive stage resolution through a **`StageRegistry`** configured per stage in `.spec/config.yaml`:
- **`llm`**: Executes the `LlmAgent` adapter (Phase 1 default).
- **`shadow`** *(restricted strictly to pure/read-only stages or isolated copy-on-write sandboxes via `allow_shadow=True`)*: Clones unique node names (`node(llm_node, name=f"{stage}_llm")`, `node(python_node, name=f"{stage}_py")`), forwards `input_schema`/`output_schema` onto the nested `Workflow`, executes both concurrently via `JoinNode`, returns the trusted `llm` output, and records structural diffs + `AgentEvaluator` efficiency telemetry. **Never enable parallel `shadow` mode on mutating stages (`apply`, `archive`) sharing one working tree.**
- **`hybrid`**: Deterministic Python pre-pass (lint, evidence, AST) feeds a minimal LLM semantic judge (e.g., `Analyze`, `VerifyConverge`).
- **`python`**: Cuts over 100% to the deterministic `@node` `FunctionNode` once `shadow` diffs + `AgentEvaluator` reach target parity (`>= 99%`).

### 6.3 Git Worktree Isolation for Parallel Execution

When running multiple active changes or independent `roadmap.md` slices concurrently—or executing `[P]` tasks across conflicting modules—provision isolated Git worktrees:

```bash
git worktree add .worktrees/<change-id> -b spec/<change-id>
```

Each ADK `LocalEnvironment(working_dir=".worktrees/<change-id>")` operates inside its own clean checkout, preventing index locks, branch switching races, and cross-change file contamination, and cleans up automatically upon `archive`.

### 6.4 Python 3.14 Engineering & Design Patterns Checklist (`adk_review`-Aligned)

1. **`uv` Workspace & Supply-Chain Hygiene:** Pin `.python-version` to `3.14` (`requires-python = ">=3.14,<3.15"`), set `[tool.uv] exclude-newer = "P3D"` (3-day PyPI cooldown) and `required-version = ">=0.12"`, build with `hatchling>=1.33.0`, and isolate terminal UI dependencies in a separate `[tool.uv.workspace]` member (`members = ["tui"]`) so headless CI/pipeline installs stay minimal while sharing one `uv.lock`.
2. **Python 3.14 Native Typing (PEP 649 / PEP 749):** Omit `from __future__ import annotations` boilerplate—deferred annotation evaluation is now native, letting Pydantic `2.14.4` and ADK `@node` `TypeAdapter` schema inference handle forward references directly; use stdlib `annotationlib` for any runtime annotation inspection.
3. **PEP 750 Template Strings (`t-strings` via `string.templatelib.Template`):** Use `t"..."` when constructing untrusted data prompt wrappers (`<untrusted_data>`), Markdown renders, or TUI templates so static literals stay strictly separated from interpolated inputs for injection-safe escaping.
4. **Enterprise TLS (`truststore >= 0.10.5`) & Strict Subprocess Rules (`S607`):** Inject `truststore` before building HTTP/LLM clients so OS-trusted corporate proxy CAs work cleanly; resolve full executable paths (e.g., `git`, `pytest`) in production code to satisfy Ruff `S607`.
5. **Frozen Pydantic v2 Contracts (`ConfigDict(frozen=True, extra="forbid")`):** Immutable boundary DTOs prevent silent state corruption across parallel branches and enforce ADK Rule #8 static schema matching.
6. **Async-First with Explicit Blocking Offload:** All filesystem, subprocess, and SQLite/HTTP I/O runs either async or offloaded via `RunConfig(tool_thread_pool_config=ToolThreadPoolConfig(...))`.
7. **Structured Error Envelopes & Plugin Chain of Responsibility:** Adopt `{code, message, details, retryable}` envelopes across domain engines/tools, and place cross-cutting policies (`WritePolicyPlugin`, `ToolCallIntegrityPlugin`, `ModelArmorPlugin`, retry reflection) on `App`.
8. **Pinned Lint, Type & QA Toolchain:** Pin `ruff==0.17.6` (`line-length = 120`, `target-version = "py314"`, `mccabe max-complexity = 10`) and `pyrefly==1.5.0` (`direct-abstract-base-instantiation = "ignore"` for ADK's `LlmAgent`), plus `import-linter>=2.17`, `pytest>=9.2.0` (`asyncio_mode = "strict"`, `faulthandler_timeout = 300`), `hypothesis>=6.170.17`, and `mutmut>=3.8.1`.

---

## 7. Anti-Tautological Verification & Architectural Fitness Functions

AI coding agents frequently write shallow, example-only unit tests that mirror implementation bugs rather than validating invariants, or quietly introduce forbidden cross-layer imports. `adk-spec` defeats both failure modes deterministically:

1. **Property-Based Testing (`Hypothesis`) from EARS Invariants:**
   - Translate *Ubiquitous* and *Unwanted Behavior* EARS clauses into `@given(...)` property assertions (e.g., round-trip spec parsing/serialization, idempotency of `delta_merger` when re-applied, path-normalization invariants).
   - Translate *State-Driven* EARS clauses into `Hypothesis` `RuleBasedStateMachine` specs exploring arbitrary sequences of `propose`/`edit`/`analyze`/`archive` transitions.
2. **Mutation Testing Gate (`mutmut` / `cosmic-ray`):**
   - During `strict` `verify_converge`, run targeted mutation checks against newly written/modified Python modules. Any **surviving mutant** indicates an unverified branch or weak assertion—automatically appending a targeted remediation task to `## Phase N: Convergence` in `tasks.md`.
3. **Executable Architectural Fitness Functions (`import-linter`):**
   - Enforce `adk-spec`'s own Hexagonal boundary continuously in CI (`adk_spec.domain` MUST NOT import `google.adk`, `google.genai`, `adk_spec.adapters`, `adk_spec.orchestration`, or `adk_spec.interfaces`).
   - Optionally compile `constitution.md` module-layer bans into target-repo `import-linter` contracts checked deterministically during `analyze` and `verify_converge`.

---

## 8. OWASP Top 10 for Agentic Applications (2025–2026) Security Posture

| OWASP Agentic Risk | Threat Vector in Spec/Coding Agents | Concrete Defense in `adk-spec` |
| --- | --- | --- |
| **ASI01: Agent Goal Hijack** *(Indirect Prompt Injection)* | Malicious instructions embedded inside third-party repo READMEs, PR comments, or issue bodies read via `ReadFile` / git tools | Screen `after_tool_callback` outputs with ADK `ModelArmorPlugin`; wrap untrusted repo/issue text in explicit `<untrusted_data>` boundaries; separate `static_instruction` system policy |
| **ASI02: Tool Misuse & Exploitation** | Hijacked agent uses `Execute("sed -i ...")` or relative `..` paths to alter `checklists/`, `.spec/constitution.md`, or `.env` | Least-privilege `BaseToolset(tool_filter=...)` removing `WriteFile`/`EditFile`/`Execute` from RO agents; path-normalized `PurePosixPath` `WritePolicyPlugin`; narrow `append_convergence_tasks` tool; `ToolConfirmation` + `ToolCallIntegrityPlugin` |
| **ASI05: Unexpected Code Execution (RCE)** | Agent runs untrusted repo scripts, Skill scripts, or destructive shell pipelines | Dedicated `.worktrees/<change-id>` locally + cloud `E2BEnvironment` / `DaytonaEnvironment` container sandboxes for untrusted builds/tests; `RunConfig(max_llm_calls=...)` circuit breakers |
| **ASI06: Memory & Context Poisoning** | Poisoned PR text or transient hallucination gets saved into long-term `BaseMemoryService` and corrupts future changes | **Quarantine ingestion:** never persist unvetted sessions/PR text into `BaseMemoryService`; index only human-approved archived artifacts (`proposal.md`, `design.md`, `ReviewVerdict`) post-`archive` |

---

## 9. Cross-Platform Engineering (Windows & macOS First-Class Parity)

Grounded in `/Users/emrec/Projects/playground/adk_review/` production practices and Python 3.14 / `google-adk 2.15.0` internals:

1. **CRLF / Line-Ending & Git Determinism:**
   - Ship `.gitattributes` containing `* text=auto eol=lf` so Windows checkouts never rewrite spec or code line endings.
   - **Always normalize text to LF (`\n`) before computing SHA-256 requirement fingerprints or running 3-way `diff3`**, preventing Windows CRLF checkouts from triggering false `stale_base_conflict` aborts.
   - Pass settled Git overrides (`core.autocrlf=input`, `core.fsmonitor=false`, `core.precomposeUnicode=false`, `core.attributesFile=os.devnull`, stripping `GIT_*` env leaks) so macOS Unicode NFD paths and Windows CRLF index entries never distort diffs.
2. **Windows Path, Junction & Case-Sensitivity Hardening:**
   - Reject Windows drive letters (`^[A-Za-z]:`), UNC paths (`//` or `\\`), null bytes, reserved DOS device names (`CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`, `LPT1`–`LPT9`), POSIX symlinks (`Path.is_symlink()`), and **NTFS junctions (`os.path.isjunction()`)**.
   - Enforce strictly lowercase kebab-case capability and change IDs so case-insensitive Windows and macOS filesystems never collide.
3. **Subprocesses & Binary Resolution (`S607`):**
   - Never invoke `shell=True` when running `git`, `pytest`, `ruff`, or `pyrefly`; resolve binaries by **full path from absolute `PATH` entries only** (Windows searches the current working directory first unless avoided—critical when checking out untrusted repos).
   - On Windows timeouts, terminate process trees cleanly (`taskkill /F /T /PID`) because `LocalEnvironment` (`_local_environment.py`) notes `os.killpg` is ignored on Windows.
4. **Console Encoding, Temp Cleanup & User Directories:**
   - Call `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` and `sys.stderr.reconfigure(...)` at CLI entrypoints (Windows consoles default to legacy codepages like `cp1252`), pass `encoding="utf-8"` explicitly on every `Path.read_text` / `subprocess.run`, and offer ASCII fallbacks alongside Unicode glyphs.
   - Never hardcode `/tmp/`; use `tempfile.TemporaryDirectory(ignore_cleanup_errors=True)` and retry-guarded cleanup on `.worktrees/` removal (Windows Defender/indexers briefly lock recently read files).
   - Store user config/state under `%APPDATA%\adk-spec` on Windows and `$XDG_CONFIG_HOME/adk-spec` (`~/.config/adk-spec`) on macOS/Linux.
5. **Windows-Compatible Mutation Testing & 3-OS CI:**
   - Because `mutmut 3.8.1` relies on POSIX `os.fork()`, declare `"mutmut>=3.8.1; sys_platform != 'win32'"` and support `cosmic-ray>=8.9.0` (or WSL / Linux CI) for Windows mutation checks.
   - Document PowerShell/CMD `uv run ...` equivalents beside `Makefile` targets (GNU `make` is optional on Windows), ship `.github/copilot-instructions.md` + `.vscode/` settings, and gate PRs on a **3-OS CI matrix (`windows-latest`, `macos-latest`, `ubuntu-latest`)**—skipping tests on an OS only where the underlying OS primitive cannot exist, with an explicit skip reason.
