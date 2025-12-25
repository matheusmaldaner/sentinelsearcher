<div align="center">

# Sentinel Searcher

**AI-powered web search and structured data extraction**

[![PyPI](https://img.shields.io/pypi/v/sentinelsearcher.svg)](https://pypi.org/project/sentinelsearcher/)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

</div>

---

## Overview

Sentinel Searcher is a tool for automated web research that returns structured data. Define a schema, describe what to search for, and let AI agents browse the web and return exactly the data you need in JSON or YAML format.

**Supported Providers:**
- **Anthropic Claude** - Uses `web_search_20250305` tool
- **OpenAI GPT** - Uses `web_search_preview` via Responses API

**Use Cases:**
- Portfolio automation (awards, publications, news mentions)
- Competitive intelligence gathering
- Content curation and aggregation
- Research data collection

---

## Installation

```bash
pip install sentinelsearcher
```

For OpenAI support:

```bash
pip install sentinelsearcher[openai]
```

---

## Quick Start

### 1. Set up API keys

Create a `.env` file or set environment variables:

```bash
# For Anthropic (default)
ANTHROPIC_API_KEY=your_key_here

# For OpenAI
OPENAI_API_KEY=your_key_here
```

### 2. Create configuration

Create `sentinel.config.yaml`:

```yaml
api:
  provider: "anthropic"  # or "openai"
  model: "claude-sonnet-4-20250514"  # or "gpt-4o"
  delay_between_jobs: 60

jobs:
  - name: "news-updates"
    instruction: "Find recent news articles mentioning Acme Corp product launches"
    file_path: "data/news.yaml"
    output_format: "yaml"
    schema:
      type: "array"
      items:
        title: "string"
        url: "string"
        date: "YYYY-MM-DD"
        summary: "string"

  - name: "awards"
    instruction: "Find industry awards won by Acme Corp in 2024-2025"
    file_path: "data/awards.json"
    schema:
      type: "array"
      items:
        award_name: "string"
        date: "YYYY-MM-DD"
        description: "string"
```

### 3. Run

```bash
sentinelsearcher --config sentinel.config.yaml
```

Or generate starter files:

```bash
sentinelsearcher --start
```

---

## Python API

```python
from sentinelsearcher import run_sentinel_searcher, create_provider

# Simple usage (reads provider from config)
results = run_sentinel_searcher("sentinel.config.yaml")

for job_name, items in results.items():
    print(f"{job_name}: {len(items)} new items found")

# With explicit provider
provider = create_provider("openai")
results = run_sentinel_searcher("config.yaml", provider=provider)
```

---

## Configuration Reference

### API Section

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `provider` | string | Yes | `"anthropic"` or `"openai"` |
| `model` | string | Yes | Model identifier |
| `delay_between_jobs` | int | No | Seconds between jobs (default: 60) |

**Recommended Models:**
- Anthropic: `claude-sonnet-4-20250514`
- OpenAI: `gpt-4o`

### Job Section

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique job identifier |
| `instruction` | string | Yes | Search instruction for the AI |
| `file_path` | string | Yes | Output file path |
| `schema` | object | Yes | Output data schema |
| `output_format` | string | No | `"json"` (default) or `"yaml"` |

### Schema Types

The schema uses a simplified format:

```yaml
schema:
  type: "array"
  items:
    field_name: "string"       # Any text
    date_field: "YYYY-MM-DD"   # ISO date format
    image_field: "example.png" # Placeholder indicator
```

---

## GitHub Actions

Automate searches with a scheduled workflow:

```yaml
name: Sentinel Search

on:
  schedule:
    - cron: "0 9 1 * *"  # Monthly on the 1st
  workflow_dispatch: {}

jobs:
  search:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - run: pip install sentinelsearcher[openai]

      - run: sentinelsearcher --config sentinel.config.yaml
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}

      - uses: peter-evans/create-pull-request@v5
        with:
          commit-message: "chore: update from Sentinel Search"
          title: "Sentinel Search: New content found"
          branch: sentinel-updates
```

### Setting Secrets

```bash
gh secret set OPENAI_API_KEY --body "sk-..."
gh secret set ANTHROPIC_API_KEY --body "sk-ant-..."
```

---

## How It Works

1. **Load Configuration** - Reads your YAML config with jobs and schemas
2. **Read Existing Data** - Loads current file contents to avoid duplicates
3. **Web Search** - AI agent searches the web based on your instruction
4. **Extract & Validate** - Parses response and validates against schema
5. **Deduplicate & Merge** - Combines new items with existing data
6. **Write Output** - Saves updated file in JSON or YAML format

---

## License

MIT License - see [LICENSE](LICENSE) for details.
