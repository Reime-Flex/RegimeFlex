from pathlib import Path
import yaml

class Config:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._strategies = None
        self._risk = None
        self._schedule = None
        self._telemetry = None  # NEW

    def _load_yaml(self, rel_path: str):
        p = self.root / rel_path
        if not p.exists():
            raise FileNotFoundError(f"Missing config: {rel_path}")
        with p.open("r") as f:
            return yaml.safe_load(f) or {}

    @property
    def strategies(self):
        if self._strategies is None:
            self._strategies = self._load_yaml("config/strategies.yaml")
        return self._strategies

    @property
    def risk(self):
        if self._risk is None:
            self._risk = self._load_yaml("config/risk.yaml")
        return self._risk

    @property
    def schedule(self):
        if self._schedule is None:
            self._schedule = self._load_yaml("config/schedule.yaml")
        return self._schedule

    @property
    def telemetry(self):
        if self._telemetry is None:
            self._telemetry = self._load_yaml("config/telemetry.yaml")
        return self._telemetry
