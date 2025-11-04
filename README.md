<div align="center">

# 🔍 Sentinel Searcher

*AI-powered web browsing and structured data extraction*

[![PyPI](https://img.shields.io/pypi/v/sentinelsearcher.svg)](https://pypi.org/project/sentinelsearcher/)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

</div>

---

## 🧠 Overview

**Sentinel Searcher** is a simple, powerful tool for browsing the web and retrieving structured data in JSON format. Define a schema, point it at a topic, and let AI agents search the web and return exactly the data you need.

Perfect for automated research, data collection, content curation, and keeping files up-to-date with the latest information from the web.

---

## 🚀 Quick Start

### Installation

Install from TestPyPI:

```bash
uv pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple sentinelsearcher==0.1.0
```

Or add to your project:

```bash
uv add sentinelsearcher
```

### Configuration

**1. Set up your API keys**

Copy `.env-example` and rename it to `.env`, then fill in your API key:

```bash
ANTHROPIC_API_KEY=your_key_here
```

**2. Create your configuration**

Populate `sentinel.config.yaml` with the path to the file you want updated and the specific schema you want the LLM to follow.

Example configuration:

```yaml
api:
  provider: "anthropic"
  model: "claude-sonnet-4-20250514"
  delay_between_jobs: 60  # Seconds to wait between jobs to avoid rate limits

jobs:
  # Example: Track academic awards
  - name: "academic-awards"
    instruction: "Find recent academic awards and honors for [Your Name] in AI research"
    file_path: "examples/awards.json"
    schema:
      type: "array"
      items:
        award_name: "string"
        award_date: "YYYY-MM-DD"
        award_picture: "string"
        award_description: "string"

  # Example: Track news mentions
  - name: "news-updates"
    instruction: "Find recent news mentions of [Your Organization]"
    file_path: "examples/news.json"
    schema:
      type: "array"
      items:
        title: "string"
        url: "string"
        date: "YYYY-MM-DD"
        summary: "string"
```

**3. Run the searcher**

```bash
sentinelsearcher
```

The tool will search the web and update your files with structured JSON data matching your schema.

---

## 🤖 GitHub Actions Automation

You can easily run Sentinel Searcher as a GitHub workflow to automatically update your repository files on a schedule.

### Setting Up Secrets

Set up your API keys as GitHub secrets either by navigating to "GitHub Actions → Secrets" or programmatically:

```bash
gh secret set OPENAI_API_KEY --body "$(grep OPENAI_API_KEY .env | cut -d '=' -f2-)"
gh secret set ANTHROPIC_API_KEY --body "$(grep ANTHROPIC_API_KEY .env | cut -d '=' -f2-)"
```

Ensure you have the variables defined in your `.env` file.

**Don't have `gh` CLI installed?**

```bash
sudo apt install gh
```

**Authenticate GitHub CLI:**

Choose one method:
1. `gh auth login`
2. Set `GH_TOKEN="yourtoken"` in `.env` (generate at https://github.com/settings/tokens)

**Enable PR creation:**

Allow GitHub Actions to create pull requests:

```bash
gh api -X PUT /repos/OWNER/REPO/actions/permissions/workflow \
  -f default_workflow_permissions=write \
  -F can_approve_pull_request_reviews=true
```

*(Replace `OWNER/REPO` with your repository path)*

### Workflow Configuration

Add this workflow to `.github/workflows/sentinel-searcher.yml` in your repository:

```yaml
name: Sentinel Searcher

on:
  schedule:
    - cron: "0 3 * * *"  # daily at 3 AM UTC
  workflow_dispatch: {}  # manual trigger

jobs:
  run:
    uses: matheusmaldaner/sentinelsearcher/.github/workflows/sentinel-searcher-callable.yml@main
    with:
      working_directory: "."  # adjust if needed
      config_path: "sentinel.config.yaml"  # path in the target repo
      python_version: "3.11"
    secrets:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

The workflow will automatically search the web based on your configuration and create pull requests with updated data.

---

## 📄 License

MIT License - feel free to use this in your projects!

---

<div align="center">
Made with ❤️ for intelligent web data extraction
</div>