from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, RadioButton, RadioSet

from .config import Config
from .themes import DEFAULT_THEME, THEMES


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

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Live-preview the selected theme on the app behind the modal."""
        if event.index < len(self._theme_names):
            self.app._apply_theme(self._theme_names[event.index])  # type: ignore[attr-defined]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            url = self.query_one("#input-url", Input).value.strip().rstrip("/")
            token = self.query_one("#input-token", Input).value.strip()
            idx = self.query_one("#theme-radio", RadioSet).pressed_index
            theme = self._theme_names[idx] if idx is not None else DEFAULT_THEME
            self.dismiss((url, token, theme))
        elif event.button.id == "btn-cancel":
            self.action_cancel()

    def action_cancel(self) -> None:
        self.dismiss(None)
