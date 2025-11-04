"""
Sentinel Searcher - Automated web research and content updates.

Use this package to:
- Run automated web searches using Claude with web search
- Extract structured data into JSON files
- Automate content updates via GitHub Actions

CLI Usage:
    sentinelsearcher --config sentinel.config.yaml

Python API Usage:
    from sentinelsearcher import run_sentinel_searcher, create_client

    # Simple usage
    run_sentinel_searcher(config_path="sentinel.config.yaml")

    # Advanced usage
    client = create_client()
    results = run_sentinel_searcher(
        config_path="sentinel.config.yaml",
        client=client
    )
"""

from sentinelsearcher.main import run_job, main
from sentinelsearcher.config import load_config, Config, Job, APIConfig
import anthropic
import os
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List

__version__ = "0.1.0"
__all__ = [
    "run_sentinel_searcher",
    "create_client",
    "run_job",
    "load_config",
    "Config",
    "Job",
    "APIConfig",
]


def create_client(api_key: Optional[str] = None) -> anthropic.Anthropic:
    """
    Create an Anthropic client with API key from environment or parameter.

    Args:
        api_key: Optional API key. If not provided, loads from ANTHROPIC_API_KEY env var.

    Returns:
        Configured Anthropic client

    Raises:
        ValueError: If API key is not provided and not found in environment

    Example:
        >>> client = create_client()
        >>> # or
        >>> client = create_client(api_key="your-api-key")
    """
    load_dotenv()

    key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError(
            "ANTHROPIC_API_KEY not provided and not found in environment. "
            "Either pass api_key parameter or set ANTHROPIC_API_KEY in .env file."
        )

    return anthropic.Anthropic(api_key=key)


def run_sentinel_searcher(
    config_path: str = "sentinel.config.yaml",
    client: Optional[anthropic.Anthropic] = None,
    api_key: Optional[str] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Run Sentinel Searcher with a config file.

    Args:
        config_path: Path to sentinel.config.yaml file
        client: Optional pre-configured Anthropic client
        api_key: Optional API key (only used if client is not provided)

    Returns:
        Dictionary mapping job names to their results

    Raises:
        ValueError: If config is invalid or API key is missing
        Exception: If any job fails

    Example:
        >>> # Simple usage
        >>> results = run_sentinel_searcher("sentinel.config.yaml")
        >>> print(f"Found {len(results['academic-awards'])} awards")

        >>> # With custom client
        >>> client = create_client(api_key="your-key")
        >>> results = run_sentinel_searcher("config.yaml", client=client)

        >>> # Access results
        >>> for job_name, items in results.items():
        ...     print(f"{job_name}: {len(items)} new items")
    """
    # Load config
    cfg = load_config(config_path)

    # Create client if not provided
    if client is None:
        client = create_client(api_key=api_key)

    # Validate provider
    provider = cfg.api.provider.lower()
    if provider != "anthropic":
        raise ValueError(f"Unsupported provider: {provider}. Only 'anthropic' is supported.")

    # Run all jobs and collect results
    results = {}

    import time
    delay_between_jobs = getattr(cfg.api, 'delay_between_jobs', 60)

    for idx, job in enumerate(cfg.jobs):
        print(f"Running job: {job.name}")

        job_results = run_job(
            client=client,
            model=cfg.api.model,
            instruction=job.instruction,
            schema=job.schema,
            file_path=job.file_path
        )

        results[job.name] = job_results
        print(f"[{job.name}] completed. New items: {len(job_results)}")

        # Add delay between jobs (except after last job)
        if idx < len(cfg.jobs) - 1 and delay_between_jobs > 0:
            print(f"Waiting {delay_between_jobs} seconds before next job...")
            time.sleep(delay_between_jobs)

    return results
