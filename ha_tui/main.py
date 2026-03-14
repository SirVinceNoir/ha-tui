from __future__ import annotations

from .app import HATuiApp
from .config import Config, CONFIG_FILE


def prompt_setup() -> Config:
    print("\nHome Assistant TUI — First Time Setup")
    print("─" * 40)
    url = input("Home Assistant URL (e.g. http://192.168.1.x:8123): ").strip()
    token = input("Long-lived access token: ").strip()
    config = Config(url=url.rstrip("/"), token=token)
    config.save()
    print(f"\nConfig saved to {CONFIG_FILE}\n")
    return config


def main() -> None:
    config = Config.load()
    if config is None:
        config = prompt_setup()
    HATuiApp(config).run()


if __name__ == "__main__":
    main()
