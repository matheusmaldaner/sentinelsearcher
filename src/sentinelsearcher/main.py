
import os
import json
import argparse
import sys
import time
from datetime import date as _date
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

import yaml
from dotenv import load_dotenv

from sentinelsearcher.config import load_config
from sentinelsearcher.providers import WebSearchProvider, create_provider

CONFIG_PLACEHOLDER = """api:
  provider: "anthropic"
  model: "claude-sonnet-4-20250514"
  delay_between_jobs: 60

jobs:
  - name: "example-job"
    instruction: "Describe what to search for"
    file_path: "examples/output.yaml"
    schema:
      type: "array"
      items:
        title: "string"
        url: "string"
        date: "YYYY-MM-DD"
        summary: "string"
    output_format: "yaml"
"""

ENV_PLACEHOLDER = """# Populate with your API keys before running sentinelsearcher
# For Anthropic:
ANTHROPIC_API_KEY=your_key_here

# Optional OpenAI key if support is added later:
# OPENAI_API_KEY=your_key_here
"""


def _create_placeholder_file(path: Path, contents: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        print(f"{path} already exists; leaving it untouched.")
        return
    path.write_text(contents)
    print(f"Created {path}")


def _handle_start(config_path: Path) -> None:
    _create_placeholder_file(config_path, CONFIG_PLACEHOLDER)
    _create_placeholder_file(Path(".env"), ENV_PLACEHOLDER)
    print("Placeholder files ready. Populate them, then run sentinelsearcher --config your_config.yaml")

def _read_json_array(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text() or "[]")
    except Exception:
        return []

def _read_yaml_array(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        return yaml.safe_load(path.read_text() or "[]")
    except Exception:
        return []
    
def _extract_json_from_text(text: str) -> Any:
    import json, re
    # Try direct parse
    try:
        return json.loads(text)
    except Exception:
        pass
    # Try fenced code block
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\}|\[[\s\S]*?\])\s*```", text, re.MULTILINE)
    if m:
        return json.loads(m.group(1))
    # Try first top-level array/object
    m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    if m:
        return json.loads(m.group(1))
    raise ValueError("Could not parse JSON from model output")

def _convert_dates_to_strings(obj: Any) -> Any:
    """Recursively convert datetime.date objects to ISO format strings."""
    if isinstance(obj, _date):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: _convert_dates_to_strings(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_dates_to_strings(item) for item in obj]
    return obj

def _extract_yaml_from_text(text: str) -> Any:
    import yaml, re

    # If model says "no results" or similar, return empty array
    no_results_phrases = [
        "no news items", "no items found", "nothing found", "no results",
        "empty array", "no new", "nothing new", "could not find"
    ]
    text_lower = text.lower()
    if any(phrase in text_lower for phrase in no_results_phrases):
        # Check if there's still an array in the text
        if "[]" in text or not re.search(r'\[.*\{', text, re.DOTALL):
            return []

    data = None
    # Try direct parse
    try:
        data = yaml.safe_load(text)
    except Exception:
        pass
    # Try fenced code block
    if data is None:
        m = re.search(r"```(?:yaml)?\s*([\s\S]*?)\s*```", text, re.MULTILINE)
        if m:
            try:
                data = yaml.safe_load(m.group(1))
            except Exception:
                pass
    # Fallback to the whole text if no fences
    if data is None:
        try:
            data = yaml.safe_load(text)
        except Exception:
            return []  # Can't parse, return empty
    # Handle case where model returns {items: [...]} instead of [...]
    if isinstance(data, dict) and 'items' in data and isinstance(data['items'], list):
        data = data['items']
    # If still not a list, return empty
    if not isinstance(data, list):
        return []
    # Convert any datetime.date objects to strings
    data = _convert_dates_to_strings(data)
    return data

def _write_json_array(path: Path, data: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

def _write_yaml_array(path: Path, data: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, indent=2, allow_unicode=True))

def _dedupe(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for it in items:
        key = yaml.dump(it, sort_keys=True)
        if key not in seen:
            seen.add(key)
            out.append(it)
    return out

def _validate_simple_schema(data: Any, schema: Dict[str, Any]) -> Tuple[bool, str]:
    # Supports schema like:
    # { type: "array", items: { field: "string" | "YYYY-MM-DD" | "example.png" } }
    if schema.get("type") != "array":
        return False, "Only array schemas are supported"
    if not isinstance(data, list):
        return False, "Model did not return an array"
    item_shape = schema.get("items", {})
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            return False, f"Item {idx} is not an object"
        for k, t in item_shape.items():
            if k not in item:
                return False, f"Missing key '{k}' in item {idx}"
            v = item[k]
            if t in ("string", "example.png"):
                # Be lenient: convert int/float to string
                if isinstance(v, (int, float)):
                    item[k] = str(v)
                elif not isinstance(v, str):
                    return False, f"Key '{k}' in item {idx} should be string"
            elif t == "YYYY-MM-DD":
                if isinstance(v, _date):
                    item[k] = v.isoformat()
                    v = item[k]
                if not isinstance(v, str):
                    return False, f"Key '{k}' in item {idx} should be string"
                parts = v.split("-")
                if len(parts) != 3 or not all(p.isdigit() for p in parts):
                    return False, f"Key '{k}' in item {idx} should be YYYY-MM-DD"
    return True, ""

def run_job(
    provider: WebSearchProvider,
    model: str,
    instruction: str,
    schema: Dict[str, Any],
    file_path: str,
    output_format: str = "json",
    max_retries: int = 3,
    extra_context: str = ""
) -> List[Dict[str, Any]]:
    """
    Run a single search job using the configured provider.

    Args:
        provider: WebSearchProvider instance (Anthropic or OpenAI)
        model: Model identifier
        instruction: Search instruction
        schema: Output schema definition
        file_path: Path to output file
        output_format: 'json' or 'yaml'
        max_retries: Number of retry attempts for rate limits

    Returns:
        List of new items found
    """
    dst = Path(file_path)

    if output_format == "yaml":
        existing = _read_yaml_array(dst)
        format_prompt = "Return ONLY valid YAML, no prose. Do not wrap in markdown."
        schema_str = yaml.dump(schema, indent=2)
        existing_str = yaml.dump(existing, allow_unicode=True)
    else:  # default to json
        existing = _read_json_array(dst)
        format_prompt = "Return ONLY valid JSON, no prose. Do not wrap in markdown."
        schema_str = json.dumps(schema, indent=2)
        existing_str = json.dumps(existing, ensure_ascii=False, indent=2)

    # Get today's date for context
    from datetime import date
    today = date.today().isoformat()

    system = (
        "You are a precise web researcher.\n"
        f"Today's date: {today}\n\n"
        f"{format_prompt}\n"
        f"Output schema: {schema_str}\n"
        "Do not duplicate items that already exist in EXISTING_CONTENT.\n"
        "If nothing new is found, return an empty array [].\n"
    )

    # Build user prompt
    user_parts = [f"Task: {instruction}"]

    if extra_context:
        user_parts.append(f"\nADDITIONAL_CONTEXT:\n{extra_context}")

    user_parts.append(f"\nEXISTING_CONTENT:\n{existing_str}")

    user = "\n".join(user_parts)

    rate_limit_error = provider.get_rate_limit_error_class()

    # Retry logic with exponential backoff for rate limits
    for attempt in range(max_retries):
        try:
            text = provider.search_and_extract(
                system=system,
                user=user,
                model=model,
                max_tokens=2048,
                max_search_uses=5,
            )

            if output_format == "yaml":
                data = _extract_yaml_from_text(text)
            else:
                data = _extract_json_from_text(text)

            ok, err = _validate_simple_schema(data, schema)
            if not ok:
                raise ValueError(f"Model output failed schema validation: {err}")

            merged = _dedupe([*existing, *data])
            if merged != existing:
                if output_format == "yaml":
                    _write_yaml_array(dst, merged)
                else:
                    _write_json_array(dst, merged)
            return data

        except rate_limit_error:
            if attempt < max_retries - 1:
                # Exponential backoff: 2^attempt * 30 seconds
                wait_time = (2 ** attempt) * 30
                print(f"Rate limit hit. Retrying in {wait_time} seconds... (attempt {attempt + 1}/{max_retries})", file=sys.stderr)
                time.sleep(wait_time)
            else:
                raise  # Re-raise on last attempt



def main():
    load_dotenv()  # loads .env into os.environ

    parser = argparse.ArgumentParser(description="Sentinel Searcher")
    parser.add_argument("--config", default="sentinel.config.yaml", help="Path to config YAML")
    parser.add_argument("--start", action="store_true", help="Create starter sentinel.config.yaml and .env files")
    args = parser.parse_args()

    if args.start:
        _handle_start(Path(args.config))
        return

    print("Welcome to Sentinel Searcher!")

    provider_name = None
    model = None
    try:
        cfg = load_config(args.config)
        provider_name = cfg.api.provider.lower()
        model = cfg.api.model
    except Exception as e:
        print(f"Failed to load config: {e}", file=sys.stderr)
        sys.exit(1)

    # Create provider instance
    try:
        provider = create_provider(provider_name)
        print(f"Using provider: {provider_name} (model: {model})")
    except ValueError as e:
        print(f"Provider error: {e}", file=sys.stderr)
        sys.exit(1)
    except ImportError as e:
        print(f"Import error: {e}", file=sys.stderr)
        sys.exit(1)

    delay_between_jobs = getattr(cfg.api, 'delay_between_jobs', 60)

    for idx, job in enumerate(cfg.jobs):
        try:
            added = run_job(provider, model, job.instruction, job.schema, job.file_path, job.output_format)
            print(f"[{job.name}] completed. New items: {len(added)}")

            # Add delay between jobs to avoid rate limits (except after last job)
            if idx < len(cfg.jobs) - 1 and delay_between_jobs > 0:
                print(f"Waiting {delay_between_jobs} seconds before next job to avoid rate limits...")
                time.sleep(delay_between_jobs)

        except Exception as e:
            print(f"[{job.name}] failed: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
