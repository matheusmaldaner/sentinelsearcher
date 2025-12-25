"""
Sentinel Searcher - Automated web research and content updates.

Supports multiple AI providers:
- Anthropic Claude with web search (web_search_20250305)
- OpenAI GPT with web search (web_search_preview via Responses API)

CLI Usage:
    sentinelsearcher --config sentinel.config.yaml

Python API Usage:
    from sentinelsearcher import run_sentinel_searcher, create_provider

    # Simple usage with Anthropic (default)
    run_sentinel_searcher(config_path="sentinel.config.yaml")

    # With OpenAI
    provider = create_provider("openai")
    results = run_sentinel_searcher(
        config_path="sentinel.config.yaml",
        provider=provider
    )
"""

from sentinelsearcher.main import run_job, main
from sentinelsearcher.config import load_config, Config, Job, APIConfig, ConfigError
from sentinelsearcher.providers import (
    WebSearchProvider,
    AnthropicProvider,
    OpenAIProvider,
    create_provider,
)
import os
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List

__version__ = "0.2.0"
__all__ = [
    # Main entry points
    "run_sentinel_searcher",
    "run_job",
    # Providers
    "create_provider",
    "WebSearchProvider",
    "AnthropicProvider",
    "OpenAIProvider",
    # Configuration
    "load_config",
    "Config",
    "Job",
    "APIConfig",
    "ConfigError",
]


def run_sentinel_searcher(
    config_path: str = "sentinel.config.yaml",
    provider: Optional[WebSearchProvider] = None,
    api_key: Optional[str] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Run Sentinel Searcher with a config file.

    Args:
        config_path: Path to sentinel.config.yaml file
        provider: Optional pre-configured WebSearchProvider instance
        api_key: Optional API key (only used if provider is not provided)

    Returns:
        Dictionary mapping job names to their results

    Raises:
        ValueError: If config is invalid or API key is missing
        Exception: If any job fails

    Example:
        >>> # Simple usage (reads provider from config)
        >>> results = run_sentinel_searcher("sentinel.config.yaml")
        >>> print(f"Found {len(results['academic-awards'])} awards")

        >>> # With custom provider
        >>> provider = create_provider("openai", api_key="your-key")
        >>> results = run_sentinel_searcher("config.yaml", provider=provider)

        >>> # Access results
        >>> for job_name, items in results.items():
        ...     print(f"{job_name}: {len(items)} new items")
    """
    load_dotenv()

    # Load config
    cfg = load_config(config_path)

    # Create provider if not provided
    if provider is None:
        provider_name = cfg.api.provider.lower()
        provider = create_provider(provider_name, api_key=api_key)

    model = cfg.api.model

    # Run all jobs and collect results
    results = {}

    import time
    delay_between_jobs = getattr(cfg.api, 'delay_between_jobs', 60)

    for idx, job in enumerate(cfg.jobs):
        print(f"Running job: {job.name}")

        job_results = run_job(
            provider=provider,
            model=model,
            instruction=job.instruction,
            schema=job.schema,
            file_path=job.file_path,
            output_format=job.output_format,
        )

        results[job.name] = job_results
        print(f"[{job.name}] completed. New items: {len(job_results)}")

        # Add delay between jobs (except after last job)
        if idx < len(cfg.jobs) - 1 and delay_between_jobs > 0:
            print(f"Waiting {delay_between_jobs} seconds before next job...")
            time.sleep(delay_between_jobs)

    return results
