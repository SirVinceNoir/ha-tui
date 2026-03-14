from __future__ import annotations

from collections import defaultdict

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.message import Message
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Static,
    Switch,
)

from .client import Entity, HAClient
from .config import Config
from .widgets import BrightnessPicker, ColorPicker, ColorTempPicker

_COLOR_MODES = {"hs", "rgb", "xy", "rgbw", "rgbww"}


def _entity_state_str(entity: Entity) -> str:
    state = entity.state
    if entity.domain == "light" and state == "on":
        b = entity.attributes.get("brightness")
        return f"ONLINE  {round(b / 255 * 100)}%" if b is not None else "ONLINE"
    elif entity.domain == "light":
        return "OFFLINE"
    elif entity.domain == "climate":
        t = entity.attributes.get("current_temperature")
        return f"{state.upper()}  {t}°" if t is not None else state.upper()
    return state


class AreaHeader(ListItem):
    def __init__(self, name: str) -> None:
        super().__init__()
        self._area_name = name

    def compose(self) -> ComposeResult:
        yield Label(f"── {self._area_name.upper()} ──", classes="area-header-label")


class EntityItem(ListItem):
    def __init__(self, entity: Entity) -> None:
        super().__init__()
        self.entity = entity

    def compose(self) -> ComposeResult:
        yield Label(f"> {self.entity.name}", classes="item-name")
        yield Label(_entity_state_str(self.entity), classes="item-state")


class LightPanel(Static):
    class StateChanged(Message):
        pass

    def __init__(self, entity: Entity, client: HAClient) -> None:
        super().__init__()
        self._entity = entity
        self._client = client
        self._updating = False

    def _supports_color(self) -> bool:
        modes = self._entity.attributes.get("supported_color_modes", [])
        return bool(_COLOR_MODES & set(modes))

    def _supports_color_temp(self) -> bool:
        modes = self._entity.attributes.get("supported_color_modes", [])
        return "color_temp" in modes

    def compose(self) -> ComposeResult:
        e = self._entity
        is_on = e.state == "on"
        b = e.attributes.get("brightness", 255)
        brightness_pct = round(b / 255 * 100) if b else 0

        yield Label(f"// {e.name.upper()} //", id="panel-title")
        yield Label(f">> {'ONLINE' if is_on else 'OFFLINE'}", id="panel-status")

        with Horizontal(classes="control-row"):
            yield Label("PWR", classes="control-label")
            yield Switch(value=is_on, id="light-switch")

        yield BrightnessPicker(initial_brightness=float(brightness_pct), id="brightness-picker")

        if self._supports_color():
            hs = e.attributes.get("hs_color") or [0, 100]
            yield Label("── COLOR ──────────────", classes="section-divider")
            yield ColorPicker(
                initial_hue=float(hs[0]),
                initial_sat=float(hs[1]),
                id="color-picker",
            )

        if self._supports_color_temp():
            mireds = e.attributes.get("color_temp") or None
            min_m = e.attributes.get("min_mireds") or 153
            max_m = e.attributes.get("max_mireds") or 500
            kelvin = round(1_000_000 / mireds) if mireds else 4000
            min_k = round(1_000_000 / max_m)
            max_k = round(1_000_000 / min_m)
            yield Label("── COLOR TEMP ─────────", classes="section-divider")
            yield ColorTempPicker(
                initial_kelvin=float(kelvin),
                min_kelvin=min_k,
                max_kelvin=max_k,
                id="color-temp-picker",
            )

    def update_entity(self, entity: Entity) -> None:
        """Update displayed values in-place without remounting."""
        self._entity = entity
        is_on = entity.state == "on"

        self.query_one("#panel-status", Label).update(
            f">> {'ONLINE' if is_on else 'OFFLINE'}"
        )

        self._updating = True
        self.query_one("#light-switch", Switch).value = is_on
        self._updating = False

        b = entity.attributes.get("brightness") or 0
        try:
            self.query_one("#brightness-picker", BrightnessPicker).update_value(
                round(b / 255 * 100)
            )
        except Exception:
            pass

        hs = entity.attributes.get("hs_color")
        if hs:
            try:
                self.query_one("#color-picker", ColorPicker).update_hs(
                    float(hs[0]), float(hs[1])
                )
            except Exception:
                pass

        mireds = entity.attributes.get("color_temp")
        if mireds:
            try:
                self.query_one("#color-temp-picker", ColorTempPicker).update_kelvin(
                    round(1_000_000 / mireds)
                )
            except Exception:
                pass

    async def on_switch_changed(self, event: Switch.Changed) -> None:
        if self._updating:
            return
        service = "turn_on" if event.value else "turn_off"
        try:
            await self._client.call_service(
                "light", service, {"entity_id": self._entity.entity_id}
            )
            self.post_message(self.StateChanged())
        except Exception as exc:
            self.app.notify(str(exc), severity="error")

    async def on_brightness_picker_applied(self, event: BrightnessPicker.Applied) -> None:
        try:
            await self._client.call_service(
                "light", "turn_on",
                {"entity_id": self._entity.entity_id, "brightness": round(event.brightness / 100 * 255)},
            )
            self.post_message(self.StateChanged())
        except Exception as exc:
            self.app.notify(str(exc), severity="error")

    async def on_color_temp_picker_applied(self, event: ColorTempPicker.Applied) -> None:
        try:
            await self._client.call_service(
                "light", "turn_on",
                {"entity_id": self._entity.entity_id, "color_temp": round(1_000_000 / event.kelvin)},
            )
            self.post_message(self.StateChanged())
        except Exception as exc:
            self.app.notify(str(exc), severity="error")

    async def on_color_picker_applied(self, event: ColorPicker.Applied) -> None:
        try:
            await self._client.call_service(
                "light", "turn_on",
                {"entity_id": self._entity.entity_id, "hs_color": [event.hue, event.saturation]},
            )
            self.post_message(self.StateChanged())
        except Exception as exc:
            self.app.notify(str(exc), severity="error")


class ClimatePanel(Static):
    class StateChanged(Message):
        pass

    def __init__(self, entity: Entity, client: HAClient) -> None:
        super().__init__()
        self._entity = entity
        self._client = client

    def compose(self) -> ComposeResult:
        e = self._entity
        attrs = e.attributes
        current = attrs.get("current_temperature", "—")
        target = attrs.get("temperature") or attrs.get("target_temp_high") or "—"
        unit = attrs.get("temperature_unit", "")
        min_t = attrs.get("min_temp", 7)
        max_t = attrs.get("max_temp", 35)

        yield Label(f"// {e.name.upper()} //", id="panel-title")
        yield Label(f">> MODE: {e.state.upper()}", id="panel-status")
        yield Label(f"  CURRENT  {current}{unit}", id="label-current-temp", classes="temp-display")
        yield Label(f"  TARGET   {target}{unit}", id="label-target-temp", classes="temp-display")
        yield Label(f"  RANGE    {min_t}–{max_t}{unit}", classes="temp-range")
        with Horizontal(classes="control-row"):
            yield Label("SET TARGET", classes="control-label")
            yield Input(
                value=str(target) if target != "—" else "",
                id="temp-input",
                placeholder="Temperature",
            )
            yield Button("Set", id="btn-temp", variant="primary")

    def update_entity(self, entity: Entity) -> None:
        """Update displayed values in-place without remounting."""
        self._entity = entity
        attrs = entity.attributes
        current = attrs.get("current_temperature", "—")
        target = attrs.get("temperature") or attrs.get("target_temp_high") or "—"
        unit = attrs.get("temperature_unit", "")

        self.query_one("#panel-status", Label).update(f">> MODE: {entity.state.upper()}")
        self.query_one("#label-current-temp", Label).update(f"  CURRENT  {current}{unit}")
        self.query_one("#label-target-temp", Label).update(f"  TARGET   {target}{unit}")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "btn-temp":
            return
        inp = self.query_one("#temp-input", Input)
        try:
            temp = float(inp.value)
            await self._client.call_service(
                "climate",
                "set_temperature",
                {"entity_id": self._entity.entity_id, "temperature": temp},
            )
            self.post_message(self.StateChanged())
        except ValueError:
            self.app.notify("Enter a valid temperature", severity="warning")
        except Exception as exc:
            self.app.notify(str(exc), severity="error")


class HATuiApp(App[None]):
    CSS_PATH = "app.tcss"
    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, config: Config) -> None:
        super().__init__()
        self._client = HAClient(config.url, config.token)
        self._entities: list[Entity] = []
        self._area_map: dict[str, str] = {}
        self._selected_id: str | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="body"):
            with Container(id="sidebar"):
                yield Label("// HA-CTRL //", id="sidebar-title")
                yield ListView(id="entity-list")
            with ScrollableContainer(id="detail"):
                yield Label("> SELECT NODE_", id="placeholder")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_entities()
        self.set_interval(30, self.refresh_entities)

    @work(exclusive=True)
    async def refresh_entities(self) -> None:
        try:
            self._entities = await self._client.get_states()
        except Exception as exc:
            self.notify(f"Connection failed: {exc}", severity="error", timeout=6)
            return
        try:
            self._area_map = await self._client.get_area_map()
        except Exception:
            self._area_map = {}

        await self._rebuild_list()
        if self._selected_id:
            entity = self._find(self._selected_id)
            if entity:
                await self._show_panel(entity)

    def _ordered_entities(self) -> list[tuple[str, Entity]]:
        """Return [(area_name, entity), ...] sorted by area then entity name."""
        groups: dict[str, list[Entity]] = defaultdict(list)
        for entity in self._entities:
            area = self._area_map.get(entity.entity_id) or "Uncategorized"
            groups[area].append(entity)

        areas = sorted(k for k in groups if k != "Uncategorized")
        if "Uncategorized" in groups:
            areas.append("Uncategorized")

        return [
            (area, entity)
            for area in areas
            for entity in sorted(groups[area], key=lambda e: e.name)
        ]

    async def _rebuild_list(self) -> None:
        lv = self.query_one("#entity-list", ListView)
        ordered = self._ordered_entities()
        new_ids = [e.entity_id for _, e in ordered]

        # If the entity IDs and order are unchanged, just update state labels in-place
        current_items = list(lv.query(EntityItem))
        if [item.entity.entity_id for item in current_items] == new_ids:
            for item, (_, entity) in zip(current_items, ordered):
                item.entity = entity
                item.query_one(".item-state", Label).update(_entity_state_str(entity))
            return

        # Structure changed — full rebuild
        await lv.clear()
        current_area: str | None = None
        for area, entity in ordered:
            if area != current_area:
                await lv.append(AreaHeader(area))
                current_area = area
            await lv.append(EntityItem(entity))

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, EntityItem):
            self._selected_id = event.item.entity.entity_id
            await self._show_panel(event.item.entity)

    async def _show_panel(self, entity: Entity) -> None:
        detail = self.query_one("#detail", ScrollableContainer)

        # Try to update in-place if the same entity is already displayed
        if entity.domain == "light":
            panels = list(detail.query(LightPanel))
            if panels and panels[0]._entity.entity_id == entity.entity_id:
                panels[0].update_entity(entity)
                return
        elif entity.domain == "climate":
            panels = list(detail.query(ClimatePanel))
            if panels and panels[0]._entity.entity_id == entity.entity_id:
                panels[0].update_entity(entity)
                return

        # Different entity — full remount
        await detail.remove_children()
        if entity.domain == "light":
            await detail.mount(LightPanel(entity, self._client))
        elif entity.domain == "climate":
            await detail.mount(ClimatePanel(entity, self._client))

    def _find(self, entity_id: str) -> Entity | None:
        return next((e for e in self._entities if e.entity_id == entity_id), None)

    def on_light_panel_state_changed(self, _: LightPanel.StateChanged) -> None:
        self.set_timer(0.5, self.refresh_entities)

    def on_climate_panel_state_changed(self, _: ClimatePanel.StateChanged) -> None:
        self.set_timer(0.5, self.refresh_entities)

    def action_refresh(self) -> None:
        self.refresh_entities()
        self.notify("Refreshing…", timeout=2)
