# PR Review Bot - Project Overview

## Executive Summary

An automated pull request review system that leverages Retrieval-Augmented Generation (RAG) with on-premise language models to provide intelligent code review feedback. The system automatically indexes repositories, maintains incremental updates, and generates contextually-aware review comments.

## Project Goals

### Primary Objectives

1. **Automated Code Review**: Provide meaningful, context-aware feedback on pull requests without human intervention
2. **On-Premise Deployment**: Run entirely on local infrastructure using open-source models (Qwen3-8B)
3. **Incremental Processing**: Efficiently handle large codebases by only processing changes
4. **Language-Aware Analysis**: Understand code structure beyond simple text matching

### Key Benefits

- Reduces reviewer burden for routine checks
- Catches potential issues early in development cycle
- Maintains consistent review standards
- Preserves code privacy (no external API calls)

## Architecture Overview

### High-Level Components

```text
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Git Repository│────▶│  Indexing Engine │────▶│  Vector Store   │
└─────────────────┘     └──────────────────┘     │  + Metadata DB  │
                                                  └─────────────────┘
                                                           │
┌─────────────────┐     ┌──────────────────┐              │
│    PR Event     │────▶│  Diff Analyzer   │◀─────────────┘
└─────────────────┘     └──────────────────┘
                                 │
                        ┌────────▼─────────┐
                        │ Context Selector │
                        │  (3-Tier RAG)    │
                        └────────┬─────────┘
                                 │
                        ┌────────▼─────────┐
                        │   LLM Review     │
                        │  (Qwen3-8B)      │
                        └──────────────────┘
```

### Core Components

#### 1. **Indexing Engine**

- **Purpose**: Build and maintain searchable knowledge base of repository code
- **Technology**:
  - Vector embeddings via `sentence-transformers/all-MiniLM-L6-v2`
  - HNSW index (via `hnswlib`) for fast approximate nearest neighbor search
  - SQLite for metadata storage (file paths, line numbers, timestamps)
- **Features**:
  - Incremental updates based on file modification time and content hash
  - Git-aware (respects .gitignore patterns)
  - Tracks file deletions and updates

#### 2. **Storage Layer**

- **Vector Store**:
  - HNSW index for semantic search (~100k vectors capacity)
  - Cosine similarity for relevance scoring
- **Metadata Database**:
  - SQLite with Write-Ahead Logging (WAL)
  - Stores: file_path, start_line, end_line, content_hash, modification_time
  - No raw code storage (privacy/efficiency)

#### 3. **Diff Analysis**

- **Purpose**: Extract and parse changes from pull requests
- **Implementation**:
  - GitPython for diff extraction
  - Hunk-level analysis (changed line ranges)
  - Supports multi-file changes

#### 4. **Context Selection (3-Tier RAG)**

- **Tier 0 - Direct Overlap**:
  - Code directly modified in the PR
  - Highest relevance, always included
- **Tier 1 - Surrounding Context**:
  - ±20 lines around changed code
  - Provides immediate context
- **Tier 2 - Semantic Neighbors**:
  - Vector similarity search (top-3 similar code blocks)
  - Finds related code across the repository

#### 5. **LLM Integration**

- **Model**: Qwen3-8B (8 billion parameters)
- **Features**:
  - Local execution (no external APIs)
  - Token limit management (131k context window)
  - Memory-efficient loading (8-bit quantization option)
  - Smart truncation when input exceeds limits

## Data Flow

1. **Initial Index**:

   ```text
   Repository → Git tracked files → Text extraction → Embedding generation → Vector/metadata storage
   ```

2. **PR Review Flow**:

   ```text
   PR event → Diff extraction → Context retrieval (3-tier) → LLM prompt → Review generation
   ```

3. **Incremental Updates**:

   ```text
   File changes → Hash comparison → Re-embed modified files → Update indices
   ```

## Technical Design Decisions

### Why These Choices?

1. **HNSW over other vector DBs**:
   - Extremely fast queries (sub-millisecond)
   - Low memory overhead
   - No external dependencies

2. **SQLite for metadata**:
   - ACID compliance
   - Zero configuration
   - Excellent for read-heavy workloads

3. **Separate vector/metadata storage**:
   - Allows independent scaling
   - Efficient updates (metadata changes don't require re-indexing)

4. **Git-aware indexing**:
   - Prevents indexing build artifacts (node_modules, target/, etc.)
   - Reduces storage and processing time by 90%+

5. **Token limit management**:
   - Prevents OOM errors with large diffs
   - Prioritizes diff content (70%) over context (30%)
   - Graceful degradation instead of failure

## Performance Characteristics

- **Indexing Speed**: ~100-500 files/minute (depending on size)
- **Incremental Updates**: Only modified files (typically <1% per PR)
- **Query Latency**: <100ms for context retrieval
- **Memory Usage**:
  - Embedding model: ~500MB
  - LLM: ~16-32GB (configurable with quantization)
  - Vector index: ~1GB per 100k vectors

## Scalability Considerations

### Current Limitations

- Single-node deployment
- Memory-bound by LLM size
- Sequential file processing

### Future Scaling Options

1. **Horizontal scaling**: Shard by repository/directory
2. **Model optimization**: LoRA fine-tuning for domain-specific reviews
3. **Caching layer**: Redis for frequently accessed embeddings
4. **Batch processing**: Parallel embedding generation

## Security & Privacy

- **On-premise execution**: No code leaves local infrastructure
- **No raw code storage**: Only embeddings and metadata
- **Git integration**: Inherits repository access controls
- **Configurable expiry**: Auto-cleanup of old data (90-day default)

## Integration Points

### Current

- CLI tool (`uv run pr-review`)
- Direct repository analysis

### Planned

- GitHub webhook integration
- GitHub Actions workflow
- GitLab CI/CD pipeline
- Bitbucket integration

## Roadmap

### Completed (Milestones 0-3)

- ✅ Core indexing engine
- ✅ Incremental updates
- ✅ 3-tier context retrieval
- ✅ LLM integration
- ✅ Token limit management

### In Progress (Milestone 4)

- 🔄 GitHub API integration
- 🔄 Automated PR commenting

### Future (Milestone 5+)

- ⏳ Cross-file analysis
- ⏳ Security vulnerability detection
- ⏳ Code quality metrics
- ⏳ Custom review policies
- ⏳ Multi-language support (via Tree-sitter)

## Dependencies

### Core

- Python 3.12+
- PyTorch (CUDA optional)
- Transformers (Hugging Face)
- GitPython
- hnswlib
- SQLiteDict

### Models

- Embedding: `sentence-transformers/all-MiniLM-L6-v2` (90MB)
- LLM: `Qwen/Qwen3-8B` (16GB in fp16, 8GB in int8)

## Configuration

### Environment Variables (Planned)

```bash
PRREVIEW_MODEL_NAME="Qwen/Qwen3-8B"
PRREVIEW_MAX_TOKENS=131072
PRREVIEW_EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"
PRREVIEW_ENABLE_QUANTIZATION=true
PRREVIEW_DEVICE="cuda"  # or "cpu"
```

### Resource Requirements

- **Minimum**: 16GB RAM, 20GB disk
- **Recommended**: 32GB RAM, NVIDIA GPU with 16GB+ VRAM
- **Storage**: ~10MB per 1000 source files

## Known Issues & Limitations

1. **Large repositories**: Initial indexing can be slow (>10k files)
2. **Binary files**: Not supported (skipped during indexing)
3. **Non-UTF8 files**: May cause encoding errors
4. **Memory usage**: LLM requires significant RAM/VRAM
5. **Context window**: Very large diffs may be truncated

## Alternative Approaches Considered

1. **Full-text search instead of embeddings**:
   - Rejected: Misses semantic similarities

2. **Graph databases for code relationships**:
   - Rejected: Complexity outweighs benefits for MVP

3. **External LLM APIs (OpenAI, Anthropic)**:
   - Rejected: Privacy concerns, latency, cost

4. **Streaming diff processing**:
   - Deferred: Planned for future optimization

## Success Metrics

- Review generation time: <30 seconds per PR
- Relevant context retrieval: >80% precision
- False positive rate: <20%
- Memory efficiency: <32GB for typical repositories

## Contributing Guidelines

When extending this system, consider:

1. **Maintain incremental processing**: Don't break the efficiency gains
2. **Respect memory limits**: Test with large repositories
3. **Preserve privacy**: No external data transmission
4. **Document changes**: Update this document with architectural changes

## Questions for Review

1. Should we implement distributed processing for large repositories?
2. Is the 3-tier context selection optimal, or should we add more tiers?
3. Should we support multiple LLM backends (Llama, Mistral, etc.)?
4. How should we handle multi-language repositories?
5. What metrics should we track for continuous improvement?
