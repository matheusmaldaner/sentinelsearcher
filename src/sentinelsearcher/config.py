"""
Configuration loading and validation for Sentinel Searcher.

This module provides dataclasses for structured configuration and
a loader function to parse YAML config files.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List
from pathlib import Path

import yaml


@dataclass
class APIConfig:
    """
    API provider configuration.

    Attributes:
        provider: The AI provider to use ('anthropic' or 'openai')
        model: The model identifier (e.g., 'claude-sonnet-4-20250514', 'gpt-4o')
        delay_between_jobs: Seconds to wait between jobs to avoid rate limits
    """
    provider: str
    model: str
    delay_between_jobs: int = 60


@dataclass
class Job:
    """
    A single search job configuration.

    Attributes:
        name: Unique identifier for this job
        instruction: Search instruction describing what to find
        file_path: Output file path for results
        schema: Output schema definition with field types
        output_format: Output format ('json' or 'yaml')
    """
    name: str
    instruction: str
    file_path: str
    schema: Dict[str, Any] = field(default_factory=dict)
    output_format: str = "json"


@dataclass
class Config:
    """
    Complete Sentinel Searcher configuration.

    Attributes:
        api: API provider settings
        jobs: List of search jobs to execute
    """
    api: APIConfig
    jobs: List[Job] = field(default_factory=list)


class ConfigError(Exception):
    """Raised when configuration is invalid or missing required fields."""
    pass


def load_config(path: str) -> Config:
    """
    Load and validate a Sentinel Searcher configuration file.

    Args:
        path: Path to the YAML configuration file

    Returns:
        Validated Config object

    Raises:
        ConfigError: If the file is missing, invalid YAML, or missing required fields
        FileNotFoundError: If the config file doesn't exist

    Example:
        >>> config = load_config("sentinel.config.yaml")
        >>> print(f"Using provider: {config.api.provider}")
        >>> for job in config.jobs:
        ...     print(f"  - {job.name}")
    """
    config_path = Path(path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    try:
        data = yaml.safe_load(config_path.read_text())
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in config file: {e}")

    if not isinstance(data, dict):
        raise ConfigError("Config file must contain a YAML mapping")

    if "api" not in data:
        raise ConfigError("Config file missing required 'api' section")

    api_data = data["api"]
    if "provider" not in api_data:
        raise ConfigError("API config missing required 'provider' field")
    if "model" not in api_data:
        raise ConfigError("API config missing required 'model' field")

    api = APIConfig(**api_data)

    jobs = []
    for idx, job_data in enumerate(data.get("jobs", [])):
        if "name" not in job_data:
            raise ConfigError(f"Job {idx} missing required 'name' field")
        if "instruction" not in job_data:
            raise ConfigError(f"Job '{job_data.get('name', idx)}' missing required 'instruction' field")
        if "file_path" not in job_data:
            raise ConfigError(f"Job '{job_data['name']}' missing required 'file_path' field")
        jobs.append(Job(**job_data))

    return Config(api=api, jobs=jobs)
