from __future__ import annotations

from urllib.parse import urlparse

import httpx

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, RadioButton, RadioSet

from .client import HAClient
from .config import Config
from .themes import DEFAULT_THEME, THEMES


def _connection_error(exc: Exception) -> str:
    """Return a short, human-readable description of a connection failure."""
    if isinstance(exc, httpx.ConnectError):
        return "Cannot reach server — check the URL"
    if isinstance(exc, (httpx.ConnectTimeout, httpx.ReadTimeout)):
        return "Connection timed out — check the URL"
    if isinstance(exc, httpx.HTTPStatusError):
        if exc.response.status_code == 401:
            return "Unauthorised — check your access token"
        return f"Server returned {exc.response.status_code}"
    return str(exc)


class SettingsScreen(ModalScreen[tuple[str, str, str] | None]):
    """Settings modal. Dismisses with (url, token, theme) or None if cancelled."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, config: Config) -> None:
        super().__init__()
        self._config = config
        self._theme_names = list(THEMES.keys())

    def compose(self) -> ComposeResult:
        current_theme = getattr(self._config, "theme", DEFAULT_THEME)

        with Container(id="settings-dialog"):
            yield Label("// SETTINGS //", id="settings-title")

            yield Label("── CONNECTION ──────────────────", classes="settings-divider")
            yield Label("URL", classes="settings-label")
            yield Input(
                value=self._config.url,
                id="input-url",
                placeholder="http://192.168.1.x:8123",
            )
            yield Label("TOKEN", classes="settings-label")
            yield Input(
                value=self._config.token,
                id="input-token",
                password=True,
                placeholder="Long-lived access token",
            )

            yield Label("── THEME ────────────────────────", classes="settings-divider")
            with RadioSet(id="theme-radio"):
                for name in self._theme_names:
                    yield RadioButton(
                        name.upper(),
                        value=(name == current_theme),
                    )

            with Horizontal(id="settings-buttons"):
                yield Button("Save", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")

            yield Label("", id="settings-status")

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Live-preview the selected theme on the app behind the modal."""
        if event.index < len(self._theme_names):
            self.app._apply_theme(self._theme_names[event.index])  # type: ignore[attr-defined]

    def _set_status(self, message: str, error: bool = False) -> None:
        label = self.query_one("#settings-status", Label)
        label.update(message)
        label.set_class(error, "settings-status-error")
        label.set_class(not error and bool(message), "settings-status-info")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            await self._save()
        elif event.button.id == "btn-cancel":
            self.action_cancel()

    async def _save(self) -> None:
        url = self.query_one("#input-url", Input).value.strip().rstrip("/")
        token = self.query_one("#input-token", Input).value.strip()

        # Basic format checks before hitting the network
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            self._set_status("Invalid URL — must start with http:// or https://", error=True)
            return
        if not token:
            self._set_status("Token cannot be empty", error=True)
            return

        # Live connection test
        self._set_status("Testing connection…")
        save_btn = self.query_one("#btn-save", Button)
        save_btn.disabled = True
        try:
            await HAClient(url, token).test_connection()
        except Exception as exc:
            self._set_status(_connection_error(exc), error=True)
            save_btn.disabled = False
            return

        save_btn.disabled = False
        idx = self.query_one("#theme-radio", RadioSet).pressed_index
        theme = self._theme_names[idx] if idx is not None else DEFAULT_THEME
        self.dismiss((url, token, theme))

    def action_cancel(self) -> None:
        self.dismiss(None)
