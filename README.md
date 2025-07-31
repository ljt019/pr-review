# Bug Detection Bot

An automated bug detection system that analyzes codebases for security vulnerabilities, code quality issues, and potential bugs.

## Features

- Automated code analysis for common security vulnerabilities
- Support for multiple programming languages
- Evaluation framework with ground truth comparison
- Containerized deployment with Docker
- Comprehensive reporting and metrics

## Quick Start

### Prerequisites

- Python 3.11+
- Docker (for containerized deployment)
- uv package manager

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd bug-bot

# Install dependencies
uv sync
```

### Usage

```bash
# Run bug detection analysis
uv run src/main.py

# Run evaluation against ground truth
uv run scripts/eval.py

# Run with Docker
docker compose up
```

## Project Structure

```
├── src/                    # Main source code
├── scripts/               # Utility scripts
├── evals/                 # Evaluation framework
├── claude_agents/         # Claude agent configurations
├── bugs_ground_truth.json # Ground truth data for evaluation
└── compose.yml           # Docker compose configuration
```

## Configuration

Set up your environment variables in `.env`:

```bash
ANTHROPIC_API_KEY=your_api_key_here
```

## Evaluation

The evaluation system compares detected bugs against ground truth data:

```bash
# Run full evaluation suite
uv run scripts/eval.py

# View evaluation results
cat evaluation_results.json
```

## Contributing

1. Follow existing code conventions
2. Add tests for new functionality
3. Update ground truth data when adding new bug types
4. Run evaluations before submitting changes