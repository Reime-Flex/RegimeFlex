# engine/model_manifest.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
from .config import Config

def load_model_manifest(root: Path | str = ".") -> Dict[str, Any]:
    cfg = Config(root)
    try:
        data = cfg._load_yaml("config/model_manifest.yaml")
    except FileNotFoundError:
        return {
            "model": {
                "name": "RegimeFlex",
                "version": "0.0.0",
                "description": "NO_MANIFEST_FOUND",
                "components": {},
                "tags": [],
            }
        }
    return data or {}

