from dataclasses import dataclass
from typing import Any, Dict, List
import yaml
from pathlib import Path

@dataclass
class APIConfig:
    provider: str
    model: str

@dataclass
class Job:
    name: str
    instruction: str
    file_path: str
    schema: Dict[str, Any]

@dataclass
class Config:
    api: APIConfig
    jobs: List[Job]

def load_config(path: str) -> Config:
    data = yaml.safe_load(Path(path).read_text())
    api = APIConfig(**data["api"])
    jobs = [Job(**j) for j in data.get("jobs", [])]
    return Config(api=api, jobs=jobs)