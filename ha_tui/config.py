from __future__ import annotations

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

from dataclasses import dataclass
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "ha-tui"
CONFIG_FILE = CONFIG_DIR / "config.toml"


@dataclass
class Config:
    url: str
    token: str

    @classmethod
    def load(cls) -> Config | None:
        if not CONFIG_FILE.exists():
            return None
        with open(CONFIG_FILE, "rb") as f:
            data = tomllib.load(f)
        return cls(url=data["url"], token=data["token"])

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            f.write(f'url = "{self.url}"\n')
            f.write(f'token = "{self.token}"\n')
