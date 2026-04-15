from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import yaml

BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "configs"
OUTPUTS_DIR = BASE_DIR / "outputs"


def ensure_directory(path: Path | str) -> Path:
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj


def load_yaml_config(relative_path: str) -> dict[str, Any]:
    config_path = CONFIG_DIR / relative_path
    with config_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def dump_yaml_file(path: Path | str, data: Any) -> Path:
    path_obj = Path(path)
    ensure_directory(path_obj.parent)
    with path_obj.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(to_serializable(data), handle, sort_keys=False, allow_unicode=False)
    return path_obj


def dump_json_file(path: Path | str, data: Any) -> Path:
    path_obj = Path(path)
    ensure_directory(path_obj.parent)
    with path_obj.open("w", encoding="utf-8") as handle:
        json.dump(to_serializable(data), handle, indent=2, sort_keys=True)
    return path_obj


def deep_update(base: dict[str, Any], overrides: dict[str, Any] | None) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    if not overrides:
        return merged

    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_update(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def to_serializable(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return to_serializable(dataclasses.asdict(value))
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): to_serializable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_serializable(item) for item in value]
    return value


def stable_hash(data: Any) -> str:
    payload = json.dumps(to_serializable(data), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
