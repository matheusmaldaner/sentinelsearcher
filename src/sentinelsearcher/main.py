
import os
import json
import argparse
import sys
import time
from datetime import date as _date
from pathlib import Path
from typing import Any, Dict, List, Tuple

import anthropic
import yaml
from dotenv import load_dotenv

from sentinelsearcher.config import load_config

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

def _extract_yaml_from_text(text: str) -> Any:
    import yaml, re
    # Try direct parse
    try:
        return yaml.safe_load(text)
    except Exception:
        pass
    # Try fenced code block
    m = re.search(r"```(?:yaml)?\s*([\s\S]*?)\s*```", text, re.MULTILINE)
    if m:
        return yaml.safe_load(m.group(1))
    # Fallback to the whole text if no fences
    return yaml.safe_load(text)

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
                if not isinstance(v, str):
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

def run_job(client: anthropic.Anthropic, model: str, instruction: str, schema: Dict[str, Any], file_path: str, output_format: str = "json", max_retries: int = 3) -> List[Dict[str, Any]]:
    dst = Path(file_path)
    
    if output_format == "yaml":
        existing = _read_yaml_array(dst)
        format_prompt = "Return ONLY valid YAML, no prose. Do not wrap in markdown."
        schema_str = yaml.dump(schema, indent=2)
        existing_str = yaml.dump(existing, allow_unicode=True)
    else: # default to json
        existing = _read_json_array(dst)
        format_prompt = "Return ONLY valid JSON, no prose. Do not wrap in markdown."
        schema_str = json.dumps(schema, indent=2)
        existing_str = json.dumps(existing, ensure_ascii=False, indent=2)


    system = (
        "You are a precise web researcher.\n"
        f"{format_prompt}\n"
        f"The output MUST conform to this shape (array of objects): {schema_str}\n"
        "Do not duplicate items that already exist in EXISTING_CONTENT.\n"
        "If nothing new is found, return an empty array []."
    )
    print(system)

    user = (
        f"Task: {instruction}\n\n"
        f"EXISTING_CONTENT:\n{existing_str}\n"
    )

    # Retry logic with exponential backoff for rate limits
    for attempt in range(max_retries):
        try:
            msg = client.messages.create(
                model=model,
                max_tokens=2048,
                system=system,
                messages=[{"role": "user", "content": user}],
                tools=[{
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": 5
                }],
            )

            # Anthropic content is a list of text blocks
            text = "".join(getattr(b, "text", "") for b in msg.content if getattr(b, "type", "") == "text")
            
            if output_format == "yaml":
                data = _extract_yaml_from_text(text)
            else:
                data = _extract_json_from_text(text)

            print(data)
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

        except anthropic.RateLimitError:
            if attempt < max_retries - 1:
                # Exponential backoff: 2^attempt * 30 seconds
                wait_time = (2 ** attempt) * 30
                print(f"Rate limit hit. Retrying in {wait_time} seconds... (attempt {attempt + 1}/{max_retries})", file=sys.stderr)
                time.sleep(wait_time)
            else:
                raise  # Re-raise on last attempt



def main_deprecated():
    # load .env file into environment variables
    load_dotenv()

    # set the api key from environment variable
    api_key = os.getenv("ANTHROPIC_API_KEY")

    # initialize the client with the api key
    client = anthropic.Anthropic(api_key=api_key)

    # create a message with web search tool enabled
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": "Find the latest 3 news about Matheus Kunzler Maldaner"
            }
        ],
        tools=[{
            "type": "web_search_20250305",
            "name": "web_search",
            #"max_uses": 5
        }]
    )
    print(message.content)



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

    provider = None
    model = None
    try:
        cfg = load_config(args.config)
        provider = cfg.api.provider.lower()
        model = cfg.api.model
    except Exception as e:
        print(f"Failed to load config: {e}", file=sys.stderr)
        sys.exit(1)

    if provider not in ("anthropic", "openai"):
        print(f"Unsupported provider: {provider}", file=sys.stderr)
        sys.exit(1)

    if provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("ANTHROPIC_API_KEY not set", file=sys.stderr)
            sys.exit(1)
        client = anthropic.Anthropic(api_key=api_key)
    else:
        print("OpenAI provider not implemented yet in this runner.", file=sys.stderr)
        sys.exit(1)

    delay_between_jobs = getattr(cfg.api, 'delay_between_jobs', 60)

    for idx, job in enumerate(cfg.jobs):
        try:
            added = run_job(client, model, job.instruction, job.schema, job.file_path, job.output_format)
            print(f"[{job.name}] completed. New items: {len(added)}")

            # Add delay between jobs to avoid rate limits (except after last job)
            if idx < len(cfg.jobs) - 1 and delay_between_jobs > 0:
                print(f"Waiting {delay_between_jobs} seconds before next job to avoid rate limits...")
                time.sleep(delay_between_jobs)

        except Exception as e:
            print(f"[{job.name}] failed: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
