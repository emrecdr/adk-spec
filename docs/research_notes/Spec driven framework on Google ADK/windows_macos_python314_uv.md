# Windows + macOS, Python 3.14 and uv for a google-adk project (verified 2026-11-20 and 2026-11-21)

How to read these notes:

- Evidence labels: **[source-read]** = read from the `google-adk` 2.15.0 wheel/sdist or another primary file; **[documented]** = stated in official documentation; **[local test]** = run by the researcher on macOS arm64 with `uv 0.13.9 (Homebrew 2026-11-17)` and CPython 3.14.10, resolve-only (`uv lock`, `uv pip compile --no-build`), nothing installed or executed; **[inferred]** = reasoning from the above. Nothing was run on Windows.
- Versions verified against: `google-adk` 2.15.0 (PyPI upload 2026-11-20T00:30:35Z) and 2.14.1 (2026-11-12T21:32:01Z); `uv` 0.13.9 (released 2026-11-17); `litellm` 1.106.2 (2026-10-21T10:44Z) and 1.110.2 (2026-11-20T04:05Z); CPython 3.14.10 (released 2026-10-26).
- Fixed owner requirement: "latest" means the newest release that is at least three days old (`[tool.uv] exclude-newer = "P3D"`), as in the owner's `adk_review` project, which pins `google-adk==2.14.1`, `litellm==1.106.2` and `required-version = ">=0.12"`.
- Each section ends its Inferences with verdicts on the owner documents' claims (`reports/02-...roadmap.md`, `research_notes/.../04-validation-audit-...md`).

## 1. Does google-adk 2.15.0 (and 2.14.1) support Python 3.14, do its dependencies have 3.14 wheels on Windows x64 / Windows ARM64 / macOS arm64, and which 3.14 changes matter?

### Takeaway
Both 2.14.1 and 2.15.0 declare Python 3.14 (classifier, `constraints-3.14.txt`, a 3.14 CI job), but ADK's CI runs on `ubuntu-latest` only, so Windows and macOS are untested upstream. On Python 3.14, ADK 2.15.0 and LiteLLM install from wheels on Windows x64 and macOS arm64; 2.14.1 needs a source build of `watchdog` 6.0.0 on macOS; native Windows ARM64 has no wheels for LiteLLM, current `cryptography`, `fastuuid`, `tiktoken` or `grpcio`.

### Cited Findings

ADK metadata, constraints and CI

- `google-adk` 2.15.0: `Requires-Python: >=3.11`; classifiers for 3.11, 3.12, 3.13, 3.14 and 3.15 and `Operating System :: OS Independent`; one pure wheel `google_adk-2.15.0-py3-none-any.whl` plus sdist; uploaded 2026-11-20T00:30:35Z. — [PyPI JSON 2.15.0](https://pypi.org/pypi/google-adk/2.15.0/json)
- `google-adk` 2.14.1: same `Requires-Python` and classifiers; pure wheel; uploaded 2026-11-12T21:32:01Z. Its base dependencies differ from 2.15.0 in two lines: `google-genai>=2.30,<3` (2.15.0: `>=2.34,<3`) and `watchdog>=6,<7` (2.15.0: `>=7,<8`). — [PyPI JSON 2.14.1](https://pypi.org/pypi/google-adk/2.14.1/json)
- 2.15.0 base dependencies: `aiosqlite>=0.21`, `authlib>=1.9.1,<2`, `click>=8.1.8,<9`, `cryptography>=42`, `fastapi>=0.133,<1`, `google-auth[pyopenssl]>=2.47`, `google-genai>=2.34,<3`, `graphviz>=0.20.2,<1`, `httpx>=0.27,<1`, `jsonschema>=4.23,<5`, `opentelemetry-api>=1.39,<=1.45.2`, `opentelemetry-sdk>=1.39,<=1.45.2`, `packaging>=21`, `pydantic>=2.12,<3`, `python-dotenv>=1,<2`, `python-multipart>=0.0.9,<1`, `pyyaml>=6.0.2,<7`, `requests>=2.32.4,<3`, `starlette>=1.3.1,<2`, `tenacity>=9,<10`, `typing-extensions>=4.5,<5`, `uvicorn>=0.34,<1`, `watchdog>=7,<8`, `websockets>=15.0.1,<16`. `mcp`, `sqlalchemy`, `litellm`, `a2a-sdk` and the OTLP exporters are extras only (`[mcp]`: `mcp>=1.24,<3`, `anyio>=4.9,<5`, `aiohttp!=3.14.2`; `[db]`: `sqlalchemy[asyncio]>=2,<3`, `sqlalchemy-spanner>=1.14`; `[extensions]`: `litellm>=1.84,<1.106.3` and others; `[otel]`; `[a2a]`). — [google-adk 2.15.0 pyproject.toml](https://github.com/google/adk-python/blob/v2.15.0/pyproject.toml)
- The 3.15 classifier is generated, not tested: `[tool.pyproject-fmt] max_supported_python = "3.15"` writes it, and no CI job runs 3.15. — [google-adk 2.15.0 pyproject.toml](https://github.com/google/adk-python/blob/v2.15.0/pyproject.toml)
- `constraints-3.14.txt` exists at tag `v2.15.0` (beside 3.11, 3.12, 3.13 and 3.15 files). Header: `uv pip compile pyproject.toml --all-extras --python-version 3.14 --no-emit-package google-adk --exclude-newer 2026-11-05 ...`. It pins, among others, `google-genai==2.34.0`, `pydantic==2.13.4`, `pydantic-core==2.46.4`, `fastapi==0.139.2`, `starlette==1.3.1`, `uvicorn==0.51.0`, `litellm==1.95.0`, `mcp==1.28.1`, `sqlalchemy==2.0.51`, `watchdog==7.1.0`, `websockets==15.0.1`, `cryptography==49.0.0`, `opentelemetry-api==1.42.1`. It is one all-extras compile, not a per-platform file. — [constraints-3.14.txt at v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/constraints-3.14.txt)
- ADK CI at `v2.15.0`: unit tests run on `runs-on: ubuntu-latest` with `python-version: ["3.11", "3.12", "3.13", "3.14"]`; the mypy matrix is 3.11 to 3.13; the A2A and MCP v2 jobs are also Ubuntu only. No Windows or macOS job exists. `tox.ini` has `envlist = py311, py312, py313, py314`. — [continuous-integration.yml at v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/.github/workflows/continuous-integration.yml); [tox.ini at v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/tox.ini)
- An open ADK pull request states the consequence: three timeout tests "fail on Windows with exactly this AttributeError; CI only runs Linux, so the failure is invisible there." — [adk-python PR #8152](https://github.com/google/adk-python/pull/8152)
- ADK's docs state "ADK requires `litellm>=1.84`" for the LiteLLM connector. — [adk.dev llms-full.txt](https://adk.dev/llms-full.txt)

Known Python 3.14 issues in ADK

- Issue #7749 (closed 2026-10-30): on Python 3.14 and 3.15 `Path.is_dir()` returns `False` for `OSError` such as `PermissionError` instead of raising, so ADK 2.13.0 skill discovery silently skipped inaccessible directories without calling `on_error`. — [adk-python issue #7749](https://github.com/google/adk-python/issues/7749)
- PR #8045 (2026-11-09, labelled merged): "Watchdog 6.0.0 has no matching macOS wheels, causing `uv sync --locked` to fail when source builds are disabled" on Python 3.14; fixed by moving to watchdog v7. The fix is in 2.15.0 (`watchdog>=7,<8`), not in 2.14.1 (`watchdog>=6,<7`). — [adk-python PR #8045](https://github.com/google/adk-python/pull/8045); [PyPI JSON 2.14.1](https://pypi.org/pypi/google-adk/2.14.1/json)
- PR #4755 (closed 2026-03-26): context-parameter detection failed under deferred (string) annotations; fixed by resolving with `get_type_hints()` and falling back on `NameError`/`TypeError`/`AttributeError`. — [adk-python PR #4755](https://github.com/google/adk-python/pull/4755)
- A title search of `google/adk-python` for "3.14" returned only #8045 and #7749 on 2026-11-20. — [GitHub issue search](https://github.com/google/adk-python/issues?q=3.14+in%3Atitle)

How ADK 2.15.0 reads annotations (PEP 649/749) [source-read]

- Function-tool declarations call `get_type_hints_cached(func, include_extras=True)`, a wrapper over `typing.get_type_hints`; on `NameError` it retries once with ADK context types in `localns`; a per-parameter resolver (`get_best_effort_type_hints`) skips annotations it cannot resolve "so that resolvable sibling parameters still retain their type hints". — [utils/_callable_utils.py at v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/utils/_callable_utils.py); [tools/_function_tool_declarations.py at v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/tools/_function_tool_declarations.py)
- Plugin callback inspection is 3.14-aware: `_signature_without_annotations` uses `inspect.signature(function, annotation_format=annotationlib.Format.STRING)` when `sys.version_info >= (3, 14)`, with the comment "From Python 3.14, annotations are evaluated only when they are read, so a function may annotate its parameters with names it imports only for type checking, and reading those annotations as values raises NameError." — [plugins/_callback_helpers.py at v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/plugins/_callback_helpers.py)
- 749 of the 830 `.py` files in the 2.15.0 wheel begin with `from __future__ import annotations`. — [google-adk 2.15.0 files on PyPI](https://pypi.org/project/google-adk/2.15.0/#files)

Python 3.14 language and runtime changes [documented]

- PEP 649/749: annotations are no longer evaluated eagerly; they are stored in annotate functions and evaluated on demand, except under `from __future__ import annotations`. `annotationlib` offers `Format.VALUE` (raises `NameError` for undefined names), `Format.FORWARDREF` and `Format.STRING`; `inspect.signature()` gained `annotation_format`. — [What's New in Python 3.14](https://docs.python.org/3.14/whatsnew/3.14.html)
- PEP 750: `t"..."` literals produce `string.templatelib.Template` objects whose static parts and `Interpolation` objects can be processed separately. — [What's New in Python 3.14](https://docs.python.org/3.14/whatsnew/3.14.html)
- asyncio: "`asyncio.get_event_loop()` now raises a `RuntimeError` if there is no current event loop, and no longer implicitly creates an event loop"; the child watcher classes and `get_child_watcher()`/`set_child_watcher()` were removed; "The asyncio policy system is deprecated and will be removed in Python 3.16", naming `asyncio.WindowsSelectorEventLoopPolicy`, `asyncio.WindowsProactorEventLoopPolicy`, `asyncio.get_event_loop_policy()` and `asyncio.set_event_loop_policy()`; "Users should use `asyncio.run()` or `asyncio.Runner` with the `loop_factory` argument"; `asyncio.iscoroutinefunction()` is deprecated in favour of `inspect.iscoroutinefunction()`. — [What's New in Python 3.14](https://docs.python.org/3.14/whatsnew/3.14.html)
- `multiprocessing` and `ProcessPoolExecutor`: on Unix platforms other than macOS the default start method changed from `fork` to `forkserver`; Windows and macOS keep `spawn`. — [What's New in Python 3.14](https://docs.python.org/3.14/whatsnew/3.14.html)
- Free-threaded Python is officially supported in 3.14 (PEP 779). Python 3.14.0 to 3.14.4 shipped an incremental garbage collector that was reverted to the 3.13 generational collector in 3.14.5. PEP 765: `SyntaxWarning` when `return`/`break`/`continue` leaves a `finally` block. `PurePath.is_reserved()` has been deprecated since 3.13: "Use `os.path.isreserved()` to detect reserved paths on Windows." — [What's New in Python 3.14](https://docs.python.org/3.14/whatsnew/3.14.html)
- UTF-8 mode becomes the default only in Python 3.15 (PEP 686, `Python-Version: 3.15`). On 3.14, "Windows still uses legacy encodings for the system encoding (the ANSI Code Page)"; UTF-8 mode is opt-in via `-X utf8` or `PYTHONUTF8=1`. "Even when UTF-8 mode is disabled, Python uses UTF-8 by default on Windows for: Console I/O including standard I/O ... The filesystem encoding". — [PEP 686](https://peps.python.org/pep-0686/); [Using Python on Windows](https://docs.python.org/3.14/using/windows.html)
- Schedule: 3.14.10 was released 2026-10-26; 3.14.11 is expected 2026-12-08; bugfix releases continue about every two months to 3.14.16 on 2027-10-05 ("Final regular bugfix release with binary installers"); source-only security releases "until approximately October 2030". — [PEP 745](https://peps.python.org/pep-0745/)
- uv 0.13.0 (2026-10-09) made Python 3.15 "the default stable Python version"; this "affects Python downloads when no version is requested or pinned"; "For projects, use `uv python pin 3.14` to record the version in `.python-version`." — [uv CHANGELOG 0.13.0](https://github.com/astral-sh/uv/blob/main/CHANGELOG.md)
- `uv python install 3.14` prefers the GIL-enabled build; for 3.14+ a free-threaded interpreter can be used without explicit selection if it is first on `PATH`; `+gil` forces the GIL build. — [uv Python versions](https://docs.astral.sh/uv/concepts/python-versions/)

Wheel availability on CPython 3.14 (PyPI file listings read 2026-11-20; "any" = pure wheel)

| Package (version checked) | Windows x64 | Windows ARM64 | macOS arm64 | Note |
|---|---|---|---|---|
| google-adk 2.15.0 / 2.14.1 | any | any | any | pure Python |
| google-genai 2.34.0 (and 3.6.1) | any | any | any | ADK caps `<3` |
| pydantic 2.14.4 / pydantic-core 2.50.5 | cp314 | cp314 | cp314 | |
| cryptography 50.0.2 | abi3 | **none** | abi3 | win_arm64 wheels exist for 46.0.1 to 46.0.3 only |
| cffi 2.1.1, pyyaml 6.0.3, rpds-py 2026.9.1, regex, jiter 0.19.0, markupsafe 3.0.4, greenlet 3.5.6, asyncpg 0.32.0, pymongo 4.20.1, mmh3 | cp314 | cp314 | cp314 | |
| watchdog 7.1.0 (ADK 2.15.0) | py3-none | py3-none | cp314 | |
| watchdog 6.0.0 (ADK 2.14.1) | py3-none | **none** | **none for cp314** | released 2024-11-01; classifiers stop at 3.13 |
| websockets 15.0.1 (ADK caps `<16`; latest is 17.4) | any | any | any | |
| litellm 1.106.2 and 1.110.2 | abi3 (cp310) | **none** | abi3 (cp310) | maturin-built; contains `litellm/rust_bridge/_native.abi3.so` |
| fastuuid 0.14.0 (LiteLLM dependency on Python < 3.15) | cp314 | **none** | cp314 | |
| tiktoken 0.14.0 (LiteLLM dependency) | cp314 | **none** | cp314 | |
| tokenizers 0.23.3, hf-xet 1.8.0 (LiteLLM dependencies) | abi3 | abi3 | abi3 | |
| aiohttp 3.14.5, yarl, multidict, frozenlist, propcache | yes | yes | yes | pure fallback wheels exist |
| mcp 2.3.0, mcp-types, pydantic-settings, sse-starlette, anyio, pyjwt | any | any | any | |
| pywin32 312 (pulled in on Windows by `mcp`) | cp314 | cp314 | n/a | no sdist |
| sqlalchemy 2.1.9, aiosqlite 0.22.1, redis 8.1.0, psycopg 3.3.9 | any | any | any | |
| psycopg-binary 3.3.9, psycopg2-binary 2.9.13 | cp314 | **none** | cp314 | |
| grpcio 1.85.3 (via `sqlalchemy-spanner` in `[db]`, GCP exporters) | cp314 | **none** | cp314 | |
| opentelemetry-api/sdk 1.45.2, otlp-proto-http 1.45.2, protobuf 7.36.2 | any | any | any | ADK caps OTel `<=1.45.2` |
| a2a-sdk 1.3.1, truststore 0.10.5, python-dotenv 1.2.4 | any | any | any | |

Sources for the table: [google-adk](https://pypi.org/pypi/google-adk/json), [cryptography](https://pypi.org/pypi/cryptography/json), [watchdog 7.1.0](https://pypi.org/pypi/watchdog/7.1.0/json), [watchdog 6.0.0](https://pypi.org/pypi/watchdog/6.0.0/json), [litellm 1.110.2](https://pypi.org/pypi/litellm/1.110.2/json), [litellm](https://pypi.org/pypi/litellm/json), [fastuuid](https://pypi.org/pypi/fastuuid/json), [tiktoken](https://pypi.org/pypi/tiktoken/json), [tokenizers](https://pypi.org/pypi/tokenizers/json), [pywin32](https://pypi.org/pypi/pywin32/json), [grpcio](https://pypi.org/pypi/grpcio/json), [psycopg-binary](https://pypi.org/pypi/psycopg-binary/json), [mcp](https://pypi.org/pypi/mcp/json), [pydantic-core](https://pypi.org/pypi/pydantic-core/json), [websockets](https://pypi.org/pypi/websockets/json).

- `cryptography` changelog: 46.0.0 (2025-09-16) "We now build `win_arm64` (Windows on Arm) wheels and publish them to PyPI"; 46.0.4 (2026-01-27) "Dropped support for win_arm64 wheels". — [cryptography CHANGELOG](https://github.com/pyca/cryptography/blob/main/CHANGELOG.rst)
- LiteLLM wheel metadata: `Generator: maturin (1.15.0)`, `Root-Is-Purelib: false`, tag `cp310-abi3-macosx_11_0_arm64`. LiteLLM 1.106.2 through 1.110.2 publish wheels for macOS x86_64/arm64, manylinux and musllinux x86_64/aarch64 and `win_amd64`, plus an sdist. `litellm` 1.106.2 declares `requires_python <3.15,>=3.10`; 1.109.x and 1.110.x declare `<3.16,>=3.10`. LiteLLM 1.110.2 hard-requires, among others, `fastuuid>=0.14.0` (only on Python < 3.15), `tiktoken>=0.12.0` on 3.14, `tokenizers`, `huggingface-hub`, `aiohttp>=3.14.2`, `pydantic>=2.12.0` on 3.14, `pydantic-settings>=2.14.1`, `boto3>=1.43.117`, `openai>=2.20.0`. — [litellm 1.110.2 files](https://pypi.org/project/litellm/1.110.2/#files); [litellm 1.110.2 JSON](https://pypi.org/pypi/litellm/1.110.2/json)

Wheels-only resolution checks [local test: `uv pip compile --no-build --python-version 3.14 --python-platform <target>`]

| Requirement set | x86_64-pc-windows-msvc | aarch64-pc-windows-msvc | aarch64-apple-darwin |
|---|---|---|---|
| `google-adk==2.15.0` | OK, 48 packages | OK only by falling back to `cryptography==46.0.3` | OK, 48 packages |
| `google-adk[mcp]==2.15.0` | OK (adds `pywin32==312`) | OK with `cryptography==46.0.3` | OK |
| `google-adk[otel]==2.15.0`, `[a2a]` | OK | OK with `cryptography==46.0.3` | OK |
| `google-adk[db]==2.15.0` | OK | FAIL: `grpcio` has no usable wheels | OK |
| `google-adk[extensions]==2.15.0` | OK (162 packages) | FAIL: `grpcio` (and LiteLLM) | OK |
| `google-adk[eval]==2.15.0` | FAIL everywhere: `rouge-score==0.1.2` is sdist-only | same | same |
| `google-adk[mcp,db,otel,a2a]==2.15.0` + `litellm==1.110.2` + `truststore` + `python-dotenv` | OK, 123 packages | FAIL: `litellm==1.110.2 has no usable wheels` | OK, 121 packages |
| `google-adk==2.14.1` (P3D cooldown) | OK, 48 packages | FAIL: `watchdog==6.0.0 has no usable wheels` | FAIL: `watchdog==6.0.0 has no usable wheels` |
| adk_review set: `google-adk==2.14.1`, `litellm==1.106.2`, `truststore`, `python-dotenv`, `ruff==0.17.5`, `pyrefly==1.4.1` (P3D) | OK, 85 packages | FAIL: `litellm==1.106.2 has no usable wheels` | FAIL: `watchdog==6.0.0 has no usable wheels` |

- Flag semantics behind the test: with `no-build`, operations that need a new sdist build fail. — [uv settings reference](https://docs.astral.sh/uv/reference/settings/)
- uv 0.13.0 changed the Windows ARM64 default: "Previously, ARM64 builds of uv preferred emulated `x86_64` Python installations because native wheel support was limited. Now, uv prefers native ARM64 (`aarch64`) interpreters". Opt out with `UV_PYTHON_ARCH=x86_64` or an explicit request such as `cpython-3.14-windows-x86_64`; with `setup-uv`, `python-arch: x86_64`. The entry says CPython, the Python install manager and `actions/setup-python` made similar changes. — [uv CHANGELOG 0.13.0](https://github.com/astral-sh/uv/blob/main/CHANGELOG.md)
- "Both macOS and Windows support running x86_64 binaries on aarch64 through transparent emulation." — [uv Python versions](https://docs.astral.sh/uv/concepts/python-versions/)

### Inferences
- "Supports 3.14" holds for both 2.14.1 and 2.15.0 in the sense of classifier + constraints file + Linux CI. It does not extend to Windows or macOS, which ADK does not test; a Windows-first project must run its own Windows CI and will meet ADK regressions before upstream does.
- For adk_review's current pins (2.14.1 on Python 3.14), a macOS install works only because `watchdog` 6.0.0 is compiled from its sdist (needs a C compiler, that is Xcode Command Line Tools). 2.15.0 removes that build. A `--no-build` policy is incompatible with 2.14.1 on macOS + 3.14.
- A universal `uv.lock` records `cryptography` 50.0.2 for all platforms (observed), so on native Windows ARM64 `uv sync` would try to build `cryptography`, `litellm`, `fastuuid` and `tiktoken` from source (Rust toolchain plus MSVC). The practical route on Windows ARM64 is an x64 interpreter under emulation (`UV_PYTHON_ARCH=x86_64`). Because `required-version = ">=0.12"` admits both uv 0.12.x (prefers emulated x64) and 0.13.x (prefers native ARM64), behaviour on those machines depends on the uv version unless the variable is set.
- Staying on 3.14 has three concrete consequences: (1) uv 0.13 downloads 3.15 by default, so the pin must be explicit everywhere; (2) UTF-8 mode is not the default until 3.15, so every file, pipe and subprocess encoding must be explicit or `PYTHONUTF8=1` must be set; (3) asyncio event-loop policies still exist but are deprecated, so new code should use `loop_factory`.
- PEP 649 lets framework code drop `from __future__ import annotations`, but a tool function whose parameter annotation names a `TYPE_CHECKING`-only import raises `NameError` inside `typing.get_type_hints`; ADK's fallback then drops that parameter's hint (the generated schema loses the type) instead of failing. Tool signatures and Pydantic models should import their annotation types at runtime.
- Free-threaded 3.14t should be avoided: LiteLLM, `fastuuid` and `pywin32` publish no `cp314t` wheels (same PyPI listings), and uv can select a free-threaded interpreter that is first on `PATH`.

Verdicts on the owner documents' claims

| Claim | Verdict |
|---|---|
| `google-adk` 2.15.0 has a 3.14 classifier, a wheel and `constraints-3.14.txt` | Confirmed (also true of 2.14.1 for classifier and wheel) |
| `google-adk 2.15.0` requires `google-genai>=2.34,<3`; `2.34.0` in `constraints-3.14.txt`; PyPI has 3.6.1 | Confirmed |
| "ADK excludes `aiohttp!=3.14.2`" | Confirmed, in the `mcp`, `slack`, `teams` and `all` extras only |
| Core stack "all ship Python 3.14 wheels" (pydantic, fastapi, uvicorn, pyyaml, aiosqlite, sqlalchemy) | Confirmed for Windows x64 and macOS arm64; on Windows ARM64 `cryptography` (a base ADK dependency) has no current wheel |
| Python 3.14.10 is the current 3.14 | Confirmed (released 2026-10-26) |
| PEP 649/749 allows omitting `from __future__ import annotations`; PEP 750 `string.templatelib.Template` exists | Confirmed, with the `TYPE_CHECKING` caveat above |
| `litellm==1.110.2` as the pinned Copilot arm | Exists, but: published 2026-11-20 (younger than the cooldown), outside the range ADK tests (`<1.106.3`), compiled (Rust) with no Windows ARM64 wheel |

### Gaps
- No ADK statement was found that Windows is a supported or tested platform.
- Wheel coverage was resolved only for the extras in the table; `[gcp]`, `[eval]` beyond `rouge-score`, and every transitive dependency of `[extensions]` were not enumerated individually.
- Whether `uv.toml`/`[tool.uv]` has a persistent setting equivalent to `UV_PYTHON_ARCH` was not checked.
- Must be tested on real Windows: `uv sync --locked` on Windows x64 with Python 3.14; the same on Windows ARM64 with and without `UV_PYTHON_ARCH=x86_64`; import and one live call of LiteLLM's Rust bridge on Windows.

## 2. Which Windows-specific problems are documented for ADK?

### Takeaway
ADK 2.15.0 has explicit Windows branches (reload forced off, `taskkill` in the dev server, drive-letter and reserved-name handling in file artifacts), but its local command and code-execution paths are POSIX-shaped: `ExecuteBashTool` refuses to run on Windows, `LocalEnvironment` runs through the shell without a process group, and its timeout escalation references `signal.SIGKILL`, which does not exist on Windows (open PR #8152).

### Cited Findings

What ADK's own documentation says about Windows

- "Note for Windows users: When hitting the `_make_subprocess_transport NotImplementedError`, consider using `adk web --no-reload` instead." — [adk.dev llms-full.txt](https://adk.dev/llms-full.txt)
- "Windows Encoding with LiteLLM: When using ADK agents with LiteLLM on Windows, you might encounter a `UnicodeDecodeError`. This error occurs because LiteLLM may attempt to read cached files using the default Windows encoding (`cp1252`) instead of UTF-8. Prevent this error by setting the `PYTHONUTF8` environment variable to `1`." The PowerShell example is `$env:PYTHONUTF8 = "1"`. — [adk.dev llms-full.txt](https://adk.dev/llms-full.txt)
- "`ExecuteBashTool` is currently supported **only on POSIX systems** such as Linux or macOS. Executing this tool on a Windows system will result in a hard error." — [adk.dev llms-full.txt](https://adk.dev/llms-full.txt)
- "When using ADK on Windows for the next few steps, we recommend creating Python files using File Explorer or an IDE because the following commands (`mkdir`, `echo`) typically generate files with null bytes and/or incorrect encoding." — [adk.dev llms-full.txt](https://adk.dev/llms-full.txt)

`adk web` / `adk api_server`, reload and the event loop

- `--reload/--no-reload` defaults to `True`; `_check_windows_reload` forces it off on `sys.platform == "win32"` with the message "The --reload flag is not supported on Windows because it forces Uvicorn to use SelectorEventLoop, which does not support subprocesses (needed for executing tools). Forcing --no-reload." It is applied in the `web` and `api_server` commands. `--reload_agents` (watchdog-based) is a separate flag, default off. — [cli/cli_tools_click.py at v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/cli/cli_tools_click.py)
- Python's platform notes: "On Windows, `ProactorEventLoop` is now the default event loop" (since 3.8); for `SelectorEventLoop` on Windows "Subprocesses are not supported, i.e. `loop.subprocess_exec()` and `loop.subprocess_shell()` methods are not implemented"; `loop.add_signal_handler()` and `loop.remove_signal_handler()` are not supported by any Windows event loop; `ProactorEventLoop` does not support `add_reader()`/`add_writer()`. — [asyncio Platform Support](https://docs.python.org/3.14/library/asyncio-platforms.html)
- History of the guard: issue #585 "MCPToolset.from_server fails on Windows with NotImplementedError from asyncio subprocess", PR #415 "fix(cli): Disable auto-reload feature on Windows system", PR #958, issues #725 and #1321 (local MCP servers not starting on Windows); all closed in 2025. — [issue #585](https://github.com/google/adk-python/issues/585); [PR #415](https://github.com/google/adk-python/pull/415); [issue #725](https://github.com/google/adk-python/issues/725); [issue #1321](https://github.com/google/adk-python/issues/1321)
- The dev server's own subprocess handling is Windows-aware: `CREATE_NEW_PROCESS_GROUP` on Windows (`start_new_session` elsewhere) and tree termination with `taskkill /PID <pid> /T` (adding `/F` when forcing), falling back to `process.kill()`. — [cli/dev_server.py at v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/cli/dev_server.py)
- Issue #4418 (closed 2026-02-11): on Windows with ADK 1.24.1 and Python 3.14.2, `adk web` opened a console pop-up window for each model, sub-agent or tool call. — [issue #4418](https://github.com/google/adk-python/issues/4418)
- Issue #6248 / PR #6166 (closed 2026-08): Click's Windows glob expansion made CLI commands fail when an option value contained `*`. — [issue #6248](https://github.com/google/adk-python/issues/6248)
- `adk web`, `adk run` and `adk api_server` default to `use_local_storage=True`; sessions go to `<agent_dir>/.adk/session.db` (SQLite); `--no_use_local_storage` switches it off; `adk create` writes `.env` and `.adk/` into the generated `.gitignore`. — [cli/utils/dot_adk_folder.py at v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/cli/utils/dot_adk_folder.py); [cli/cli_tools_click.py at v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/cli/cli_tools_click.py); [cli/cli_create.py at v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/cli/cli_create.py)

Local command and code execution

- `LocalEnvironment.execute` uses `asyncio.create_subprocess_shell(command, ..., start_new_session=True)` with the comment "Its own session, so a timeout can take down everything the command started and nothing else. Ignored on Windows, as `os.killpg` is." `_signal_group` returns immediately when `os.killpg` is missing, so on Windows only `proc.terminate()` / `proc.kill()` act, on the shell process itself. Output is decoded as UTF-8 with `errors='replace'`. — [environment/_local_environment.py at v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/environment/_local_environment.py)
- The escalation step in the same file calls `_signal_group(group, signal.SIGKILL)` unconditionally. PR #8152 (open, created 2026-11-14, unmerged on 2026-11-20): "`signal.SIGKILL` does not exist on Windows", so a timed-out `UnsafeLocalCodeExecutor` execution raises `AttributeError: module 'signal' has no attribute 'SIGKILL'`, "The process is never killed", and "`LocalEnvironment._kill_command` has the same unconditional `signal.SIGKILL` lookup in its escalation step (SIGTERM, 5 s grace, then SIGKILL), so a timed-out command whose descendants keep the output pipes open crashes the same way instead of returning a timed-out `ExecutionResult`." — [adk-python PR #8152](https://github.com/google/adk-python/pull/8152)
- Python documents `signal.SIGKILL` as "Availability: Unix". — [signal module](https://docs.python.org/3.14/library/signal.html)
- `ExecuteBashTool` returns `{"error": "ExecuteBashTool is only supported on POSIX systems."}` when `os.name != "posix"`; on POSIX it uses `shlex.split`, `start_new_session=True`, `preexec_fn` resource limits and `os.killpg`. — [tools/bash_tool.py at v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/tools/bash_tool.py)
- `LocalEnvironment` file access reads and writes bytes (`open(path, 'rb')` / `'wb'`) and confines paths with `candidate.resolve()` + `is_relative_to(working_dir)`. — [environment/_local_environment.py at v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/environment/_local_environment.py)
- Issue #6289 / PR #6288 (closed 2026-07): `RunSkillScriptTool` shell output could fail to decode under Windows locale defaults. Issue #5819 / PR #5820 (closed 2026-06): `UnicodeEncodeError` on Windows when materialising skill files. — [issue #6289](https://github.com/google/adk-python/issues/6289); [issue #5819](https://github.com/google/adk-python/issues/5819)

Paths, artifacts, sessions, encoding

- `FileArtifactService` rejects rooted, drive-qualified and `..` paths using both `PurePosixPath` and `PureWindowsPath`, compares names caselessly "because the collision is decided by the filesystem, and the case-insensitive ones ADK supports (APFS, NTFS) resolve `Metadata.json` and `metadata.json` to the same file", and strips trailing dots and spaces "because Win32 removes them from path components". In 2.15.0 payloads are written and read as bytes with explicit UTF-8. — [artifacts/file_artifact_service.py at v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/artifacts/file_artifact_service.py)
- Issue #7914 (opened 2026-10-31, closed 2026-11-06): `FileArtifactService` changed line endings because it used `Path.read_text`/`write_text`: "on Windows every `\n` is stored as `\r\n`", on the backend `adk web` and `adk run` use by default. — [issue #7914](https://github.com/google/adk-python/issues/7914)
- Issue #5486 / PR #5523 (closed 2026-07): `file:///C:/...` artifact URIs resolved to the wrong path on Windows; 2.15.0 applies `url2pathname` when `os.name == "nt"`. — [issue #5486](https://github.com/google/adk-python/issues/5486); [cli/service_registry.py at v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/cli/service_registry.py)
- PR #7098 (closed 2026-11-05): Windows drive-letter `sqlite:///C:/...` session URIs were mishandled; found "while running the documented unit tests on Windows". — [PR #7098](https://github.com/google/adk-python/pull/7098)
- PR #7979 (open, 2026-11-03): `ntpath.isabs('/etc/passwd')` is `False`, so the "absolute paths are not allowed" guard for `AgentRefConfig.config_path` does not fire on Windows and a cross-drive case raises an unhandled `ValueError: Paths don't have the same drive`. — [PR #7979](https://github.com/google/adk-python/pull/7979)
- Closed Windows issues: #4635 (`adk deploy` `[WinError 5]` when cleaning read-only `.git` files), #4223 (paths starting with `\u`), #6415 (`adk eval` misparsing Windows absolute paths), #361 (`adk web` agent discovery), tracking issue #3306 "Main Issue: ADK Windows platform issues" (closed 2026-02-06). — [issue #4635](https://github.com/google/adk-python/issues/4635); [issue #6415](https://github.com/google/adk-python/issues/6415); [issue #3306](https://github.com/google/adk-python/issues/3306)
- UTF-8 hardening during 2026: PR #6763 "read and write CLI text files as UTF-8", #6690 and #6298 (eval JSON files), #7538, #7453. In the 2.15.0 wheel the text opens in `cli/cli.py` pass `encoding='utf-8'`. — [PR #6763](https://github.com/google/adk-python/pull/6763); [cli/cli.py at v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/cli/cli.py)

MCP stdio

- ADK hands `StdioConnectionParams` to the MCP SDK's `stdio_client(..., errlog=sys.stderr)`; `mcp_session_manager.py` contains no Windows-specific code. On Windows the `[mcp]` extra resolves `pywin32` 312. — [tools/mcp_tool/mcp_session_manager.py at v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/tools/mcp_tool/mcp_session_manager.py); [pywin32 on PyPI JSON](https://pypi.org/pypi/pywin32/json)

### Inferences
- On Windows a `LocalEnvironment` timeout either leaves the command's children running (only the `cmd.exe` shell is terminated) or, when children hold the pipes for more than 5 seconds, raises `AttributeError` inside the tool call. A Windows-first framework should not route test runners, linters or git through `LocalEnvironment` / `EnvironmentToolset` `Execute`; its own argv-based runner with tree kill is the safer design.
- Because `LocalEnvironment` uses `create_subprocess_shell`, a command string is interpreted by `cmd.exe` on Windows and `/bin/sh` on macOS, so agent-written command strings are not portable between the two.
- `adk web` on Windows drops `--reload` automatically. The framework's own launchers must also avoid uvicorn `reload=True` and any explicit `SelectorEventLoop`/policy selection, or MCP stdio servers and subprocess tools fail with `NotImplementedError`. With policies deprecated in 3.14, the correct mechanism is `asyncio.run(..., loop_factory=...)`, and the default (Proactor) is the right loop.
- The LiteLLM `cp1252` problem in ADK's docs applies directly to the Copilot arm on Python 3.14; `PYTHONUTF8=1` in the documented launch environment (or `-X utf8`) is the upstream-recommended fix, in addition to explicit encodings in the framework's own code.
- ADK has no Windows CI, so each ADK upgrade is a Windows regression risk (pop-up consoles in 1.24.1, `SIGKILL` in the 2.1x line). The cooldown does not cover this; a Windows job in the project's own CI does.

Verdicts on the owner documents' claims

| Claim | Verdict |
|---|---|
| `LocalEnvironment` uses `create_subprocess_shell` and "ignores `start_new_session=True` / `os.killpg` on Windows" | Confirmed from source; understated, since the `SIGKILL` lookup can also crash the timeout path on Windows (PR #8152, open) |
| ADK writes sessions to `.adk/session.db` by default; `adk web --no_use_local_storage` avoids it | Confirmed (flag and path exist in 2.15.0). That the stored diffs are "unredacted" was not examined |
| Use `taskkill /F /T /PID` for tree kill on Windows | Consistent with ADK's own dev server (`taskkill /PID <pid> /T [/F]`) and with adk_review |

### Gaps
- Must be tested on real Windows: `adk web` and `adk run` (interactive `input()` loop, console encoding), MCP stdio servers started through `npx`/`uvx` shims, `.adk/session.db` locking while the dev UI is open, whether the #4418 console pop-ups are gone in 2.14.1/2.15.0, and the `LocalEnvironment` timeout path.
- Whether a fix equivalent to PR #8152 landed on `main` after 2.15.0 is unknown.
- No ADK issue about `MAX_PATH` was found; `.adk/artifacts/...` nesting under a deep project path is untested.
- Issue #7914's fix release was not pinned down; 2.15.0 uses byte I/O, 2.14.1 was not inspected.

## 3. What are the right uv practices (pinning 3.14, universal lock, markers, workspaces, `uv run`, installing on Windows), is `exclude-newer = "P3D"` valid, and how does the cooldown behave?

### Takeaway
`exclude-newer = "P3D"` is valid in uv 0.13.9 and is recorded in `uv.lock` as a span, not a date; a `==` pin younger than the span makes `uv lock` fail with an explicit hint, and `exclude-newer-package` exempts a single package. `uv tool install`, pip and pre-commit read neither the lock nor the project's `[tool.uv]`, so the cooldown has to be handed to them explicitly.

### Cited Findings

Cooldown syntax and recorded form

- `exclude-newer` accepts RFC 3339 timestamps, "friendly" durations (`24 hours`, `1 week`, `30 days`) and ISO 8601 durations (`PT24H`, `P7D`, `P30D`). Durations are "always resolved to a fixed number of seconds assuming that a day is 24 hours"; "Calendar units such as months and years are not allowed"; the cutoff is compared with "the upload time of each individual distribution artifact"; `false` disables it. — [uv settings reference](https://docs.astral.sh/uv/reference/settings/); [uv resolution concepts](https://docs.astral.sh/uv/concepts/resolution/)
- `exclude-newer-package` is a table of `package = "date-or-duration"`; `false` exempts the package from the global setting. Docs example: `exclude-newer-package = { tqdm = "2022-04-04T00:00:00Z", markupsafe = false }`; CLI form `--exclude-newer-package "setuptools=30 days"`. — [uv settings reference](https://docs.astral.sh/uv/reference/settings/); [uv resolution concepts](https://docs.astral.sh/uv/concepts/resolution/)
- A distribution with no upload-time field "will be treated as unavailable" unless the package is opted out or its index carries its own `exclude-newer`; the option applies to registry packages, not Git dependencies. — [uv resolution concepts](https://docs.astral.sh/uv/concepts/resolution/)
- History: relative durations ("dependency cooldowns") arrived in uv 0.9.17 (2025-12-09); per-package disable in 0.9.25; 0.10.0 stopped invalidating locked versions when `exclude-newer` changes ("uv will only change package versions if they are no longer within the `exclude-newer` range"); 0.11.8 (2026-04-27) introduced "a sentinel timestamp for relative `exclude-newer` and `exclude-newer-package` values in lockfiles" and `exclude-newer-span`; 0.11.5 added per-index `exclude-newer`; 0.12.10 fixed `--locked` and `uv lock --check` cases with `exclude-newer-package`; 0.12.12 excludes too-new files from the lock and from generated hashes; 0.13.2 respects `--exclude-newer` when a newer wheel is already cached. — [uv changelog 0.9.x](https://github.com/astral-sh/uv/blob/main/changelogs/0.9.x.md); [0.10.x](https://github.com/astral-sh/uv/blob/main/changelogs/0.10.x.md); [0.11.x](https://github.com/astral-sh/uv/blob/main/changelogs/0.11.x.md); [0.12.x](https://github.com/astral-sh/uv/blob/main/changelogs/0.12.x.md); [CHANGELOG 0.13.x](https://github.com/astral-sh/uv/blob/main/CHANGELOG.md)
- [local test] With `[tool.uv] exclude-newer = "P3D"`, uv 0.13.9 wrote this lock header: `version = 1`, `revision = 5`, `requires-python = "==3.14.*"`, then `[options]` with `exclude-newer = "0001-01-01T00:00:00Z" # This has no effect and is included for backwards compatibility when using relative exclude-newer values.` and `exclude-newer-span = "P3D"`. `uv lock --check` immediately afterwards passed. — behaviour described in [uv changelog 0.11.x, entry 0.11.8](https://github.com/astral-sh/uv/blob/main/changelogs/0.11.x.md)
- Conflict between sources: the docs say "When using a `uv.lock` file, the timestamp is included in the lockfile. uv will not update the lockfile when the current time changes, instead, uv will update the timestamp when a new resolution is performed, e.g., when `--upgrade` or `--refresh` is used." The observed 0.13.9 lock contains only the sentinel timestamp and the span, as the 0.11.8 changelog entry describes. The stable-over-time behaviour is the same in both accounts. — [uv resolution concepts](https://docs.astral.sh/uv/concepts/resolution/); [uv changelog 0.11.x](https://github.com/astral-sh/uv/blob/main/changelogs/0.11.x.md)

A pin younger than the cooldown, and exemptions [local tests, 2026-11-20 22:48 to 22:50 UTC]

- `google-adk==2.15.0` + `litellm==1.110.2` with `exclude-newer = "P3D"`: `uv lock` failed with "Because there is no version of google-adk==2.15.0 and your project depends on google-adk==2.15.0, we can conclude that your project's requirements are unsatisfiable." and the hint "`google-adk` was filtered by `exclude-newer` to only include packages uploaded before 2026-11-17T22:48:53.088301Z. The requested version, v2.15.0, was published at 2026-11-20T00:30:35.991Z. Consider using `exclude-newer-package` to override the cutoff for this package." The hint feature dates from 0.10.8 and 0.11.7. — [uv changelog 0.10.x](https://github.com/astral-sh/uv/blob/main/changelogs/0.10.x.md); [uv changelog 0.11.x](https://github.com/astral-sh/uv/blob/main/changelogs/0.11.x.md)
- The same project locks when one of these is added: `exclude-newer-package = { google-adk = false }`, `{ google-adk = "2026-11-21T00:00:00Z" }` or `{ google-adk = "P0D" }`; the lock gains `[options.exclude-newer-package]` holding `google-adk = false`, the timestamp, or `{ timestamp = "0001-01-01T00:00:00Z", span = "PT0S" }`. `{ google-adk = "1 day" }` parsed and still rejected 2.15.0. With ADK exempted, its dependencies stayed under the cooldown (`authlib` 1.9.9 not 1.9.10, `fastapi` 0.163.2 not 0.165.0, `pydantic` 2.14.3 not 2.14.4). — setting documented in [uv settings reference](https://docs.astral.sh/uv/reference/settings/)
- adk_review's pins (`google-adk==2.14.1`, `litellm==1.106.2`, `truststore>=0.10`, `python-dotenv>=1.0`) locked under P3D to 84 packages, including `cryptography` 50.0.2, `google-genai` 2.34.0, `fastuuid` 0.14.0, `tiktoken` 0.14.0. — setting documented in [uv resolution concepts](https://docs.astral.sh/uv/concepts/resolution/)
- `required-version` enforces a uv version with a PEP 440 specifier; a non-matching uv exits with an error. — [uv settings reference](https://docs.astral.sh/uv/reference/settings/)

Installs that read no lock

- "For `tool` commands, which operate at the user level, local configuration files will be ignored." They read only user-level (`~/.config/uv/uv.toml`, `%APPDATA%\uv\uv.toml`) and system-level (`/etc/uv/uv.toml`, `%PROGRAMDATA%\uv\uv.toml`) configuration. — [uv configuration files](https://docs.astral.sh/uv/concepts/configuration-files/)
- "tools are always run isolated from the project"; `uv tool install` takes the latest version unless one is requested; per-project Python requests such as `.python-version` are ignored for tools; `uv tool upgrade` "will respect the version constraints provided when installing the tool" and "retain the settings provided when installing the tool"; "Tool executables are symlinked into the executable directory on Unix and copied on Windows." — [uv tools concepts](https://docs.astral.sh/uv/concepts/tools/)
- [local test] uv 0.13.9 has the flags adk_review's install recipe relies on: `uv export --frozen --no-hashes --no-dev --no-emit-project`; `uv tool install -c/--constraints`, `--exclude-newer`, `--exclude-newer-package`, `--reinstall`, `--no-build`; `uv run --no-project`; `uv lock --check`, `-U/--upgrade`, `-P/--upgrade-package`; `uv sync --locked`, `--all-packages`, `--no-build`. — [uv tools concepts](https://docs.astral.sh/uv/concepts/tools/)
- adk_review's `Makefile` does `uv export --frozen --no-hashes --no-dev --no-emit-project --quiet --output-file "$(LOCKED)"` then `uv tool install --reinstall --exclude-newer P3D --constraints "$(LOCKED)" .`, with the recorded reason "`uv tool install .` alone took a LiteLLM three days old or less, where the lock holds an older one; and, reading no [tool.uv] of the project, it took the build backend's newest release". Its `pyproject.toml` pins `litellm`, `ruff` and `pyrefly` exactly because "`uv tool install`, pip and pre-commit resolve afresh". — local files `/Users/emrec/Projects/playground/adk_review/Makefile` and `/Users/emrec/Projects/playground/adk_review/pyproject.toml`

Python pinning, universal lock, markers, workspaces

- uv searches the working directory and its parents for `.python-version`; `uv python pin` writes it; project commands respect `requires-python` and use the first compatible interpreter unless a version is requested; managed Python is preferred, but an installed system Python is preferred over a download; downloads are automatic by default. — [uv Python versions](https://docs.astral.sh/uv/concepts/python-versions/)
- `uv.lock` is a universal resolution, "portable across operating systems, architectures, and Python versions"; different versions of a package may be locked for different markers. `sys_platform` is `'linux'`, `'darwin'` or `'win32'` ("On Windows, `sys_platform` is always `'win32'`, even on 64-bit systems"). — [uv resolution concepts](https://docs.astral.sh/uv/concepts/resolution/)
- `[tool.uv] environments` limits the platforms uv solves for (entries must be disjoint); `required-environments` lists platforms for which packages without source distributions must have wheels. — [uv settings reference](https://docs.astral.sh/uv/reference/settings/); [uv resolution concepts](https://docs.astral.sh/uv/concepts/resolution/)
- Lock schema: a uv version rejects a lock with a greater `version`; schema bumps happen only in minor releases; `revision` changes "will not cause older versions of uv to error". — [uv resolution concepts](https://docs.astral.sh/uv/concepts/resolution/)
- `link-mode` defaults to `clone` on macOS and Linux and `hardlink` on Windows. — [uv settings reference](https://docs.astral.sh/uv/reference/settings/)
- Workspaces: every workspace has a root that is also a member; `uv run` and `uv sync` operate on the root by default and take `--package`; members reference each other with `{ workspace = true }` under `tool.uv.sources`; the workspace's Python requirement is the "intersection of all members' `requires-python` values"; configuration is read from the root ("ignoring any configuration defined in workspace members"). — [uv workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/); [uv configuration files](https://docs.astral.sh/uv/concepts/configuration-files/)
- adk_review uses one root project plus one member (`[tool.uv.workspace] members = ["tui"]`), one `uv.lock`, `uv sync --locked --all-packages` for everything and plain `uv sync --locked` for the reviewer alone. — local file `/Users/emrec/Projects/playground/adk_review/pyproject.toml`

`uv run`, installation and storage on Windows

- `uv run` on Windows supports legacy setuptools scripts "with the `.ps1`, `.cmd`, and `.bat` extensions", looking them up "in that order"; "On Windows ... uv ignores Ctrl-C events, deferring handling to the child process so it can exit cleanly"; dotenv files load with `--env-file` or `UV_ENV_FILE`. — [uv running commands](https://docs.astral.sh/uv/concepts/projects/run/); [uv configuration files](https://docs.astral.sh/uv/concepts/configuration-files/)
- Install on Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`, `winget install --id=astral-sh.uv -e`, `scoop install main/uv`, `pipx install uv`, `pip install uv`; a specific version via `https://astral.sh/uv/0.13.9/install.ps1`. macOS: `curl -LsSf https://astral.sh/uv/install.sh | sh`, `brew install uv`. The standalone installer puts `uv.exe`, `uvx.exe`, `uvw.exe` in `$HOME\.local\bin` (Windows) and `uv`, `uvx` in `~/.local/bin` (macOS); `uv self update` works only for standalone installs. — [uv installation](https://docs.astral.sh/uv/getting-started/installation/)
- uv storage follows XDG conventions on Linux and macOS and Known Folders on Windows: cache `%LOCALAPPDATA%\uv\cache`, data `%APPDATA%\uv\data`, config `%APPDATA%\uv`. — [uv storage reference](https://docs.astral.sh/uv/reference/storage/)
- uv-managed Python on Windows is registered per PEP 514 and selectable with the `py` launcher. Independently of uv, python.org's recommended Windows route is the Python install manager (`winget install 9NQ7512CXL7T -e --accept-package-agreements --disable-interactivity`, then `py install 3.14`); the traditional full installer "is deprecated since 3.14 and will not be produced for Python 3.16 or later". — [uv Python versions](https://docs.astral.sh/uv/concepts/python-versions/); [Using Python on Windows](https://docs.python.org/3.14/using/windows.html)
- uv 0.13.0 fixed "overlong wheel cache lock filenames on Windows". — [uv CHANGELOG 0.13.0](https://github.com/astral-sh/uv/blob/main/CHANGELOG.md)

### Inferences
- How the cooldown behaves in practice: the span is stored, the cutoff is computed at each new resolution (`uv lock` after an edit, `--upgrade`, `--upgrade-package`), locked versions are kept as long as they stay inside the window (they only get older, so they do), and `uv sync --locked` never needs the clock. adk_review's comment "The lock records the span, not a date, so `uv sync --locked` holds day after day" is accurate.
- `required-version = ">=0.12"` is a safe floor; the span sentinel dates from 0.11.8, so that is the technical minimum. A uv older than 0.11.8 would read the sentinel year-1 timestamp as the real cutoff.
- Three ways the cooldown can be bypassed: (a) a `==` pin younger than the span (fails loudly); (b) an `exclude-newer-package` exemption left in place (silent; review in every upgrade pull request); (c) any install that reads no lock: `uv tool install`, `uvx`, `pip install`, pre-commit hook environments. For (c): exact pins in `[project.dependencies]` for the packages that matter, `--exclude-newer P3D --constraints <export>` in the documented install command, and optionally a user-level `uv.toml` with `exclude-newer = "P3D"` (the only configuration `uv tool` reads). pip has no equivalent to hand over, so a pip install is protected only by the exact pins.
- Exempting one package does not exempt its dependencies. If a new ADK needs a dependency younger than three days, each needs its own temporary exemption; waiting is simpler.
- An absolute timestamp in `exclude-newer-package` (for example the release time plus a minute) documents itself and expires naturally; `false` is permanent until removed.
- `.python-version` (`3.14`) and `requires-python = ">=3.14,<3.15"` are both needed: the first steers project commands now that uv defaults to 3.15, the second is the only thing `uv tool install` and pip honour.
- OS-specific dependencies are best expressed as PEP 508 markers in `pyproject.toml` (for example `; sys_platform != 'win32'`); the universal lock keeps both branches. Adding Windows ARM64 to `required-environments` would not catch LiteLLM (it has an sdist), so document `UV_PYTHON_ARCH=x86_64` for those machines instead.
- With `link-mode` defaulting to `hardlink` on Windows, a project on a different drive from `%LOCALAPPDATA%\uv\cache` cannot be hard-linked and uv falls back to copying (slower, more disk); this is an inference from the link-mode description, not a tested fact.

Verdicts on the owner documents' claims

| Claim | Verdict |
|---|---|
| `exclude-newer = "P3D"` is valid `[tool.uv]` syntax | Confirmed (docs and local test) |
| `[tool.uv] required-version = ">=0.12"` | Valid; technically 0.11.8 is the first version with the span form |
| "`uv tool install` ignores root `uv.lock` & `[tool.uv]`" | Confirmed for configuration by uv's docs ("local configuration files will be ignored"); the docs describe tools as isolated from the project and do not mention `uv.lock` at all |
| `uv export --frozen --no-hashes --no-dev --no-emit-project` + `uv tool install --exclude-newer P3D --constraints ...`; `uv run --no-project` in Makefile helpers | All flags exist in 0.13.9 |
| `requires-python = ">=3.14,<3.15"`, `.python-version` = 3.14, `uv python pin 3.14` | Sound, and necessary since uv 0.13.0 defaults to 3.15 |
| `uv 0.13.9`, `hatchling 1.33.0` are current | Confirmed (2026-11-17 and 2026-10-28) |
| `google-adk==2.15.0` + `litellm==1.110.2` + `ruff==0.17.6` + `pyrefly==1.5.0` pinned together with `exclude-newer = "P3D"` | Not lockable on the day written; see section 4 |

### Gaps
- The docs do not state whether `uv tool upgrade` keeps an `--exclude-newer` given at install time (only "retain the settings provided").
- Not tested: a span-form lock read by uv older than 0.11.8.
- Whether uv 0.13.9 has a built-in task runner was not checked.
- Must be tested on real Windows: `uv sync --locked` with cache and project on different drives; `uv run` from PowerShell 5.1, PowerShell 7 and `cmd.exe`; `uv tool install` placing `.exe` shims on `PATH`; installation via winget on a locked-down corporate machine.

## 4. How can the project stay on the latest versions safely (upgrade commands, Dependabot/Renovate, cooldowns, caps)?

### Takeaway
Under the owner's rule, "latest" on 2026-11-20 was `google-adk` 2.14.1, not 2.15.0, and the owner documents' "latest version baseline" lists at least ten releases the three-day cooldown refused that day, including four `==` pins that could not be locked. Dependabot (ecosystem `uv`, `cooldown.default-days: 3`) and Renovate (`minimumReleaseAge`) can both mirror uv's delay, which uv's docs recommend.

### Cited Findings

Why the cooldown exists

- LiteLLM 1.107.0 was a malicious release: seven wheels uploaded 2026-10-21 11:39:51 to 11:40:13 UTC and removed by 13:23 UTC; Docker tags `v1.107.0`, `latest`, `main-latest`, `main-stable` were compromised 11:46:56 to 14:20 UTC. It "contained compiled malware which steals credentials and loads remote-code execution tools". LiteLLM states "All previous versions are safe" and recommends pinning `1.106.2` or "any explicit version published prior to now". The post does not declare later releases audited. — [LiteLLM security incident, Oct 21 2026](https://docs.litellm.ai/blog/security-incident-oct-21-2026)
- The malicious release was caught "within 20 minutes of publication" and "The compromised artifacts were live for about two hours before they were pulled." — [LiteLLM attack-chain post](https://docs.litellm.ai/blog/security-incident-oct-21-2026-attack-chain)
- PyPI lists no `1.107.0` final today (only `1.107.0.dev*` and `rc*`); `1.106.2` was uploaded 2026-10-21T10:44Z and `1.106.3` on 2026-10-24. — [litellm on PyPI JSON](https://pypi.org/pypi/litellm/json)
- ADK 2.14.1 and 2.15.0 both cap the optional LiteLLM dependency at `litellm>=1.84,<1.106.3`, with the comment "1.107.0 was a compromised release; raise only after checking the new release is clean." — [google-adk 2.15.0 pyproject.toml](https://github.com/google/adk-python/blob/v2.15.0/pyproject.toml); [PyPI JSON 2.14.1](https://pypi.org/pypi/google-adk/2.14.1/json)
- adk_review depends on `google-adk==2.14.1` without extras and on `litellm==1.106.2` directly, and tells Dependabot to ignore `litellm` `>=1.106.3`. Its comments also cite LiteLLM 1.82.7/1.82.8 ("shipped a credential stealer on PyPI for 2 h 32 min"). — local files `/Users/emrec/Projects/playground/adk_review/pyproject.toml` and `/Users/emrec/Projects/playground/adk_review/.github/dependabot.yml`

What "latest under P3D" meant on 2026-11-20 (cutoff 2026-11-17T22:49Z)

- `google-adk`: 2.15.0 excluded; 2.14.1 (2026-11-12) was the newest eligible. 2.15.0 clears the cooldown about 2026-11-23 00:31 UTC. Recent cadence: 2.12.0 (10-13), 2.13.0 (10-23), 2.14.0 (11-07), 2.14.1 (11-12), 2.15.0 (11-20). — [google-adk on PyPI JSON](https://pypi.org/pypi/google-adk/json)
- `litellm`: 1.110.2 (2026-11-20T04:05Z) excluded, as were 1.110.0 (11-18), 1.110.1 (11-19), 1.109.2 (11-19) and 1.109.3 (11-20); the newest eligible stable release by version number was 1.109.1 (2026-11-12); inside ADK's cap the newest is 1.106.2. LiteLLM published 14 releases in its 1.108 line (1.108.0 to 1.108.13) between 2026-11-04 and 2026-11-20 and patch releases 1.106.3 to 1.106.12 between 2026-10-24 and 2026-11-20. 1.110.2 clears the cooldown about 2026-11-23 04:06 UTC. — [litellm on PyPI JSON](https://pypi.org/pypi/litellm/json)
- Newest on PyPI versus selected under P3D [local test]: `fastapi` 0.165.0 (2026-11-18) vs 0.163.2; `pydantic` 2.14.4 (11-19) vs 2.14.3; `ruff` 0.17.6 (11-19) vs 0.17.5; `pyrefly` 1.5.0 (11-19) vs 1.4.1; `import-linter` 2.17 (11-18) vs 2.16; `hypothesis` 6.170.17 (11-20) vs 6.170.15; `typer` 0.29.2 (11-18) vs 0.29.1; `ty` 0.0.107 (11-18) vs 0.0.105; `authlib` 1.9.10 (11-20) vs 1.9.9. — [ruff](https://pypi.org/pypi/ruff/json); [pyrefly](https://pypi.org/pypi/pyrefly/json); [import-linter](https://pypi.org/pypi/import-linter/json); [pydantic](https://pypi.org/pypi/pydantic/json); [fastapi](https://pypi.org/pypi/fastapi/json); [hypothesis](https://pypi.org/pypi/hypothesis/json); [typer](https://pypi.org/pypi/typer/json); [ty](https://pypi.org/pypi/ty/json)
- Newest on PyPI on 2026-11-20 and already three days old: `uv` 0.13.9 (2026-11-17, borderline), `a2a-sdk` 1.3.1 (2026-11-17, borderline), `hatchling` 1.33.0, `truststore` 0.10.5, `python-dotenv` 1.2.4, `mcp` 2.3.0, `pytest` 9.2.0, `pytest-asyncio` 1.5.0, `mutmut` 3.8.1, `cosmic-ray` 8.9.0, `textual` 8.2.8, `mypy` 2.4.1, `sqlalchemy` 2.1.9, `uvicorn` 0.54.0, `pyyaml` 6.0.3, `aiosqlite` 0.22.1. `google-genai` 3.6.1 (2026-11-18) is both too young and outside ADK's `<3` cap. — PyPI JSON per package, for example [uv](https://pypi.org/pypi/uv/json), [mcp](https://pypi.org/pypi/mcp/json), [pytest-asyncio](https://pypi.org/pypi/pytest-asyncio/json), [a2a-sdk](https://pypi.org/pypi/a2a-sdk/json)

Upgrade commands

- Locked versions are preferred and stay unchanged "unless an upgrade is explicitly requested with `--upgrade`"; a new resolution recomputes the relative cutoff. `uv lock --upgrade-package <name>` and `--upgrade-group` exist in 0.13.9. — [uv resolution concepts](https://docs.astral.sh/uv/concepts/resolution/)
- `uv tree --outdated` recomputes relative `exclude-newer` values (since 0.11.4), so it reports what the cooldown allows; `uv tool list --outdated` respects `--exclude-newer`. — [uv changelog 0.11.x](https://github.com/astral-sh/uv/blob/main/changelogs/0.11.x.md)

Dependabot and Renovate

- Dependabot supports `package-ecosystem: "uv"` and updates `uv.lock`; uv's docs note "there are some use cases that are not yet working" (tracked in astral-sh/uv#2512) and recommend, when `exclude-newer` is used, also setting Dependabot's `cooldown` so it does not open pull requests uv "would not be able to lock" (their example: `cooldown: default-days: 7` for a one-week `exclude-newer`). — [uv Dependabot guide](https://docs.astral.sh/uv/guides/integration/dependabot/)
- Dependabot `cooldown` keys: `default-days`, `semver-major-days`, `semver-minor-days`, `semver-patch-days`, `include`, `exclude` (up to 150 entries each; `exclude` wins). `uv` is listed among the ecosystems supporting both `default-days` and the semver-specific keys. Cooldown is "only available for *version* updates, not *security* updates". — [Dependabot options reference](https://docs.github.com/en/code-security/dependabot/working-with-dependabot/dependabot-options-reference)
- Renovate detects uv from `uv.lock`, updates `pyproject.toml` and `uv.lock`, supports `lockFileMaintenance`; uv's docs recommend "to also set the equivalent minimumReleaseAge option in Renovate" (example rule `matchDatasources: ["pypi"]`, `minimumReleaseAge: "1 week"`). Renovate does not update the lock file of a PEP 723 inline script. — [uv Renovate guide](https://docs.astral.sh/uv/guides/integration/renovate/)
- Renovate's own description: `minimumReleaseAge` exists "to provide a means to reduce risk supply chain security risks"; while a release is younger than the setting "Renovate adds a "pending" status check to that update's branch"; security updates follow the separate `vulnerabilityAlerts` setting ("null by default"); it depends on the registry providing a release timestamp. — [Renovate minimum release age](https://github.com/renovatebot/renovate/blob/main/docs/usage/key-concepts/minimum-release-age.md)
- adk_review's `.github/dependabot.yml`: ecosystem `uv`, weekly, `cooldown.default-days: 3`, one group for everything except `google-adk` and `litellm` (each gets its own pull request), `ignore` for `litellm` `>=1.106.3`, and a second entry for `github-actions` with the same cooldown. Its header records that packages named only in the lock are in no pull request ("14 such stood behind what the wait admits, and `uv lock --upgrade` moves them, by hand"). — local file `/Users/emrec/Projects/playground/adk_review/.github/dependabot.yml`

### Inferences
- A three-day cooldown would have excluded LiteLLM 1.107.0 with a wide margin (detected in 20 minutes, removed in about two hours), and likewise the earlier 1.82.7/1.82.8 incident as adk_review describes it. It does not help against a compromise that stays undetected for more than three days, nor against installs that read no lock.
- The "newest release at least three days old" for the framework's two critical pins on 2026-11-20/21 is `google-adk` 2.14.1 and, within ADK's tested range, `litellm` 1.106.2: exactly adk_review's pins. Moving to 2.15.0 is allowed by the policy from 2026-11-23.
- `litellm==1.110.2` (or any release above 1.106.2) is outside the range ADK tests. Depending on `google-adk` without the `extensions` extra makes uv accept the combination, but nothing upstream vouches for it; adk_review's rule ("a bump lands only measured live on both arms") is the compensating control. The cap was set for a security reason that LiteLLM has not formally closed, so raising it is the owner's risk decision. If the `extensions` extra were ever requested, the cap would become a hard resolver conflict; the escape hatch would be `override-dependencies`, which silences ADK's own safety bound and should be a recorded decision.
- Routine for taking a new release: (1) let Dependabot or a scheduled `uv lock --upgrade` propose it once it is three days old; (2) read the release notes and the vendor's advisories; (3) `uv lock --upgrade-package <name>` (or edit the `==` pin and run `uv lock`); (4) run Windows and macOS CI; (5) for ADK and LiteLLM repeat the live measurements; (6) merge. For an urgent security fix, add a dated `exclude-newer-package` entry in the same pull request and remove it at the next routine upgrade.
- Dependabot's cooldown counts days and uv's counts 72 hours from the moment of resolution, so a pull request opened right at the boundary can still fail to lock; it succeeds on the next run.
- Dependabot security updates ignore its cooldown, so a security pull request may propose a version uv refuses to lock; that is the case for a temporary exemption.
- Transitive packages need a scheduled `uv lock --upgrade` under the cooldown, because Dependabot's groups cover only what `pyproject.toml` names (adk_review's own finding).

Verdicts on the owner documents' claims

| Claim | Verdict |
|---|---|
| "Verified Latest Library Version Baseline (2026-11-20)" lists `google-adk` 2.15.0, `litellm` 1.110.2, `pydantic` 2.14.4, `fastapi` 0.165.0, `ruff` 0.17.6, `pyrefly` 1.5.0, `import-linter` 2.17, `hypothesis` 6.170.17, `typer` 0.29.2, `ty` 0.0.107 | Each is the newest on PyPI, but each was 0 to 2 days old on 2026-11-20 and so is not "latest" under the owner's three-day rule |
| `google-adk==2.15.0` + `litellm==1.110.2` + `ruff==0.17.6` + `pyrefly==1.5.0` pinned beside `exclude-newer = "P3D"` | Wrong as a working configuration on that date: `uv lock` fails (demonstrated for `google-adk`). Lockable from 2026-11-22 (`ruff`, `pyrefly`) and 2026-11-23 (`google-adk`, `litellm`) |
| "Pin `ruff==0.17.6` & `pyrefly==1.5.0` matching `adk_review`" | Wrong: adk_review pins `ruff==0.17.5` and `pyrefly==1.4.1` (and `google-adk==2.14.1`, `litellm==1.106.2`) |
| ADK caps LiteLLM below 1.106.3 because of the 1.107.0 compromise | Confirmed (ADK comment and LiteLLM's incident post) |
| `mcp` 2.3.0, `pytest` 9.2.0, `pytest-asyncio` 1.5.0, `mutmut` 3.8.1, `cosmic-ray` 8.9.0, `textual` 8.2.8, `truststore` 0.10.5, `python-dotenv` 1.2.4, `uvicorn` 0.54.0, `sqlalchemy` 2.1.9 are latest | Confirmed, and old enough for the cooldown |

### Gaps
- Not documented anywhere found: whether Dependabot's uv updater honours `[tool.uv] exclude-newer` when it regenerates `uv.lock`; uv's guide only recommends aligning the two settings.
- No PyPI-authored recommendation of cooldowns was located (adk_review attributes one to "the registry's own advice"); unverified.
- Whether LiteLLM releases after 1.107.0 are clean cannot be established from public sources.
- `ag-ui-adk`, `ag-ui-protocol` and `pyright` versions in the owner's table were not re-checked.

## 5. Which cross-platform task runner, and how should the GitHub Actions matrix be set up?

### Takeaway
Plain `uv run ...` commands are already the working interface in adk_review (the `Makefile` only wraps them, and CI on Windows, Linux and macOS repeats them one per step), so no task runner is required on Windows; `poethepoet` is the lightest optional addition, while `just` needs a shell setting on Windows and has no native Windows ARM64 wheel. The matrix should be `windows-latest`, `macos-latest`, `ubuntu-latest` with `setup-uv` pinned by commit and a pinned uv version.

### Cited Findings
- adk_review's `Makefile` targets are single `uv run`/`uv sync` commands (`uv sync --locked --all-packages`, `uv run pytest -q`, `uv run ruff check . && uv run ruff format --check .`, `uv run pyrefly check`); two helper variables call `uv run --no-project python -c ...` because "a plain `uv run`, read on every make, synced the environment and rewrote a stale uv.lock". — local file `/Users/emrec/Projects/playground/adk_review/Makefile`
- adk_review's `.github/workflows/ci.yml`: `matrix.os: [windows-latest, ubuntu-latest, macos-latest]`, `fail-fast: false`, `timeout-minutes: 20`, `permissions: contents: read`, `actions/checkout` pinned by commit (v7.0.1) with `persist-credentials: false`, `astral-sh/setup-uv` pinned by commit (v10.3.3) with `version: "0.13.6"` (comment: "pinned: read as a floor, `required-version` took the newest uv every run"), then one command per step: `git --version`, `uv sync --locked --all-packages`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyrefly check`, `uv run pytest -q`. `azure-pipelines.yml` mirrors it with `python -m pip install uv==0.13.6`. — local files `/Users/emrec/Projects/playground/adk_review/.github/workflows/ci.yml` and `/Users/emrec/Projects/playground/adk_review/azure-pipelines.yml`
- GitHub-hosted runner labels (README read 2026-11-21): `windows-latest` = Windows Server 2025 x64 (`windows-2025`, `windows-2025-vs2026`); `windows-2022`; `windows-11-arm` = Windows 11 Arm64; `macos-latest` = macOS 26 Arm64 (`macos-26`); `macos-15` = macOS 15 Arm64; `macos-15-intel`/`macos-26-intel` for x64; `ubuntu-latest` = Ubuntu 24.04. The `-latest` migration "is gradual and happens over 1-2 months". — [actions/runner-images README](https://github.com/actions/runner-images/blob/main/README.md)
- Default `run` shell: "`pwsh` ... This is the default shell used on Windows"; on Linux and macOS the default is `bash -e {0}`; `shell: bash` on Windows uses "the bash shell included with Git for Windows". — [GitHub Actions workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
- "Beginning in PowerShell 7, PowerShell implements the `&&` and `||` operators". — [about_Pipeline_Chain_Operators](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_pipeline_chain_operators)
- uv's GitHub guide: pin the action by commit (`astral-sh/setup-uv@c771a70e... # v9.0.0`), pin uv with `version: "0.13.9"` (called best practice), `uv python install` "will respect the Python version pinned in the project", or `actions/setup-python` with `python-version-file: ".python-version"`; `uv sync --locked --all-extras --dev`; `enable-cache: true`; `uv cache prune --ci`. Its examples use `ubuntu-latest` only. — [uv GitHub Actions guide](https://docs.astral.sh/uv/guides/integration/github/)
- `setup-uv` README (main): examples use `astral-sh/setup-uv@1db35dd8... # v10.4.0`; inputs include `version`, `version-file`, `python-version` (sets `UV_PYTHON`, overriding `pyproject.toml` and `.python-version`), `python-arch` ("Use `python-arch` to set `UV_PYTHON_ARCH` for the rest of the job"), `activate-environment`, `enable-cache: "auto"`, `cache-dependency-glob`, `prune-cache`. Sources conflict on the current major: uv's guide shows v9.0.0, the action's README v10.4.0, adk_review uses v10.3.3, ADK's own CI uses v7. — [setup-uv README](https://github.com/astral-sh/setup-uv/blob/main/README.md); [uv GitHub Actions guide](https://docs.astral.sh/uv/guides/integration/github/); [ADK continuous-integration.yml](https://github.com/google/adk-python/blob/v2.15.0/.github/workflows/continuous-integration.yml)
- `poethepoet` 0.49.0: pure-Python wheel, Python 3.14 classifier, `Operating System :: OS Independent`, depends only on `pyyaml`; tasks are declared in `pyproject.toml`, run inside uv's virtualenv, can be commands "even without a shell", sequences or parallel groups; its README marks `shell` tasks as "(posix) shell based". — [poethepoet on PyPI JSON](https://pypi.org/pypi/poethepoet/json); [poethepoet README](https://github.com/nat-n/poethepoet/blob/main/README.md)
- `just`: "On Windows, `just` works with the `sh` provided by Git for Windows"; otherwise set `set shell := ["powershell.exe", "-c"]` or `["cmd.exe", "/c"]`. The PyPI distribution `rust-just` 1.59.0 has wheels for `win_amd64`, `win32` and macOS but none for `win_arm64`. — [just README](https://github.com/casey/just/blob/master/README.md); [rust-just on PyPI JSON](https://pypi.org/pypi/rust-just/json)

### Inferences
- Recommended interface: document plain commands (`uv sync --locked --all-packages`, `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyrefly check`, `uv run lint-imports`) as the contract; keep `make` as an optional POSIX wrapper. If a single entry point is wanted, a `[tool.poe.tasks]` table with `cmd`/`sequence` tasks (no `shell` tasks) gives `uv run poe ci` identically on every OS with one small pure-Python dev dependency. `just` adds a non-Python binary, a per-OS shell setting and no native Windows ARM64 wheel, for little gain here.
- The owner document's PowerShell line `uv run ruff check .; uv run ruff format --check .; uv run pyrefly check; uv run lint-imports; uv run pytest -q` is not equivalent to `make ci`: `;` runs every command regardless of failure, so a lint failure is not a failed run. `&&` works only in PowerShell 7+, not in Windows PowerShell 5.1 (the version preinstalled on Windows). One command per line, or a task runner, avoids the difference.
- Matrix sketch assembled from the cited pieces (not run):

```yaml
jobs:
  test:
    strategy:
      fail-fast: false
      matrix:
        os: [windows-latest, macos-latest, ubuntu-latest]
    runs-on: ${{ matrix.os }}
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@<commit>        # pinned by commit
        with: { persist-credentials: false }
      - uses: astral-sh/setup-uv@<commit>      # pinned by commit
        with:
          version: "0.13.9"                    # exact uv, kept current by Dependabot
          enable-cache: true
      - run: uv sync --locked --all-packages   # .python-version selects 3.14
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run pyrefly check
      - run: uv run lint-imports
      - run: uv run pytest -q
```

- Single-command `run:` steps behave the same under `pwsh` and `bash`. An optional `windows-11-arm` job with `python-arch: x86_64` would cover Windows ARM64 users; without that input the job would attempt native ARM64 source builds.
- `macos-latest` is Apple silicon; Intel Macs are covered only by adding `macos-15-intel`, and `cryptography` no longer publishes x86_64 macOS wheels in its current line (its changelog: "Support for `x86_64` macOS has been removed"), so Intel Mac support would need a held-back `cryptography`. — [cryptography CHANGELOG](https://github.com/pyca/cryptography/blob/main/CHANGELOG.rst)

### Gaps
- Whether uv 0.13.9 ships a built-in task runner was not checked.
- The exact `cryptography` version that dropped x86_64 macOS wheels was not pinned down.
- CI behaviour was not executed; adk_review's CI results on `windows-latest` were not visible to the researcher.

## 6. Which general Windows versus macOS differences must a file-and-subprocess-heavy tool handle?

### Takeaway
The owner's reference project already implements the main defences (LF-only `.gitattributes`, explicit UTF-8, full-path executable lookup that excludes the current directory, `taskkill /F /T` tree kill, cleanup-tolerant temp directories, per-OS config directories), and each is backed by the Python and Git documentation. The open design points are reserved-name and case handling in the write policy, read-only files and locks when removing worktrees, and long paths.

### Cited Findings

Line endings and hashing

- With `text=auto`, text files are "normalized to LF in the index"; the `eol` attribute "has effect only if `text` or `text=auto` is set"; `eol=lf` "uses the same line endings in the working directory as in the index when the file is checked out"; if `eol` is unspecified and `text` is set, endings follow `core.autocrlf`/`core.eol`, and "the default is `eol=crlf` on Windows and `eol=lf` on all other platforms". — [gitattributes](https://git-scm.com/docs/gitattributes)
- `core.autocrlf`: `true` equals `text=auto` on all files with `core.eol=crlf`; `input` means "no output conversion is performed". — [git-config](https://git-scm.com/docs/git-config)
- adk_review ships `* text=auto eol=lf` ("Every text file is LF in every checkout, whatever core.autocrlf says on the machine"), writes files with `newline="\n"` or `newline=""`, replaces `\r\n` with `\n` before splitting, and avoids `str.splitlines` because it also breaks at form feed and U+2028. — local files `/Users/emrec/Projects/playground/adk_review/.gitattributes`, `adk_review/core/text.py`, `adk_review/collect/ruff.py`
- A framework layer can itself alter line endings: ADK's `FileArtifactService` did so through text-mode I/O until issue #7914. — [adk-python issue #7914](https://github.com/google/adk-python/issues/7914)

Paths: separators, case, reserved names, drives, links, length

- `os.path.isabs`: "on Windows that it begins with two (back)slashes, or a drive letter, colon, and (back)slash together"; "Changed in version 3.13: On Windows, returns `False` if the given path starts with exactly one (back)slash." — [os.path](https://docs.python.org/3.14/library/os.path.html)
- `os.path.isreserved(path)` (added in 3.13, "Availability: Windows"): reserved names "include those that end with a space or dot; those that contain colons (i.e. file streams such as "name:stream"), wildcard characters (i.e. `'*?"<>'`), pipe, or ASCII control characters; as well as DOS device names such as "NUL", "CON", "CONIN$", "CONOUT$", "AUX", "PRN", "COM1", and "LPT1"". The module docs note that `ntpath` can be imported directly to handle Windows-format paths on any system. — [os.path](https://docs.python.org/3.14/library/os.path.html)
- [local test, CPython 3.14.10 on macOS] `os.path.isreserved` does not exist on macOS (`hasattr(os.path, "isreserved")` is `False`), while `ntpath.isreserved()` is importable and returned `True` for `CON.txt`, `con`, `NUL`, `COM1.md`, `aux.tar.gz`, `LPT1`, `name.`, `name ` and `CONIN$`, and `False` for `ok.md`. The check used in the owner's skeleton (`part.split(".", 1)[0].upper() in <device names>`) returned `False` for `name.`, `name ` and `CONIN$`. `ntpath.isreserved("a:b")` returned `False` because a single letter plus colon is parsed as a drive prefix. — function documented in [os.path](https://docs.python.org/3.14/library/os.path.html)
- [local test, CPython 3.14.10 on macOS] For a symlink `link -> real`, `(root / "link").is_symlink()` is `True` but `(root / "link").resolve().is_symlink()` is `False`, and `os.path.isjunction()` of the resolved path is `False`. — behaviour documented in [pathlib](https://docs.python.org/3.14/library/pathlib.html)
- `os.path.isjunction(path)` (added in 3.12) returns `True` for a junction and "Always return `False` if junctions are not supported on the current platform"; `os.path.realpath`: "Changed in version 3.8: Symbolic links and junctions are now resolved on Windows." — [os.path](https://docs.python.org/3.14/library/os.path.html)
- Git: `core.ignoreCase` exists for "filesystems that are not case sensitive, like APFS, HFS+, FAT, NTFS"; `core.protectNTFS` blocks paths that "would cause problems with the NTFS filesystem, e.g. conflict with 8.3 "short" names" and "Defaults to `true` on Windows, and `false` elsewhere"; with `core.symlinks=false` "symbolic links are checked out as small plain files that contain the link text", and clone/init probe the filesystem to set it. — [git-config](https://git-scm.com/docs/git-config)
- `core.precomposeUnicode`: "This option is only used by Mac OS implementation of Git. When core.precomposeUnicode=true, Git reverts the unicode decomposition of filenames done by Mac OS." — [git-config](https://git-scm.com/docs/git-config)
- Long paths: "Windows historically has limited path lengths to 260 characters"; an administrator must "activate the "Enable Win32 long paths" group policy, or set `LongPathsEnabled` to `1`" under `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\FileSystem`; then `open()`, `os` and most path functions accept longer paths. — [Using Python on Windows](https://docs.python.org/3.14/using/windows.html)

Subprocesses: resolution, shells, killing

- "For maximum reliability, use a fully qualified path for the executable. To search for an unqualified name on `PATH`, use `shutil.which()`. On all platforms, passing `sys.executable` is the recommended way to launch the current Python interpreter again". On Windows with `shell=False`, "`cwd` does not override the current working directory and `env` cannot override the `PATH` environment variable" during the search. — [subprocess](https://docs.python.org/3.14/library/subprocess.html)
- `shutil.which` on Windows: "the current directory is prepended to the path if mode does not include `os.X_OK`. When the mode does include `os.X_OK`, the Windows API `NeedCurrentDirectoryForExePathW` will be consulted ... To avoid consulting the current working directory for executables: set the environment variable `NoDefaultCurrentDirectoryInExePath`"; `PATHEXT` is used to resolve names without an extension. — [shutil](https://docs.python.org/3.14/library/shutil.html)
- "On Windows, batch files (`*.bat` or `*.cmd`) may be launched by the operating system in a system shell regardless of the arguments passed to this library. This could result in arguments being parsed according to shell rules, but without any escaping added by Python." Since 3.12, `shell=True` on Windows resolves the shell from `%COMSPEC%` and `%SystemRoot%\System32\cmd.exe`, not the current directory. — [subprocess](https://docs.python.org/3.14/library/subprocess.html)
- `start_new_session`, `process_group` and `preexec_fn` are POSIX only. `Popen.terminate()`: "On Windows the Win32 API function `TerminateProcess()` is called"; "On Windows `kill()` is an alias for `terminate()`"; `CTRL_C_EVENT` and `CTRL_BREAK_EVENT` can be sent only to processes started with `CREATE_NEW_PROCESS_GROUP`; with `communicate(timeout=...)`, "The child process is not killed if the timeout expires". `CREATE_NO_WINDOW` is available as a creation flag. — [subprocess](https://docs.python.org/3.14/library/subprocess.html)
- adk_review resolves each executable once with `shutil.which(name, path=<absolute PATH entries only>)` after setting `NoDefaultCurrentDirectoryInExePath=1`; runs git with per-call settings `core.precomposeUnicode=false`, `core.attributesFile=os.devnull`, `core.fsmonitor=false`, `core.autocrlf=input`; on a Windows timeout runs `%SystemRoot%\System32\taskkill.exe /F /T /PID <pid>`; finds console scripts at `sysconfig.get_path("scripts")` with `.exe` on Windows. — local files `/Users/emrec/Projects/playground/adk_review/adk_review/collect/git.py`, `collect/ruff.py`, `collect/pyrefly.py`
- `core.fsmonitor`: "If set to `true`, enable the built-in file system monitor daemon for this working directory"; `core.attributesFile` names an extra attributes file, defaulting to `$XDG_CONFIG_HOME/git/attributes` or `$HOME/.config/git/attributes`. — [git-config](https://git-scm.com/docs/git-config)

Temporary files, locks, cleanup

- `TemporaryDirectory(ignore_cleanup_errors=True)` (parameter added in 3.10): errors during cleanup "(such as a `PermissionError` removing open files on Windows) will be ignored, and the remaining removable items deleted on a "best-effort" basis"; `delete=` was added in 3.12. `NamedTemporaryFile` gained `delete_on_close` in 3.12 with Windows-specific reopening rules. `shutil.rmtree` gained `onexc` in 3.12. — [tempfile](https://docs.python.org/3.14/library/tempfile.html); [shutil](https://docs.python.org/3.14/library/shutil.html)
- A real instance in ADK: `adk deploy` failed with `[WinError 5]` while cleaning read-only files inside `.git` on Windows. — [adk-python issue #4635](https://github.com/google/adk-python/issues/4635)

Encoding and console

- On 3.14, Windows "still uses legacy encodings for the system encoding (the ANSI Code Page)"; UTF-8 mode is enabled with `-X utf8` or `PYTHONUTF8=1`; console I/O and the filesystem encoding already use UTF-8. UTF-8 mode by default arrives in 3.15. — [Using Python on Windows](https://docs.python.org/3.14/using/windows.html); [PEP 686](https://peps.python.org/pep-0686/)
- adk_review calls `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` at each CLI entry point and passes `encoding="utf-8"` to every `read_text`, `write_text` and `subprocess.run`. — local files under `/Users/emrec/Projects/playground/adk_review/adk_review/` (`review.py`, `push.py`, `login.py`, `commit.py`)

Config and data locations

- uv itself uses XDG conventions on Linux and macOS and Known Folders on Windows (`%APPDATA%` for config and data, `%LOCALAPPDATA%` for cache). adk_review's TUI uses `%APPDATA%` for config and `%LOCALAPPDATA%` for state on Windows, `$XDG_CONFIG_HOME` or `~/.config` and `$XDG_STATE_HOME` or `~/.local/state` elsewhere, including macOS. — [uv storage reference](https://docs.astral.sh/uv/reference/storage/); local file `/Users/emrec/Projects/playground/adk_review/tui/tui/config.py`

Git worktrees

- `git worktree remove`: "Only clean worktrees (no untracked files and no modification in tracked files) can be removed. Unclean worktrees or ones with submodules can be removed with `--force`." Linked worktrees use absolute paths by default (`--relative-paths` / `worktree.useRelativePaths` switch to relative); `git worktree prune` and `repair` handle deleted or moved trees; `lock` protects a worktree from pruning. The page contains no Windows-specific section. — [git-worktree](https://git-scm.com/docs/git-worktree)

Event loop

- On Windows no event loop supports `loop.add_signal_handler()`; subprocesses need the default `ProactorEventLoop`. — [asyncio Platform Support](https://docs.python.org/3.14/library/asyncio-platforms.html)

### Inferences
- Stable content hashing: hash bytes after normalising CRLF to LF (and decide explicitly about a lone CR and a UTF-8 BOM), never the result of a text-mode read; `.gitattributes` protects checkouts but not files a user's editor or an agent writes with CRLF. Read and write spec files in binary or with `newline=""`.
- The write-policy skeleton in the owner's report has four weaknesses on Windows and macOS: (1) it tests `is_symlink()` and `isjunction()` on a path that was already passed through `.resolve()`, which follows symlinks and junctions, so those two tests can never fire (measured for symlinks on macOS; documented for junctions on Windows) and only the `is_relative_to` containment check is effective (that check does stop escapes); (2) its reserved-name test (`part.split(".", 1)[0].upper() in _WIN_RESERVED`) misses names ending in a space or dot and `CONIN$`/`CONOUT$` (measured), which `ntpath.isreserved()` covers on Python 3.13+; because `os.path.isreserved` exists only on Windows, code that must also reject these names on macOS has to call `ntpath.isreserved()` explicitly; (3) `getattr(os.path, "isjunction", ...)` is unnecessary on 3.14; (4) rules keyed on a directory name (`"checklists" in parts`) compare case-sensitively, while NTFS and default APFS do not, so `Checklists/` bypasses the rule (and on NTFS an 8.3 short name could alias it). ADK's own `FileArtifactService` uses `casefold()` for this reason.
- Process-tree kill on Windows needs its own mechanism: `Popen.kill()` ends only the direct child. `taskkill /F /T /PID` (adk_review, and ADK's dev server without `/F` first) is the documented-in-practice approach; starting the child with `CREATE_NEW_PROCESS_GROUP` additionally allows a polite `CTRL_BREAK_EVENT` first. After the kill, the reader must still drain or abandon the pipes, as ADK's own code shows.
- Tools shipped as `.cmd`/`.bat` shims (for example `npx`, `npm`) are run through `cmd.exe` even with `shell=False`, so arguments from an agent or a spec must never be passed to them unescaped. `git.exe`, and uv-installed console scripts (`ruff.exe`, `pytest.exe`), are real executables and do not have this problem.
- `core.precomposeUnicode=false` is a no-op on Windows by Git's own description; it matters on macOS only. Passing `os.devnull` as `core.attributesFile` means the literal `nul` on Windows; that Git for Windows accepts it is implied by adk_review running its suite on `windows-latest`, not verified here.
- Worktrees on Windows: each worktree path adds depth (risk with the 260-character limit when `LongPathsEnabled` is off), removal can fail on read-only files under `.git` and on files held open by antivirus, an editor or a still-running child process, and untracked files (a per-worktree `.venv`) make `git worktree remove` refuse without `--force`. Kill the process tree first, then remove with retries and a read-only-clearing `onexc` handler, then `git worktree prune`. Keep worktree roots short (for example a sibling directory near the drive root).
- Signal-based shutdown code (`loop.add_signal_handler`) must have a Windows branch (`KeyboardInterrupt` / `signal.signal(SIGINT, ...)` / `SIGBREAK`).
- On macOS the default filesystem is case-insensitive but case-preserving and Unicode-normalisation-insensitive; IDs used as directory names should be restricted to lowercase ASCII, which also sidesteps Windows reserved-character rules.

Verdicts on the owner documents' claims

| Claim | Verdict |
|---|---|
| `.gitattributes` `* text=auto eol=lf` prevents CRLF checkouts regardless of `core.autocrlf` | Confirmed by gitattributes semantics |
| Settled git settings `core.autocrlf=input`, `core.fsmonitor=false`, `core.precomposeUnicode=false`, `core.attributesFile=os.devnull` | Settings exist with the described meaning; adk_review uses exactly these; `precomposeUnicode` affects macOS only; `nul` as attributes file is unverified on Windows |
| `tempfile.TemporaryDirectory(ignore_cleanup_errors=True)` for Windows locks | Confirmed (3.10+) |
| `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` at CLI start | Sound; needed mainly when stdout is redirected, since Python already writes UTF-8 to a real Windows console |
| `os.path.isjunction()` to detect NTFS junctions | Function exists (3.12+), but the skeleton calls it after `resolve()`, where it cannot fire |
| Reject Windows drives, UNC, reserved DOS names | Right goal; the hand-written reserved-name check is incomplete compared with `ntpath.isreserved()` |
| `%APPDATA%\adk-spec` vs `$XDG_CONFIG_HOME/adk-spec` | Consistent with uv's and adk_review's conventions |
| Shell-free argv subprocesses resolving full paths from absolute `PATH` entries | Matches the subprocess documentation's recommendation and adk_review's implementation |

### Gaps
- Not researched: Windows Job Objects as an alternative to `taskkill`; the privilege requirements for creating symlinks on Windows; `core.longpaths` (a Git for Windows setting absent from the upstream `git-config` page read here); Microsoft's own documentation for `taskkill`.
- Not verified from a primary source in this session: that redirected stdout on Windows uses the ANSI code page on 3.14 (the Windows guide only states console I/O is UTF-8).
- Must be tested on real Windows: hashing the same spec file checked out on Windows and macOS; `git worktree add/remove` under `.worktrees/` with Defender active and with a `.venv` inside; tree kill of `pytest` spawning children; a project path longer than 200 characters; a path containing spaces and non-ASCII characters; `git -c core.attributesFile=nul`; `CON.md`, `aux.md`, `name.` and `Checklists/` against the write policy; Ctrl-C in `uv run <cli>` from PowerShell.

## 7. Which developer tools work on native Windows?

### Takeaway
`ruff`, `pyrefly`, `ty`, `import-linter` (with `grimp`), `pytest`, `pytest-asyncio`, `hypothesis`, `poethepoet` and `mypy` all install from wheels on Windows x64, Windows ARM64 and macOS arm64 for Python 3.14. `mutmut` is POSIX-only by its own documentation. `cosmic-ray` claims Windows through a README badge but tests only Linux up to Python 3.13 and needs a source build of one dependency.

### Cited Findings
- `mutmut` README: "Mutmut must be run on a system with `fork` support. This means that if you want to run on windows, you must run inside WSL."; on process isolation, "Both strategies require `os.fork`, so they are POSIX-only."; on macOS, "`setproctitle` uses CoreFoundation APIs on macOS that are not fork-safe, causing segfaults in child processes. By default, mutmut automatically disables `setproctitle` on macOS". — [mutmut README](https://github.com/boxed/mutmut/blob/main/README.rst)
- `mutmut` 3.8.1 (2026-10-28; classifiers 3.11 to 3.15) requires `libcst>=1.9.0`, `setproctitle>=1.3.7`, `textual>=1.0.0`, `coverage`, `pytest`, `click`. `setproctitle` 1.3.8 has `cp314` wheels for `win32`, `win_amd64` and macOS but none for `win_arm64`; a wheels-only resolve for Windows ARM64 fell back to `mutmut==0.0.6` [local test]. — [mutmut](https://pypi.org/pypi/mutmut/json); [setproctitle](https://pypi.org/pypi/setproctitle/json)
- `cosmic-ray` 8.9.0 (2026-11-10): pure wheel, `requires_python >=3.9`, classifiers stop at Python 3.13, `Operating System :: OS Independent`; requires `aiohttp`, `anybadge`, `attrs`, `click`, `decorator`, `exit-codes`, `gitpython`, `parso`, `rich`, `sqlalchemy`, `stevedore`, `toml`, `yattag`. `yattag` 1.16.1 is sdist-only, so `cosmic-ray` cannot be installed under `--no-build` on any platform [local test]. — [cosmic-ray](https://pypi.org/pypi/cosmic-ray/json); [yattag](https://pypi.org/pypi/yattag/json)
- `cosmic-ray`'s README carries a "Python version (windows) 3.9+" badge; its CI workflow runs `runs-on: ubuntu-latest` with Python 3.9 to 3.13 only. — [cosmic-ray README](https://github.com/sixty-north/cosmic-ray/blob/master/README.rst); [cosmic-ray run-tests.yml](https://github.com/sixty-north/cosmic-ray/blob/master/.github/workflows/run-tests.yml)
- `ruff` 0.17.6 and 0.17.5, `pyrefly` 1.5.0 and 1.4.1, `ty` 0.0.107 and `uv` 0.13.9 ship `py3-none` binary wheels for `win32`, `win_amd64`, `win_arm64`, `macosx_10_12_x86_64` and `macosx_11_0_arm64`. `pyrefly`'s classifiers list `Operating System :: Microsoft :: Windows`, `MacOS` and `POSIX :: Linux`; its README gives `pip install pyrefly` as the install route. — [ruff](https://pypi.org/pypi/ruff/json); [pyrefly](https://pypi.org/pypi/pyrefly/json); [ty](https://pypi.org/pypi/ty/json); [uv](https://pypi.org/pypi/uv/json); [pyrefly README](https://github.com/facebook/pyrefly/blob/main/README.md)
- `import-linter` 2.17 (pure wheel; classifiers include `Operating System :: Microsoft :: Windows` and Python 3.14) requires `grimp>=3.20`, `click>=8.2.0`, `rich>=14.2.0`; `grimp` 3.20 has `cp314` wheels for `win_amd64`, `win_arm64` and macOS arm64. — [import-linter](https://pypi.org/pypi/import-linter/json); [grimp](https://pypi.org/pypi/grimp/json)
- `pytest` 9.2.0, `pytest-asyncio` 1.5.0 (requires `pytest>=8.4`; classifiers 3.11 to 3.15) and `poethepoet` 0.49.0 are pure wheels; `hypothesis` 6.170.17 has wheels for all three targets; `mypy` 2.4.1 resolves on all three. — [pytest-asyncio](https://pypi.org/pypi/pytest-asyncio/json); [pytest](https://pypi.org/pypi/pytest/json); [hypothesis](https://pypi.org/pypi/hypothesis/json); [mypy](https://pypi.org/pypi/mypy/json)
- Wheels-only resolves under P3D succeeded on all three targets for `ruff`, `pyrefly`, `import-linter`, `pytest`, `pytest-asyncio`, `hypothesis`, `poethepoet`, `textual`, `typer`, `mypy`, `ty`, `pyright`, `pre-commit`, `hatchling`, `truststore`, `pytest-xdist`, `pytest-timeout`, `psutil` [local test]. — package metadata on [PyPI](https://pypi.org/)
- adk_review runs `ruff`, `pyrefly` and `pytest` on `windows-latest` in CI, ignores ruff rule `SIM112` because it "would upper-case Windows' own `SystemRoot` and `NoDefaultCurrentDirectoryInExePath`", sets `asyncio_mode = "strict"` and `asyncio_default_fixture_loop_scope = "function"`, and sets `[tool.pyrefly.errors] direct-abstract-base-instantiation = "ignore"` because "ADK declares LlmAgent(BaseAgent, abc.ABC) with no abstract method". — local files `/Users/emrec/Projects/playground/adk_review/pyproject.toml` and `/Users/emrec/Projects/playground/adk_review/.github/workflows/ci.yml`
- ADK's own `test` extra uses `pytest>=9,<10`, `pytest-asyncio>=0.25`, `pytest-xdist>=3.6.1`, `hypothesis>=6`; its `dev` extra pins `ruff==0.15.17`. — [google-adk 2.15.0 pyproject.toml](https://github.com/google/adk-python/blob/v2.15.0/pyproject.toml)

### Inferences

| Tool | Native Windows | Basis |
|---|---|---|
| ruff, pyrefly, ty, uv | Yes (x64 and ARM64) | binary wheels; adk_review CI on `windows-latest` for ruff and pyrefly |
| import-linter + grimp | Yes by metadata (x64 and ARM64) | Windows classifier and wheels; not run |
| pytest, pytest-asyncio, hypothesis, poethepoet, mypy | Yes | pure or wheel-covered; pytest and pytest-asyncio run in adk_review's Windows CI |
| mutmut 3.8.1 | No (WSL only) | its README |
| cosmic-ray 8.9.0 | Unverified | badge says yes; CI is Linux-only and stops at 3.13; no 3.14 classifier; needs an sdist build of `yattag` |

- The marker `"mutmut>=3.8.1; sys_platform != 'win32'"` is the right way to keep `mutmut` and `setproctitle` out of Windows environments in a universal lock. On macOS `mutmut` works but relies on `fork`, which Python 3.14 no longer uses by default for `multiprocessing` on Linux and never did on macOS; fork-unsafe test setups (event loops, threads) are the documented failure mode.
- Because `cosmic-ray` is unverified on Windows and on 3.14, the lower-risk plan is to run mutation testing only in a Linux CI job (or WSL) with `mutmut`, and treat native-Windows mutation testing as optional until a real Windows run of `cosmic-ray` on 3.14 succeeds. Adding `cosmic-ray` also adds roughly a dozen dependencies (including `aiohttp`, `sqlalchemy`, `gitpython`) to every developer environment, and blocks a `--no-build` policy.
- `pytest-asyncio` in strict mode needs no loop policy configuration on Windows; the default Proactor loop supports subprocess tests. Tests that rely on `add_signal_handler` or Unix sockets need `skipif(sys.platform == "win32")`.

Verdicts on the owner documents' claims

| Claim | Verdict |
|---|---|
| "`mutmut 3.8.1` uses POSIX `os.fork()`/`forkserver` and fails on native Windows" | Confirmed by mutmut's README (the cited issue #397 was not checked) |
| `"mutmut>=3.8.1; sys_platform != 'win32'"` | Valid and appropriate |
| "`cosmic-ray>=8.9.0` (Windows-compatible)" | Unverifiable from primary sources beyond a README badge; no 3.14 classifier; Linux-only CI |
| `import-linter 2.17`, `pytest-asyncio 1.5.0`, `ruff 0.17.6`, `pyrefly 1.5.0` exist and support 3.14 | Confirmed as existing with 3.14-installable wheels; `ruff` 0.17.6, `pyrefly` 1.5.0 and `import-linter` 2.17 were younger than three days on 2026-11-20 |
| `[tool.pyrefly.errors] direct-abstract-base-instantiation = "ignore"` is needed for `LlmAgent(...)` | Present in adk_review with that rationale; not checked against pyrefly's documentation |
| `asyncio_mode = "strict"`, `faulthandler_timeout = 300` | Present in adk_review's pytest configuration |

### Gaps
- Pyrefly's and import-linter's own platform-support pages were not read (only package metadata and pyrefly's README); import-linter's README URL returned 404.
- Must be tested on real Windows: `cosmic-ray` 8.9.0 on Python 3.14 (init, baseline, exec); `lint-imports` and `pyrefly check` on a Windows checkout; `mutmut` under WSL against a repository checked out on the Windows side (line endings and path translation).
- Whether `mutmut` 3.8.1's `forkserver` mode is reliable on macOS arm64 with asyncio-heavy tests is untested.
