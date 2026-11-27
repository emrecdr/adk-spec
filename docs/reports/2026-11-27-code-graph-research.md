# A small code graph: research and recommendations

Read-only research, 2026-11-27, by a research agent for the owner; its claims about adk-spec were checked in the code, its numbers from papers are cited, not measured here. Numbers in brackets are sources. One Graphify docs page held instructions aimed at agents; they were ignored.

## 1. What Tool A's reading gets today

From `explore.py`, `source.py` and `context.py`:

- The scout (1 call) sees the request, the profile and `tree_text`: every path up to 300 files, past that folders two levels deep with file counts.
- It names up to 12 files, 4 folders and 6 searches. A round holds up to 40,000 characters, a file up to 12,000.
- Up to 4 surveys and 2 reviews follow: 7 calls at most. Each "more" costs a survey.
- Ranges of lines are guessed (`src/app.py:120-260`), and `Source.within` finds the enclosing block from indentation.

The graph can help the scout's list, each read's precision, and the "more" rounds.

## 2. Graphify

- **Extraction.** tree-sitter, deterministic, about 40 languages. Docs, PDFs and images go through an LLM "semantic pass" [1][2].
- **Graph.** Nodes carry `id`, `label`, `source_file`, `source_location` ("L42"). Edges (`calls`, `imports`, `inherits`, …) are tagged EXTRACTED, INFERRED or AMBIGUOUS, with scores for inferred edges [2][3]. Communities: Leiden, or networkx Louvain as a fallback [1].
- **Updates.** A content hash per file; `--update` re-extracts only changed files [2].
- **God nodes.** Top N by plain degree, without file hubs, concept nodes or builtin noise such as `str` [4].
- **Surprising connections.** Cross-file edges that are not imports, scored by confidence and by crossing a file category, top-level folder or community [4].
- **Queries.** `query` walks breadth-first from nodes whose labels match the question's words, within 2,000 tokens. `path` gives a shortest path; `explain` a node and its 20 best-connected neighbours. Exit code 3 means an ambiguous name, 4 no match [5]. MCP tools include `query_graph`, `shortest_path`, `god_nodes` [1].
- **Agents.** Claude Code hooks nudge before search and Read calls [1]. Its benchmarks measure memory recall, not code-context savings [1].

**Take:** honest edge certainty (ours: resolved, or counted unresolved); degree-ranked hubs without noise; word-matched seeds with a bounded walk and a budget; an ambiguous name returns every candidate, never a pick.
**Leave:** LLM extraction (not deterministic, costs calls, secrets risk); communities (need networkx or graspologic; folders are a fair proxy); surprising connections, HTML, watch, hooks; a graph stored in the repository, which Tool B must never read.

## 3. Prior art

| Tool | Representation | Resolution | Incremental | Queried |
|---|---|---|---|---|
| Aider repo map | File graph from tree-sitter defs and call refs [6][7] | By name only. Weights ×10 mentioned, ×10 long names, ×0.1 `_private`, ×0.1 if defined in >5 files, ×50 from chat files, ×√refs [6] | Path and mtime cache in the repo [6] | A signature map, 1k tokens by default, fitted by binary search within 15% [6][8] |
| SCIP | Protobuf: documents by relative path ('/' on Windows), occurrences with 0-based ranges, symbol strings; text optional [9] | Precise, compiler-grade indexer per language [10] | Planned per file [11] | Definitions, references |
| stack-graphs | Per-file def/ref graphs, resolved by path-finding with a symbol stack [12] | Precise | Per file, reused across commits [12] | Archived 9 Sep 2025 [13] |
| universal-ctags | Flat tags: name, file, line, kind, language [14]; regex "optlib" parsers need no C [15] | None | Per file | Name lookup |
| tree-sitter tags | `@definition.*`, `@reference.*`, `@name`, `@doc` captures [16] | None | Per file | `tree-sitter tags` |
| grimp / import-linter | Module import graph with import line and `is_lazy`; can drop TYPE_CHECKING imports [17] | Module-level | `.grimp_cache` in the repo [17] | Up/downstream, shortest chain; layer and independence contracts [18] |
| pydeps | Bytecode import opcodes; needs importable modules and Graphviz [19] | Import machinery | — | Cycles |
| pyan | defines/uses from `ast`: scopes, `self`, MRO, annotations; GPL-2.0 [20] | Heuristic | — | Call graph |
| Serena | Language servers over LSP [21] | Precise | Server's | Symbol, overview, references |
| codebase-memory-mcp | tree-sitter graph, 66 languages [22] | — | — | Calls, impact: 10× fewer tokens, but 83% answer quality against 92% for an agent that reads files [22] |

Precise tools need a compiler or language server per language; cheap tools match names. Stdlib `ast` sits between.

## 4. What helps an agent choose context

- **SWE-bench** [23]: BM25 at 27,000 tokens found none of the oracle files in almost half of the instances.
- **Agentless** [24]: skeletons (headers, signatures) beat whole files for choosing functions, 58.33% against 53.67%, at about $0.02 against $0.15.
- **LocAgent** [25]: a file/class/function graph with import, invoke and inherit edges, walked through SearchEntity, TraverseGraph, RetrieveEntity. File Acc@5 94.16% against 79.56% for Agentless; function Acc@10 77.37% against 58.76%. Its 86% cost cut comes mainly from a smaller fine-tuned model.
- **RepoGraph** [26]: 1–2-hop neighbourhoods around a keyword raised SWE-bench Lite resolve rates 32.8% on average (relative), while tokens and cost rose in every setting.
- **Ranking**: Aider uses PageRank [6]; I found no published ablation. Treat its gain as unmeasured.
- **Test links** [27][28]: strict naming conventions gave 100% precision but 11% recall in one dataset; combined signals do better.

Conclusion: a graph aims the reading; it does not replace it. Skeletons are the cheapest proven win, and a multi-hop walk finds code the request never names.

## 5. More languages later

- **tree-sitter** [29]: core 0.27.0 has cp314 wheels for macOS (x86-64, arm64) and Windows (amd64, arm64), not abi3, so a new wheel for every Python minor. Grammars ship abi3 wheels of about 0.1–0.8 MB. `tree-sitter-language-pack` 1.28.0 is 2.3–2.5 MB, and its macOS wheels need macOS 15. Cost: 2–4 compiled dependencies, paired versions, name-only tags.
- **Regex, ctags-style** [15]: stdlib. JS/TS `import … from './x'` and `require('./x')` are regular enough for file-level import edges; symbols approximate.
- **A ctags binary or LSP**: an external program Tool B cannot assume. Rejected.

Proposal: v1 keeps the floor; v2 adds a stdlib regex extractor for JS/TS imports and top-level exports, marked as regex precision; tree-sitter only as an optional extra, after measurement and with the owner's consent.

## 6. Staleness and incremental rebuild

- Git gives each file's blob ID at no cost: `git ls-tree -r <commit>` for Tool B, `git ls-files -s` for the index [30]. A blob ID names exact bytes, so it is the right cache key. An mtime key, as Aider uses [6], changes on every checkout and clone.
- Per-file isolation makes caching work: stack-graphs' lesson [12]; Graphify also hashes content [2].

Proposal: split the build inside the library now, into `extract(path, text) -> FileFacts` (file-local, cacheable) and `link(facts) -> Graph` (cross-file, cheap, always recomputed). Keep both private, with no cache in v1: the worst case measured is 7.4 s. A later cache lives outside the repository, keyed by (blob ID, schema version, Python minor), because `ast` changes between minors. Tool A keys dirty files by the hash of the text it read.

## 7. Recommendations, ranked by value for effort

| # | Change | Tool A need | Effort | Rules |
|---|---|---|---|---|
| 1 | **Ranked files replace the folded tree.** Personalized PageRank over import, defines and tests edges, seeded by request words matched to name tokens (snake/camel split, case-folded), with Aider's weights. The scout sees the top N files, one reason each ("defines `Source`"). Pure Python: 30 iterations on 10k nodes, 60k edges took 0.23 s here. | Aims the first round | Low–medium | Stdlib; names and paths only; nothing on screen |
| 2 | **Read by symbol.** A qualname named by the scout or survey is looked up with `definition()` and read as `path:first-last`. | Exact, small reads; fewer "more" rounds | Low | A lookup, never a path built from model text |
| 3 | **Exact `within`** from symbol ranges; indentation stays for the floor. | Grounding precision | Very low | — |
| 4 | **Skeleton map**: top files as signature lines, under a budget (§9). | Agentless evidence | Medium | Caller renders scrubbed text |
| 5 | **Relations answered by code**: "more" may ask `importers:X`, `tests:X`, later `callers:X`. | Replaces a search round; multi-hop | Medium (schema, gate) | — |
| 6 | **`hubs()` for `init`**: most-imported modules and symbols, without tests and `__init__` re-exports. | Profile's "risky to change" | Low | — |
| 7 | **Read before the scout**: identifiers that resolve uniquely, with their tests, read first; scout skipped when they fill the round. | One call fewer | Medium; live measurement, owner's go-ahead | Changes a flow |
| 8 | Cache; more languages | — | Defer | — |

## 8. Adjustments to the agreed library shape

- **Symbols**: add module- and class-level assigned names (kind `variable`, never values; requests often name constants), and `head`, the signature's last line: `max(lineno, body[0].lineno - 1)`.
- **Imports**: add `lazy` (inside a function) and `type_checking` flags, as grimp has [17]. Resolve `*` through a literal `__all__`; otherwise count it unresolved.
- **Modules by path suffix**: `a.b.c` maps to `…/a/b/c.py` or `…/a/b/c/__init__.py`, so src layouts and monorepos need no roots parameter. Ambiguous means unresolved.
- **`tests` edges** carry `via`: `imports` or `name`. A **`main` flag** marks `__main__.py` and `if __name__ == "__main__"`.
- **Parse hygiene**, checked on 3.14.10: `ast.parse` emits `SyntaxWarning` for invalid escapes, so wrap it in `warnings.catch_warnings()`. Null bytes and over 200 nested brackets raise `SyntaxError`. A 200,000-term expression raised `RecursionError`: catch it into the floor, and walk with `ast.walk`, not recursive visitors.
- **Input guard**: refuse absolute paths, backslashes and `..` with a `ValueError`.
- **Queries**: add `matching(words)` and `ranked(seeds, limit)`, both deterministic (fixed iterations, ties by path).

## 9. Conflicts with "no source text in the graph"

- Signatures, docstring lines and repo maps are source text: they stay out. The graph stores `first`, `head`, `last`. Tool A renders lines `first..head` from `Source.lines()`, already scrubbed whole, key files withheld, each line cut at 200 characters. Tool B renders from its own blobs.
- Names and paths are still strings from the source. Tool A sends rendered facts through `scrub`; the Scrub plugin already fails closed. Word the rule "no source text beyond identifiers, paths and line numbers".
- Never record literal values: constants, `importlib` strings, decorator arguments.

## Sources

1. https://github.com/Graphify-Labs/graphify/blob/v8/README.md
2. https://github.com/Graphify-Labs/graphify/blob/v8/docs/how-it-works.md
3. https://github.com/Graphify-Labs/graphify/blob/v8/ARCHITECTURE.md
4. https://raw.githubusercontent.com/Graphify-Labs/graphify/v8/graphify/analyze.py
5. https://docs.graphify.com/reference/query
6. https://github.com/Aider-AI/aider/blob/main/aider/repomap.py
7. https://github.com/Aider-AI/aider/blob/main/aider/queries/tree-sitter-languages/python-tags.scm
8. https://aider.chat/docs/repomap.html
9. https://github.com/scip-code/scip/blob/main/scip.proto
10. https://github.com/scip-code/scip
11. https://sourcegraph.com/blog/announcing-scip
12. https://github.blog/open-source/introducing-stack-graphs/
13. https://github.com/github/stack-graphs
14. https://docs.ctags.io/en/latest/man/ctags-client-tools.7.html
15. https://docs.ctags.io/en/latest/optlib.html
16. https://tree-sitter.github.io/tree-sitter/4-code-navigation.html
17. https://grimp.readthedocs.io/en/stable/usage.html
18. https://import-linter.readthedocs.io/en/stable/
19. https://github.com/thebjorn/pydeps
20. https://github.com/Technologicat/pyan
21. https://github.com/oraios/serena
22. https://arxiv.org/abs/2603.27277
23. https://arxiv.org/pdf/2310.06770
24. https://arxiv.org/html/2407.01489
25. https://arxiv.org/html/2503.09089
26. https://arxiv.org/html/2410.14684v2
27. https://link.springer.com/article/10.1007/s10664-021-10079-1
28. https://arxiv.org/pdf/2011.09784
29. https://pypi.org/project/tree-sitter/ (with the tree-sitter-python, -javascript, -typescript and -language-pack wheel lists from PyPI's JSON API)
30. https://git-scm.com/docs/git-ls-tree, https://git-scm.com/docs/git-ls-files
