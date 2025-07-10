# Code‑Review Bot – Project Plan

---

## 1  Overview

An automated pull‑request reviewer that uses a Retrieval‑Augmented‑Generation (RAG) pipeline and an on‑prem **Qwen3** model. The bot automatically **indexes a repository the first time it sees a PR**, performs **incremental updates** on subsequent PRs, and posts inline review comments through the GitHub API.

---

## 2  Key Architecture Decisions

| Area                 | Decision                                                                                                                                                                                         | Rationale                                                                                  |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| **Indexing trigger** | Index automatically on first PR; re‑index incrementally on every new PR.                                                                                                                         | Zero manual steps; only deltas are processed after the first run.                          |
| **Storage split**    | **Vector store** (HNSW via `hnswlib`) **+** **metadata DB** (SQLite, WAL).                                                                                                                       | ANN search is lightning‑fast; SQL handles ad‑hoc queries.                                  |
| **Persisted data**   | `chunk_hash`, `vector`, `repo_id`, `file_path`, `start_line`, `end_line`, `expires_at`.                                                                                                          | No raw‑code duplication; minimal but sufficient metadata.                                  |
| **Chunking**         | **Tree‑sitter spans** for supported languages (JavaScript/TypeScript, Java, Rust, Python, C, C++, C#). Fallback to \~512‑token sliding windows (with small overlap) only when no grammar exists. | Language‑aware context for mainstream stacks; universal fallback keeps edge‑cases covered. |
| **Expiry policy**    | Delete vectors & metadata if `expires_at` < *now* (default 90 days since last PR).                                                                                                               | Bounded disk growth.                                                                       |
| **Retrieval tiers**  | **Tier 0** hunk‑overlap · **Tier 1** enclosing symbol · **Tier 2** ANN + rerank.                                                                                                                 | Guarantees local context; semantic neighbours added only if budget allows.                 |
| **LLM**              | Qwen3‑Chat (size configurable) with optional LoRA fine‑tune.                                                                                                                                     | Open‑source, tool‑calling support.                                                         |
| **Agentic loop**     | Optional single `retrieve(query)` tool call (max 2 repeats).                                                                                                                                     | Adds depth; keeps latency bounded.                                                         |

---

## 3  Data‑Flow Diagram

```text
PR webhook
   │  clone + diff
   ▼
indexer.incremental()  ──►  vector store  (hnswlib mmap)
                         metadata DB  (SQLite WAL)

Diff + PR body
   │ embed(query)
   ▼
ANN search  ─►  chunk_hashes  ─►  metadata lookup  ─►  file‑slice
                                   ▲
   Tier0/1 SQL overlap  ───────────┘

chunks + diff + PR text
   │
   ▼
Qwen3‑Chat  →  JSON review comments
   │
   ▼
GitHub REST  POST /pulls/:number/comments
```

---

## 5  Walking‑Skeleton Roadmap

| # | Milestone            | Deliverable                                                           |
| - | -------------------- | --------------------------------------------------------------------- |
| 0 | **Bootstrap**        | Repo init, uv env, `indexer.py` + `diff_analyzer.py`                  |
| 1 | **Tier 0/1 demo**    | 'uv run pr-review' prints diff + overlap/enclosing chunks.          |
| 2 | **Embeddings + ANN** | Vector table, hnswlib search, Tier 2 retrieval.                       |
| 3 | **LLM integration**  | Local Qwen3 generates review text in console.                         |
| 4 | **GitHub bot MVP**   | Webhook/Action posts comments automatically.                          |
| 5 | **Polish**           | Incremental embed, expiry GC, optional agentic loop & LoRA fine‑tune. |

---

## 6  Future Extensions

* Cross‑file second‑pass summariser.
* Severity classification & metrics dashboard.
* Token‑window optimiser for very large diffs.

---

**Status:** *Project skeleton in progress — Milestone 0 underway.*
